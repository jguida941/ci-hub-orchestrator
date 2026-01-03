"""Hub production CI helpers package.

This package splits the hub_ci module into logical submodules while
maintaining backward compatibility by re-exporting all public symbols.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # Secure XML parsing (prevents XXE)

from cihub import badges as badge_tools
from cihub.cli import hub_root
from cihub.config.io import load_yaml_file
from cihub.config.normalize import normalize_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS
from cihub.services.types import RepoEntry
from cihub.utils.env import _parse_env_bool
from cihub.utils.progress import _bar

# ============================================================================
# Shared Helpers (lines 33-151 from original hub_ci.py)
# ============================================================================


def _write_outputs(values: dict[str, str], output_path: Path | None) -> None:
    if output_path is None:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _append_summary(text: str, summary_path: Path | None) -> None:
    if summary_path is None:
        print(text)
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _resolve_output_path(path_value: str | None, github_output: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_output:
        env_path = os.environ.get("GITHUB_OUTPUT")
        return Path(env_path) if env_path else None
    return None


def _resolve_summary_path(path_value: str | None, github_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_github_path(path_value: Path) -> None:
    env_path = os.environ.get("GITHUB_PATH")
    if not env_path:
        return
    with open(env_path, "a", encoding="utf-8") as handle:
        handle.write(f"{path_value}\n")


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return normalize_config(load_yaml_file(path))
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load config: {exc}")
        return {}


def _run_command(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=env,
    )


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "cihub"})  # noqa: S310
    with urllib.request.urlopen(request) as response:  # noqa: S310
        dest.write_bytes(response.read())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_tarball_member(tar_path: Path, member_name: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        member = tar.getmember(member_name)
        tar.extract(member, path=dest_dir)
    extracted = dest_dir / member_name
    extracted.chmod(extracted.stat().st_mode | stat.S_IEXEC)
    return extracted


def _parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


# ============================================================================
# Helper functions exported for backward compatibility
# ============================================================================


def _extract_count(line: str, emoji: str) -> int:
    match = re.search(rf"{re.escape(emoji)}\s*(\d+)", line)
    if match:
        return int(match.group(1))
    return 0


def _compare_badges(expected_dir: Path, actual_dir: Path) -> list[str]:
    issues: list[str] = []
    if not expected_dir.exists():
        return [f"missing badges directory: {expected_dir}"]

    expected = {p.name: p for p in expected_dir.glob("*.json")}
    actual = {p.name: p for p in actual_dir.glob("*.json")}

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    for name in missing:
        issues.append(f"missing: {name}")
    for name in extra:
        issues.append(f"extra: {name}")

    for name in sorted(set(expected) & set(actual)):
        try:
            expected_data = json.loads(expected[name].read_text(encoding="utf-8"))
            actual_data = json.loads(actual[name].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"invalid json: {name} ({exc})")
            continue
        if expected_data != actual_data:
            issues.append(f"diff: {name}")

    return issues


def _count_pip_audit_vulns(data: Any) -> int:
    if not isinstance(data, list):
        return 0
    total = 0
    for item in data:
        vulns = item.get("vulns") or item.get("vulnerabilities") or []
        total += len(vulns)
    return total


# Empty SARIF for fallback when zizmor fails
EMPTY_SARIF = (
    '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",'
    '"runs":[{"tool":{"driver":{"name":"zizmor","version":"0.8.0"}},"results":[]}]}'
)


# ============================================================================
# Import and re-export all cmd_* functions from submodules
# ============================================================================

from cihub.commands.hub_ci.python_tools import (
    cmd_black,
    cmd_mutmut,
    cmd_ruff,
)
from cihub.commands.hub_ci.badges import (
    cmd_badges,
    cmd_badges_commit,
    cmd_outputs,
)
from cihub.commands.hub_ci.security import (
    cmd_bandit,
    cmd_pip_audit,
    cmd_security_bandit,
    cmd_security_owasp,
    cmd_security_pip_audit,
    cmd_security_ruff,
)
from cihub.commands.hub_ci.validation import (
    cmd_docker_compose_check,
    cmd_quarantine_check,
    cmd_repo_check,
    cmd_source_check,
    cmd_syntax_check,
    cmd_validate_configs,
    cmd_validate_profiles,
    cmd_verify_matrix_keys,
)
from cihub.commands.hub_ci.java_tools import (
    cmd_codeql_build,
    cmd_smoke_java_build,
    cmd_smoke_java_checkstyle,
    cmd_smoke_java_coverage,
    cmd_smoke_java_spotbugs,
    cmd_smoke_java_tests,
)
from cihub.commands.hub_ci.smoke import (
    _last_regex_int,
    cmd_smoke_python_black,
    cmd_smoke_python_install,
    cmd_smoke_python_ruff,
    cmd_smoke_python_tests,
)
from cihub.commands.hub_ci.release import (
    cmd_actionlint,
    cmd_actionlint_install,
    cmd_enforce,
    cmd_gitleaks_summary,
    cmd_kyverno_install,
    cmd_kyverno_test,
    cmd_kyverno_validate,
    cmd_license_check,
    cmd_pytest_summary,
    cmd_release_parse_tag,
    cmd_release_update_tag,
    cmd_summary,
    cmd_trivy_install,
    cmd_trivy_summary,
    cmd_zizmor_check,
    cmd_zizmor_run,
)
from cihub.commands.hub_ci.router import cmd_hub_ci

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Shared helpers
    "_write_outputs",
    "_append_summary",
    "_resolve_output_path",
    "_resolve_summary_path",
    "_extract_count",
    "_compare_badges",
    "_count_pip_audit_vulns",
    "_parse_env_bool",
    # Constants
    "EMPTY_SARIF",
    # Python tools
    "cmd_ruff",
    "cmd_black",
    "cmd_mutmut",
    # Badges
    "cmd_badges",
    "cmd_badges_commit",
    "cmd_outputs",
    # Security
    "cmd_bandit",
    "cmd_pip_audit",
    "cmd_security_pip_audit",
    "cmd_security_bandit",
    "cmd_security_ruff",
    "cmd_security_owasp",
    # Validation
    "cmd_syntax_check",
    "cmd_repo_check",
    "cmd_source_check",
    "cmd_docker_compose_check",
    "cmd_validate_configs",
    "cmd_validate_profiles",
    "cmd_verify_matrix_keys",
    "cmd_quarantine_check",
    # Java tools
    "cmd_codeql_build",
    "cmd_smoke_java_build",
    "cmd_smoke_java_tests",
    "cmd_smoke_java_coverage",
    "cmd_smoke_java_checkstyle",
    "cmd_smoke_java_spotbugs",
    # Smoke tests
    "cmd_smoke_python_install",
    "cmd_smoke_python_tests",
    "cmd_smoke_python_ruff",
    "cmd_smoke_python_black",
    "_last_regex_int",
    # Release & tooling
    "cmd_release_parse_tag",
    "cmd_release_update_tag",
    "cmd_kyverno_install",
    "cmd_kyverno_validate",
    "cmd_kyverno_test",
    "cmd_trivy_install",
    "cmd_trivy_summary",
    "cmd_zizmor_run",
    "cmd_zizmor_check",
    "cmd_actionlint_install",
    "cmd_actionlint",
    "cmd_license_check",
    "cmd_gitleaks_summary",
    "cmd_pytest_summary",
    "cmd_summary",
    "cmd_enforce",
    # Router
    "cmd_hub_ci",
]
