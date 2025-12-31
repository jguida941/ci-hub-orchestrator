#!/usr/bin/env python3
"""
CLI integration runner for fixture repos.

Runs cihub commands against fixture subdirs using a temp copy so the fixtures
repo is not modified.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class FixtureCase:
    name: str
    language: str
    subdir: str


# Fixture names correspond to subdirs in ci-cd-hub-fixtures, not to config filenames.
# Config files (config/repos/fixtures-*.yaml) are internal hub identifiers; the
# repo.subdir field in each config is the source of truth for fixture mapping.
FIXTURES: list[FixtureCase] = [
    FixtureCase("java-maven-pass", "java", "java-maven-pass"),
    FixtureCase("java-maven-fail", "java", "java-maven-fail"),
    FixtureCase("java-gradle-pass", "java", "java-gradle-pass"),
    FixtureCase("java-gradle-fail", "java", "java-gradle-fail"),
    FixtureCase("java-multi-module-pass", "java", "java-multi-module-pass"),
    FixtureCase("python-pyproject-pass", "python", "python-pyproject-pass"),
    FixtureCase("python-pyproject-fail", "python", "python-pyproject-fail"),
    FixtureCase("python-setup-pass", "python", "python-setup-pass"),
    FixtureCase("python-setup-fail", "python", "python-setup-fail"),
    FixtureCase("python-src-layout-pass", "python", "python-src-layout-pass"),
    FixtureCase("monorepo-java-pass", "java", "monorepo-pass/java"),
    FixtureCase("monorepo-java-fail", "java", "monorepo-fail/java"),
    FixtureCase("monorepo-python-pass", "python", "monorepo-pass/python"),
    FixtureCase("monorepo-python-fail", "python", "monorepo-fail/python"),
]


def run(cmd: list[str], cwd: Path, capture: bool = False) -> str:
    """Run a command, optionally capturing stdout."""
    print(f"[RUN] ({cwd}) {' '.join(cmd)}")
    result = subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        text=True,
        capture_output=capture,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout if capture else ""


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping at top level")
    return data


def iter_fixtures(fixtures: Iterable[FixtureCase], names: set[str]) -> list[FixtureCase]:
    if not names:
        return list(fixtures)
    filtered = [fx for fx in fixtures if fx.name in names]
    missing = names - {fx.name for fx in filtered}
    if missing:
        raise ValueError(f"Unknown fixtures: {', '.join(sorted(missing))}")
    return filtered


def run_fixture(fixtures_path: Path, fixture: FixtureCase) -> None:
    with tempfile.TemporaryDirectory(prefix="cihub-fixture-") as temp_dir:
        repo_root = Path(temp_dir) / fixture.name
        shutil.copytree(fixtures_path, repo_root, dirs_exist_ok=True)

        subdir_path = repo_root / fixture.subdir
        if not subdir_path.exists():
            raise FileNotFoundError(f"Missing fixture path: {subdir_path}")

        owner = "fixtures"
        repo_name = fixture.name

        # Run detect and verify it matches expected language
        detect_output = run(
            [
                sys.executable,
                "-m",
                "cihub",
                "detect",
                "--repo",
                str(subdir_path),
                "--json",
            ],
            cwd=subdir_path,
            capture=True,
        )
        try:
            payload = json.loads(detect_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"cihub detect did not return JSON: {exc}") from exc
        detected = (
            payload.get("data", {}).get("language") if isinstance(payload.get("data"), dict) else None
        ) or payload.get("language")
        if detected != fixture.language:
            raise ValueError(f"Language mismatch for {fixture.name}: expected '{fixture.language}', got: {detected}")
        run(
            [
                sys.executable,
                "-m",
                "cihub",
                "init",
                "--repo",
                str(repo_root),
                "--language",
                fixture.language,
                "--owner",
                owner,
                "--name",
                repo_name,
                "--branch",
                "main",
                "--subdir",
                fixture.subdir,
                "--apply",
            ],
            cwd=repo_root,
        )
        run(
            [
                sys.executable,
                "-m",
                "cihub",
                "update",
                "--repo",
                str(repo_root),
                "--language",
                fixture.language,
                "--owner",
                owner,
                "--name",
                repo_name,
                "--branch",
                "main",
                "--subdir",
                fixture.subdir,
                "--apply",
                "--force",
            ],
            cwd=repo_root,
        )
        run(
            [sys.executable, "-m", "cihub", "validate", "--repo", str(repo_root)],
            cwd=repo_root,
        )

        config_path = repo_root / ".ci-hub.yml"
        if not config_path.exists():
            raise FileNotFoundError(f"Missing config: {config_path}")

        config = load_yaml(config_path)
        repo_block = config.get("repo", {})
        if repo_block.get("subdir") != fixture.subdir:
            raise ValueError(f"repo.subdir mismatch for {fixture.name}: {repo_block.get('subdir')}")

        workflow_path = repo_root / ".github" / "workflows" / "hub-ci.yml"
        if not workflow_path.exists():
            raise FileNotFoundError(f"Missing workflow: {workflow_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CLI integration tests.")
    parser.add_argument(
        "--fixtures-path",
        type=Path,
        required=True,
        help="Path to a local clone of ci-cd-hub-fixtures",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only named fixture(s); can be repeated",
    )
    args = parser.parse_args()

    fixtures_path = args.fixtures_path.resolve()
    if not fixtures_path.exists():
        print(f"Fixtures path not found: {fixtures_path}", file=sys.stderr)
        return 2

    try:
        selected = iter_fixtures(FIXTURES, set(args.only))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for fixture in selected:
        print(f"[CASE] {fixture.name}")
        try:
            run_fixture(fixtures_path, fixture)
        except Exception as exc:
            print(f"[FAIL] {fixture.name}: {exc}", file=sys.stderr)
            return 1
        print(f"[OK] {fixture.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
