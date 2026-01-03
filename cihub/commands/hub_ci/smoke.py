"""Python smoke test commands."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import defusedxml.ElementTree as ET  # Secure XML parsing

from cihub.exit_codes import EXIT_SUCCESS

from . import (
    _resolve_output_path,
    _run_command,
    _write_outputs,
)


def _last_regex_int(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text)
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except ValueError:
        return 0


def cmd_smoke_python_install(args: argparse.Namespace) -> int:
    import sys

    repo_path = Path(args.path).resolve()
    commands = [
        ["python", "-m", "pip", "install", "--upgrade", "pip"],
        ["pip", "install", "pytest", "pytest-cov"],
        ["pip", "install", "ruff", "black"],
    ]
    for cmd in commands:
        proc = _run_command(cmd, repo_path)
        if proc.returncode != 0:
            print(proc.stdout or proc.stderr or "pip install failed", file=sys.stderr)

    req_files = ["requirements.txt", "requirements-dev.txt"]
    for req in req_files:
        req_path = repo_path / req
        if req_path.exists():
            _run_command(["pip", "install", "-r", str(req_path)], repo_path)

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        proc = _run_command(["pip", "install", "-e", ".[dev]"], repo_path)
        if proc.returncode != 0:
            _run_command(["pip", "install", "-e", "."], repo_path)

    return EXIT_SUCCESS


def cmd_smoke_python_tests(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(
        ["pytest", "--cov=.", "--cov-report=xml", "--cov-report=term", "-v"],
        repo_path,
    )
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    passed = _last_regex_int(r"(\d+)\s+passed", output_text)
    failed = _last_regex_int(r"(\d+)\s+failed", output_text)
    skipped = _last_regex_int(r"(\d+)\s+skipped", output_text)

    coverage = 0
    coverage_file = repo_path / "coverage.xml"
    if coverage_file.exists():
        try:
            tree = ET.parse(coverage_file)  # noqa: S314 - trusted CI tool output
            root = tree.getroot()
            coverage = int(float(root.attrib.get("line-rate", "0")) * 100)
        except (ET.ParseError, ValueError):
            coverage = 0

    total = passed + failed + skipped
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "total": str(total),
            "passed": str(passed),
            "failed": str(failed),
            "skipped": str(skipped),
            "coverage": str(coverage),
        },
        output_path,
    )
    print(f"Tests: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Coverage: {coverage}%")
    return EXIT_SUCCESS


def cmd_smoke_python_ruff(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = repo_path / args.report

    proc = _run_command(["ruff", "check", ".", "--output-format=json"], repo_path)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    errors = 0
    security = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            errors = len(data)
            security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    except json.JSONDecodeError:
        errors = 0
        security = 0

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"errors": str(errors), "security": str(security)}, output_path)
    print(f"Ruff: {errors} issues ({security} security-related)")
    return EXIT_SUCCESS


def cmd_smoke_python_black(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(["black", "--check", "."], repo_path)
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    issues = len([line for line in output_text.splitlines() if "would reformat" in line])
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)
    print(f"Black: {issues} files need reformatting")
    return EXIT_SUCCESS
