#!/usr/bin/env python3
"""
Guardrails for GitHub workflows.

- Ensures every `uses:` reference is pinned to an exact commit SHA (40 lowercase hex).
- Scans workflow/job/step `env` and `with` mappings for sensitive keys and verifies the
  values come from sanctioned expressions (`secrets.`, `vars.`, `steps.`, etc.) instead
  of hard-coded credentials.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PIN_RE = re.compile(r"@[0-9a-f]{40}(?:\b|$)")
SENSITIVE_TOKENS = ("SECRET", "TOKEN", "PASSWORD", "ACCESS_KEY", "PRIVATE_KEY")
ALLOWED_VALUE_PREFIXES = (
    "${{ secrets.",
    "${{ vars.",
    "${{ steps.",
    "${{ needs.",
    "${{ github.",
    "${{ inputs.",
)


class WorkflowError(Exception):
    """Wrapper for integrity violations."""


def _load_docs(path: Path) -> list[dict[str, Any]]:
    try:
        docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:  # pragma: no cover - surfaced in CI logs
        raise WorkflowError(f"{path}: invalid yaml: {exc}") from exc
    normalized: list[dict[str, Any]] = []
    for doc in docs:
        if doc is None:
            continue
        if not isinstance(doc, dict):
            raise WorkflowError(f"{path}: expected YAML document to be a mapping, got {type(doc).__name__}")
        normalized.append(doc)
    return normalized


def _check_env(mapping: Any, ctx: str, errors: list[str]) -> None:
    if not isinstance(mapping, dict):
        return
    for key, value in mapping.items():
        if not isinstance(key, str):
            continue
        upper_key = key.upper()
        if not any(token in upper_key for token in SENSITIVE_TOKENS):
            continue
        if not isinstance(value, str):
            continue
        if isinstance(value, str) and any(value.strip().startswith(prefix) for prefix in ALLOWED_VALUE_PREFIXES):
            continue
        errors.append(f"{ctx}: key '{key}' must source from secrets/vars/steps, not '{value}'")


def _check_steps(path: Path, job_name: str, steps: Any, errors: list[str]) -> None:
    if steps is None:
        steps = []
    if not isinstance(steps, list):
        errors.append(f"{path}: job '{job_name}' steps must be a list")
        return
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"{path}: job '{job_name}' step #{idx} must be a mapping")
            continue
        uses = step.get("uses")
        if isinstance(uses, str) and not uses.startswith("./"):
            if not PIN_RE.search(uses):
                errors.append(f"{path}: job '{job_name}' step #{idx} uses '{uses}' without a commit SHA")
        _check_env(step.get("env"), f"{path}: job '{job_name}' step #{idx} env", errors)
        _check_env(step.get("with"), f"{path}: job '{job_name}' step #{idx} with", errors)


def _check_workflow(path: Path) -> list[str]:
    errors: list[str] = []
    docs = _load_docs(path)
    for doc in docs:
        _check_env(doc.get("env"), f"{path}: workflow env", errors)
        jobs = doc.get("jobs", {})
        if not isinstance(jobs, dict):
            errors.append(f"{path}: jobs block must be a mapping")
            continue
        for job_name, job_cfg in jobs.items():
            if not isinstance(job_cfg, dict):
                errors.append(f"{path}: job '{job_name}' must be a mapping")
                continue
            _check_env(job_cfg.get("env"), f"{path}: job '{job_name}' env", errors)
            _check_steps(path, job_name, job_cfg.get("steps", []), errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub workflow guardrails")
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="Directory containing workflow YAML files (default: .github/workflows)",
    )
    args = parser.parse_args()

    if not args.workflows_dir.is_dir():
        raise SystemExit(f"Workflow directory not found: {args.workflows_dir}")

    all_errors: list[str] = []
    workflow_files = sorted(
        path for path in args.workflows_dir.iterdir() if path.is_file() and path.suffix in {".yml", ".yaml"}
    )
    for path in workflow_files:
        all_errors.extend(_check_workflow(path))

    if all_errors:
        for msg in all_errors:
            print(f"[workflow-integrity] {msg}", file=sys.stderr)
        return 1
    print("[workflow-integrity] all workflows pinned and secretless ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
