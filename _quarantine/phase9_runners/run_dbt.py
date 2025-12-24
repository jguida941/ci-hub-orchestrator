#!/usr/bin/env python3
"""Thin wrapper to run dbt with the repo-default profiles directory.

This allows IDE run configurations and local commands to invoke dbt without
having to manage per-user PATH lookups or profile flags. Any arguments passed
to this script are forwarded to dbt; if no --profiles-dir flag is provided and
DBT_PROFILES_DIR is unset, the script defaults to <repo>/models.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dbt.cli.main import dbtRunner, dbtRunnerResult


def _default_profiles_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


def _default_project_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    os.environ.setdefault("DBT_PROFILES_DIR", str(_default_profiles_dir()))
    os.environ.setdefault("DBT_PROJECT_DIR", str(_default_project_dir()))
    runner = dbtRunner()
    try:
        result: dbtRunnerResult = runner.invoke(args)
    except Exception as exc:  # pragma: no cover - surfaced in CI
        print(f"[dbt] {exc}", file=sys.stderr)
        return 1
    if result.exception:
        print(f"[dbt] {result.exception}", file=sys.stderr)
        return 1
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
