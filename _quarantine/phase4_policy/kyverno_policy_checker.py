from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml


@dataclass(frozen=True)
class EvaluationResult:
    resource: Path
    check: str
    passed: bool
    failures: Tuple[str, ...]


logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        logger.error("YAML file not found: %s", path)
        raise FileNotFoundError(f"YAML file not found: {path}") from exc
    except yaml.YAMLError as exc:
        logger.error("Invalid YAML in %s: %s", path, exc)
        raise yaml.YAMLError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}, found {type(data).__name__}")
    return data


def _extract_pod_spec(resource: dict) -> Tuple[dict, dict]:
    kind = resource.get("kind", "")
    metadata = resource.get("metadata") or {}
    if kind == "Pod":
        return resource.get("spec") or {}, metadata
    spec = resource.get("spec") or {}
    if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job"}:
        template = spec.get("template") or {}
        return template.get("spec") or {}, template.get("metadata") or {}
    if kind == "CronJob":
        job_template = (spec.get("jobTemplate") or {}).get("spec") or {}
        template = job_template.get("template") or {}
        return template.get("spec") or {}, template.get("metadata") or {}
    return {}, {}


def _collect_images(resource: dict) -> List[str]:
    pod_spec, _ = _extract_pod_spec(resource)
    images: List[str] = []
    for container in pod_spec.get("containers", []) or []:
        image = container.get("image")
        if image:
            images.append(image)
    for container in pod_spec.get("initContainers", []) or []:
        image = container.get("image")
        if image:
            images.append(image)
    return images


def _has_allow_label(resource: dict) -> bool:
    labels = (resource.get("metadata") or {}).get("labels") or {}
    if labels.get("ci-intel.dev/allow-static-secrets") == "true":
        return True
    _, template_metadata = _extract_pod_spec(resource)
    template_labels = (template_metadata or {}).get("labels") or {}
    return template_labels.get("ci-intel.dev/allow-static-secrets") == "true"


def _collect_annotations(resource: dict) -> List[dict]:
    annotations = []
    metadata = resource.get("metadata") or {}
    if metadata.get("annotations"):
        annotations.append(metadata["annotations"])
    _, template_metadata = _extract_pod_spec(resource)
    if template_metadata and template_metadata.get("annotations"):
        annotations.append(template_metadata["annotations"])
    return annotations


def _find_secret_usage(resource: dict) -> List[str]:
    pod_spec, _ = _extract_pod_spec(resource)
    findings: List[str] = []

    def scan_env(container: dict, container_name: str) -> None:
        for env in container.get("env", []) or []:
            value_from = env.get("valueFrom") or {}
            if value_from.get("secretKeyRef"):
                env_name = env.get("name") or "<unknown>"
                findings.append(f"container '{container_name}' env '{env_name}' uses secretKeyRef")

    for container in pod_spec.get("containers", []) or []:
        scan_env(container, container.get("name") or "<unnamed>")
    for container in pod_spec.get("initContainers", []) or []:
        scan_env(container, container.get("name") or "<unnamed>")

    for volume in pod_spec.get("volumes", []) or []:
        if volume.get("secret") is not None:
            findings.append(f"volume '{volume.get('name', '<unnamed>')}' mounts a secret")
    return findings


def evaluate_verify_images(policy_path: Path, resource_path: Path) -> EvaluationResult:
    policy = _load_yaml(policy_path)
    resource = _load_yaml(resource_path)

    rules = (policy.get("spec") or {}).get("rules") or []
    patterns: List[str] = []
    for rule in rules:
        for verifier in rule.get("verifyImages", []) or []:
            patterns.extend(verifier.get("imageReferences") or [])

    failures: List[str] = []
    images = _collect_images(resource)
    digest_pattern = re.compile(r"@[A-Za-z0-9_+.\-]+:[0-9A-Fa-f]{32,}")
    for image in images:
        if patterns and not any(fnmatch.fnmatch(image, pattern) for pattern in patterns):
            continue
        if not digest_pattern.search(image):
            failures.append(f"image '{image}' is missing a pinned digest (e.g., @sha256:...)")
    return EvaluationResult(resource=resource_path, check="verify-images", passed=not failures, failures=tuple(failures))


def evaluate_require_referrers(resource_path: Path) -> EvaluationResult:
    resource = _load_yaml(resource_path)
    required_keys = {
        "ci-intel.dev/sbom-referrer",
        "ci-intel.dev/provenance-referrer",
    }

    failures: List[str] = []
    annotation_sets = _collect_annotations(resource)
    if not annotation_sets:
        failures.append("no annotations found to satisfy referrer policy")
    else:
        matched = False
        for annotations in annotation_sets:
            if required_keys.issubset(annotations.keys()) and all(
                str(annotations[key]).startswith("oci://") for key in required_keys
            ):
                matched = True
                break
        if not matched:
            failures.append("required oci:// referrer annotations missing")
    return EvaluationResult(resource=resource_path, check="require-referrers", passed=not failures, failures=tuple(failures))


def evaluate_secretless(resource_path: Path) -> EvaluationResult:
    resource = _load_yaml(resource_path)
    failures: List[str] = []
    if _has_allow_label(resource):
        return EvaluationResult(resource=resource_path, check="secretless", passed=True, failures=())

    findings = _find_secret_usage(resource)
    if findings:
        failures.extend(findings)
    return EvaluationResult(resource=resource_path, check="secretless", passed=not failures, failures=tuple(failures))


def evaluate_resource(
    policies_dir: Path, resource_path: Path, checks: Iterable[str] | None = None
) -> List[EvaluationResult]:
    valid_checks = {"verify-images", "require-referrers", "secretless"}
    checks = list(checks or ["verify-images", "require-referrers", "secretless"])
    invalid_checks = [check for check in checks if check not in valid_checks]
    if invalid_checks:
        raise ValueError(f"Unknown checks requested: {', '.join(sorted(invalid_checks))}. Allowed: {', '.join(sorted(valid_checks))}")
    results: List[EvaluationResult] = []

    for check in checks:
        if check == "verify-images":
            policy_path = policies_dir / "verify-images.yaml"
            if not policy_path.exists():
                results.append(
                    EvaluationResult(
                        resource=resource_path,
                        check="verify-images",
                        passed=False,
                        failures=(f"verify-images policy file not found: {policy_path}",),
                    )
                )
                continue
            results.append(evaluate_verify_images(policy_path, resource_path))
        elif check == "require-referrers":
            results.append(evaluate_require_referrers(resource_path))
        elif check == "secretless":
            results.append(evaluate_secretless(resource_path))
    return results
