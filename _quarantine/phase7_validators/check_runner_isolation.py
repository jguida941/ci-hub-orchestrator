#!/usr/bin/env python3
"""Validate runner isolation and concurrency configurations for GitHub workflows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

DEFAULT_WORKFLOWS_DIR = Path(".github/workflows")


class RunnerIsolationError(RuntimeError):
    """Domain-specific error for validation issues."""


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover - path errors surfaced in CI
        raise RunnerIsolationError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RunnerIsolationError(f"{path}: expected top-level mapping")
    return data


def _normalize_runs_on(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        normalized: List[str] = []
        for item in value:
            if isinstance(item, str):
                normalized.append(item)
            else:
                raise RunnerIsolationError(f"runs-on entries must be strings, got {item!r}")
        return normalized
    raise RunnerIsolationError(f"runs-on must be string or list, got {type(value).__name__}")


def _validate_concurrency(workflow_path: Path, workflow: Dict[str, Any], require_cancel: bool) -> None:
    concurrency = workflow.get("concurrency")
    if concurrency is None:
        if require_cancel:
            raise RunnerIsolationError(f"{workflow_path}: concurrency block missing")
        return
    if not isinstance(concurrency, dict):
        raise RunnerIsolationError(f"{workflow_path}: concurrency block must be a mapping")
    cancel = concurrency.get("cancel-in-progress")
    if require_cancel and cancel is not True:
        raise RunnerIsolationError(
            f"{workflow_path}: concurrency.cancel-in-progress must be true for fairness budgets"
        )


def _validate_job(
    workflow_path: Path,
    job_id: str,
    job_cfg: Dict[str, Any],
    job_requirements: Dict[str, Any],
    allowed_runners: List[str],
) -> None:
    if "uses" in job_cfg:
        # Reusable workflow invocation; skip runner validation for this job.
        return
    runs_on = job_cfg.get("runs-on")
    if runs_on is None:
        raise RunnerIsolationError(f"{workflow_path}: job '{job_id}' missing runs-on")
    actual_runs = _normalize_runs_on(runs_on)
    if not set(actual_runs).intersection(set(allowed_runners)):
        raise RunnerIsolationError(
            f"{workflow_path}: job '{job_id}' runs-on {actual_runs} not in allowed set {allowed_runners}"
        )

    expected_runs_on = job_requirements.get("runs_on")
    if expected_runs_on:
        expected_normalized = _normalize_runs_on(expected_runs_on)
        if sorted(actual_runs) != sorted(expected_normalized):
            raise RunnerIsolationError(
                f"{workflow_path}: job '{job_id}' runs-on {actual_runs} does not match expected {expected_normalized}"
            )

    max_parallel = job_requirements.get("max_parallel")
    if max_parallel is not None:
        strategy = job_cfg.get("strategy")
        if not isinstance(strategy, dict):
            raise RunnerIsolationError(
                f"{workflow_path}: job '{job_id}' must define strategy.max-parallel={max_parallel}"
            )
        actual_max_parallel = strategy.get("max-parallel")
        if actual_max_parallel != max_parallel:
            raise RunnerIsolationError(
                f"{workflow_path}: job '{job_id}' strategy.max-parallel={actual_max_parallel} "
                f"does not match configured budget {max_parallel}"
            )


def _validate_workflow(
    workflows_dir: Path,
    workflow_file: str,
    requirements: Dict[str, Any],
    allowed_runners: List[str],
    default_require_cancel: bool,
    self_hosted_profiles: Dict[str, Dict[str, Any]],
) -> None:
    workflow_path = workflows_dir / workflow_file
    if not workflow_path.is_file():
        raise RunnerIsolationError(f"workflow file not found: {workflow_path}")

    workflow = _load_yaml(workflow_path)
    require_cancel = requirements.get("require_cancel_in_progress", default_require_cancel)
    _validate_concurrency(workflow_path, workflow, require_cancel)

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        raise RunnerIsolationError(f"{workflow_path}: jobs block missing or invalid")

    job_requirements = requirements.get("jobs", {})
    for job_id, job_cfg in jobs.items():
        if not isinstance(job_cfg, dict):
            continue
        requirements_for_job = job_requirements.get(job_id, {})
        if not requirements_for_job:
            # Even without explicit requirements, we still ensure the job uses an allowed runner.
            requirements_for_job = {}
        runs_on_value = job_cfg.get("runs-on")
        if runs_on_value is None and "uses" not in job_cfg:
            raise RunnerIsolationError(f"{workflow_path}: job '{job_id}' missing runs-on")

        isolation_profile = requirements_for_job.get("self_hosted_profile")
        if isolation_profile:
            profile = self_hosted_profiles.get(isolation_profile)
            if profile is None:
                raise RunnerIsolationError(
                    f"{workflow_path}: job '{job_id}' references unknown self_hosted_profile"
                )
            required_labels = profile.get("required_labels") or []
            actual_runs = _normalize_runs_on(runs_on_value)
            missing_labels = set(required_labels) - set(actual_runs)
            if missing_labels:
                raise RunnerIsolationError(
                    f"{workflow_path}: job '{job_id}' missing required runner labels {sorted(missing_labels)}"
                )
        _validate_job(
            workflow_path=workflow_path,
            job_id=job_id,
            job_cfg=job_cfg,
            job_requirements=requirements_for_job,
            allowed_runners=allowed_runners,
        )

    # Ensure every budgeted job exists.
    for job_id in job_requirements:
        if job_id not in jobs:
            raise RunnerIsolationError(
                f"{workflow_path}: configured job '{job_id}' missing from workflow"
            )


def validate(config_path: Path, workflows_dir: Path) -> None:
    config = _load_yaml(config_path)
    version = config.get("version")
    if version != 1:
        raise RunnerIsolationError(f"{config_path}: unsupported config version {version!r}")

    defaults = config.get("defaults") or {}
    require_cancel = defaults.get("require_cancel_in_progress", True)
    allowed_runners = defaults.get("allowed_runners")
    if not isinstance(allowed_runners, list) or not allowed_runners:
        raise RunnerIsolationError(f"{config_path}: defaults.allowed_runners must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in allowed_runners):
        raise RunnerIsolationError(f"{config_path}: defaults.allowed_runners must contain only non-empty strings")

    workflows = config.get("workflows")
    if not isinstance(workflows, dict) or not workflows:
        raise RunnerIsolationError(f"{config_path}: workflows mapping missing or empty")

    self_hosted_profiles = config.get("self_hosted_profiles") or {}
    if not isinstance(self_hosted_profiles, dict):
        raise RunnerIsolationError(f"{config_path}: self_hosted_profiles must be a mapping when provided")

    repo_root = workflows_dir.parent
    if repo_root.name == ".github":
        repo_root = repo_root.parent

    for profile_name, profile in self_hosted_profiles.items():
        if not isinstance(profile, dict):
            raise RunnerIsolationError(f"{config_path}: profile '{profile_name}' must be an object")
        labels = profile.get("required_labels")
        if not isinstance(labels, list) or not labels:
            raise RunnerIsolationError(
                f"{config_path}: profile '{profile_name}' must specify non-empty required_labels list"
            )
        cache_script = profile.get("cache_provenance_script")
        if cache_script:
            script_path = (repo_root / cache_script).resolve()
            if not script_path.is_file():
                raise RunnerIsolationError(
                    f"{config_path}: profile '{profile_name}' cache_provenance_script missing: {script_path}"
                )
        egress_policy = profile.get("egress_policy")
        if egress_policy:
            policy_path = (repo_root / egress_policy).resolve()
            if not policy_path.is_file():
                raise RunnerIsolationError(
                    f"{config_path}: profile '{profile_name}' egress_policy missing: {policy_path}"
                )

    for workflow_file, requirements in workflows.items():
        if not isinstance(requirements, dict):
            raise RunnerIsolationError(f"{config_path}: workflow entry '{workflow_file}' must be a mapping")
        _validate_workflow(
            workflows_dir=workflows_dir,
            workflow_file=workflow_file,
            requirements=requirements,
            allowed_runners=allowed_runners,
            default_require_cancel=require_cancel,
            self_hosted_profiles=self_hosted_profiles,
        )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ensure workflows adhere to runner isolation and concurrency budgets."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/runner-isolation.yaml"),
        help="Runner isolation configuration file (default: config/runner-isolation.yaml)",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help="Directory containing workflows (default: .github/workflows)",
    )
    args = parser.parse_args(argv)

    config_path = args.config.resolve()
    if not config_path.is_file():
        raise SystemExit(f"runner isolation config not found: {config_path}")

    workflows_dir = args.workflows_dir.resolve()
    if not workflows_dir.is_dir():
        raise SystemExit(f"workflows directory not found: {workflows_dir}")

    try:
        validate(config_path, workflows_dir)
    except RunnerIsolationError as exc:
        print(f"[runner-isolation] {exc}", file=sys.stderr)
        return 1

    print(f"[runner-isolation] validated runner isolation budgets from {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
