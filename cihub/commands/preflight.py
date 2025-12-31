"""Preflight checks for local environment readiness."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from typing import Any

from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _command_exists(command: str) -> str | None:
    return shutil.which(command)


def _add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    required: bool,
    detail: str,
    hint: str | None = None,
) -> None:
    status = "ok" if ok else ("fail" if required else "warn")
    entry = {
        "name": name,
        "status": status,
        "required": required,
        "detail": detail,
    }
    if hint:
        entry["hint"] = hint
    checks.append(entry)


def _check_python_version(checks: list[dict[str, Any]]) -> None:
    min_version = (3, 11)
    current = sys.version_info
    ok = (current.major, current.minor) >= min_version
    detail = f"{current.major}.{current.minor}.{current.micro}"
    hint = "Install Python 3.11+" if not ok else None
    _add_check(checks, "python", ok, True, detail, hint)


def _check_command(
    checks: list[dict[str, Any]],
    name: str,
    required: bool,
    hint: str,
) -> None:
    path = _command_exists(name)
    ok = path is not None
    detail = path or "not found"
    _add_check(checks, name, ok, required, detail, hint if not ok else None)


def _check_gh_auth(checks: list[dict[str, Any]]) -> None:
    if not _command_exists("gh"):
        _add_check(
            checks,
            "gh auth",
            False,
            False,
            "gh not installed",
            "Install gh and run: gh auth login",
        )
        return
    proc = subprocess.run(  # noqa: S603
        ["gh", "auth", "status", "--hostname", "github.com"],  # noqa: S607
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    detail = "authenticated" if ok else "not authenticated"
    hint = "Run: gh auth login" if not ok else None
    _add_check(checks, "gh auth", ok, False, detail, hint)


def cmd_preflight(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    full = bool(getattr(args, "full", False))

    checks: list[dict[str, Any]] = []
    _check_python_version(checks)
    _check_command(checks, "git", True, "Install git")
    _check_command(checks, "gh", False, "Install gh for GitHub operations")
    _check_gh_auth(checks)

    if full:
        _check_command(checks, "pytest", True, "Install pytest (pip install -e '.[ci]')")
        _check_command(checks, "ruff", True, "Install ruff (pip install -e '.[ci]')")
        _check_command(checks, "black", True, "Install black (pip install -e '.[ci]')")
        _check_command(checks, "isort", True, "Install isort (pip install -e '.[ci]')")
        _check_command(checks, "mvn", False, "Install Maven for Java smoke tests")
        _check_command(checks, "gradle", False, "Install Gradle for Java smoke tests")
        _check_command(checks, "java", False, "Install Java for Java smoke tests")
        _check_command(checks, "bandit", False, "Install bandit (pip install -e '.[ci]')")
        _check_command(checks, "pip-audit", False, "Install pip-audit (pip install -e '.[ci]')")
        _check_command(checks, "mutmut", False, "Install mutmut (pip install -e '.[ci]')")

    required_failures = [c for c in checks if c["required"] and c["status"] != "ok"]
    exit_code = EXIT_FAILURE if required_failures else EXIT_SUCCESS

    summary = f"{len(required_failures)} required checks failed" if required_failures else "Preflight OK"

    if json_mode:
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            data={"checks": checks},
        )

    for check in checks:
        status = check["status"].upper()
        name = check["name"]
        detail = check["detail"]
        line = f"[{status}] {name}: {detail}"
        print(line)
        hint = check.get("hint")
        if hint:
            print(f"  -> {hint}")

    return exit_code
