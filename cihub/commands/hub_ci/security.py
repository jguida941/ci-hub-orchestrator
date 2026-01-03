"""Security scanning commands (bandit, pip-audit, OWASP, ruff security)."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
from pathlib import Path

from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.utils.env import _parse_env_bool

from . import (
    _append_summary,
    _count_pip_audit_vulns,
    _resolve_output_path,
    _resolve_summary_path,
    _run_command,
    _write_outputs,
)


def cmd_bandit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "bandit",
        "-r",
        *args.paths,
        "-f",
        "json",
        "-o",
        str(output_path),
        "--severity-level",
        args.severity,
        "--confidence-level",
        args.confidence,
    ]
    _run_command(cmd, Path("."))

    # Count issues by severity
    high = 0
    medium = 0
    low = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            results = data.get("results", []) if isinstance(data, dict) else []
            high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
            medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
            low = sum(1 for item in results if item.get("issue_severity") == "LOW")
        except json.JSONDecodeError:
            pass

    total = high + medium + low

    # Write summary with breakdown table
    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    fail_on_high = getattr(args, "fail_on_high", True)
    fail_on_medium = getattr(args, "fail_on_medium", False)
    fail_on_low = getattr(args, "fail_on_low", False)

    env_fail_high = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_HIGH"))
    env_fail_medium = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_MEDIUM"))
    env_fail_low = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_LOW"))
    if env_fail_high is not None:
        fail_on_high = env_fail_high
    if env_fail_medium is not None:
        fail_on_medium = env_fail_medium
    if env_fail_low is not None:
        fail_on_low = env_fail_low

    summary = (
        "## Bandit SAST\n\n"
        "| Severity | Count | Fail Threshold |\n"
        "|----------|-------|----------------|\n"
        f"| High | {high} | {'enabled' if fail_on_high else 'disabled'} |\n"
        f"| Medium | {medium} | {'enabled' if fail_on_medium else 'disabled'} |\n"
        f"| Low | {low} | {'enabled' if fail_on_low else 'disabled'} |\n"
        f"| **Total** | **{total}** | |\n"
    )
    _append_summary(summary, summary_path)

    # Check thresholds - fail if any enabled threshold is exceeded
    fail_reasons = []

    if fail_on_high and high > 0:
        fail_reasons.append(f"{high} HIGH")
    if fail_on_medium and medium > 0:
        fail_reasons.append(f"{medium} MEDIUM")
    if fail_on_low and low > 0:
        fail_reasons.append(f"{low} LOW")

    if fail_reasons:
        # Show details for failing severities
        subprocess.run(  # noqa: S603
            ["bandit", "-r", *args.paths, "--severity-level", "low"],  # noqa: S607
            text=True,
        )
        print(f"::error::Found {', '.join(fail_reasons)} severity issues")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def cmd_pip_audit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "pip-audit",
        *sum([["-r", req] for req in args.requirements], []),
        "--format",
        "json",
        "--output",
        str(output_path),
    ]
    _run_command(cmd, Path("."))

    vulns = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            vulns = _count_pip_audit_vulns(data)
        except json.JSONDecodeError:
            vulns = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(
        f"## Dependency Vulnerabilities\nFound: {vulns}\n",
        summary_path,
    )

    if vulns > 0:
        markdown = subprocess.run(  # noqa: S603
            ["pip-audit", "--format", "markdown"],  # noqa: S607
            text=True,
            capture_output=True,
        )
        if markdown.stdout:
            _append_summary(markdown.stdout, summary_path)
        print(f"::error::Found {vulns} dependency vulnerabilities")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def cmd_security_pip_audit(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()
    requirements = args.requirements or []

    for req in requirements:
        req_path = repo_path / req
        if not req_path.exists():
            continue
        _run_command(["pip", "install", "-r", str(req_path)], repo_path)

    proc = _run_command(
        ["pip-audit", "--format=json", "--output", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    if not report_path.exists():
        report_path.write_text("[]", encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            print(f"::warning::pip-audit failed (exit {proc.returncode}): {proc.stderr or 'no output'}")

    vulns = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        vulns = _count_pip_audit_vulns(data)
    except json.JSONDecodeError:
        vulns = 0
        if proc.returncode != 0:
            tool_status = "failed"
            print(f"::warning::pip-audit produced invalid JSON (exit {proc.returncode})")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"vulnerabilities": str(vulns), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_bandit(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    if not report_path.exists():
        report_path.write_text('{"results":[]}', encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            print(f"::warning::bandit failed (exit {proc.returncode}): {proc.stderr or 'no output'}")

    high = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        results = data.get("results", []) if isinstance(data, dict) else []
        high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    except json.JSONDecodeError:
        high = 0
        if proc.returncode != 0:
            tool_status = "failed"
            print(f"::warning::bandit produced invalid JSON (exit {proc.returncode})")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"high": str(high), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_ruff(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["ruff", "check", ".", "--select=S", "--output-format=json"],
        repo_path,
    )
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    tool_status = "success"
    issues = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0
        # ruff returns non-zero when issues found (normal), but invalid JSON is a problem
        tool_status = "failed"
        print(f"::warning::ruff produced invalid JSON (exit {proc.returncode}): {proc.stderr or 'no output'}")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_owasp(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    tool_status = "success"
    proc = None
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        proc = _run_command(
            ["./mvnw", "-B", "-ntp", "org.owasp:dependency-check-maven:check", "-DfailBuildOnCVSS=11"],
            repo_path,
        )
    else:
        tool_status = "skipped"

    reports = list(repo_path.rglob("dependency-check-report.json"))
    report_path = reports[0] if reports else None
    critical = 0
    high = 0
    if report_path and report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            dependencies = data.get("dependencies", []) if isinstance(data, dict) else []
            for dep in dependencies:
                vulns = dep.get("vulnerabilities", []) if isinstance(dep, dict) else []
                for vuln in vulns:
                    severity = str(vuln.get("severity", "")).upper()
                    if severity == "CRITICAL":
                        critical += 1
                    elif severity == "HIGH":
                        high += 1
        except json.JSONDecodeError:
            critical = 0
            high = 0
            if proc and proc.returncode != 0:
                tool_status = "failed"
                print(f"::warning::OWASP dependency-check produced invalid JSON (exit {proc.returncode})")
    elif proc and proc.returncode != 0:
        # Tool ran but produced no report
        tool_status = "failed"
        print(f"::warning::OWASP dependency-check failed (exit {proc.returncode}): no report generated")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"critical": str(critical), "high": str(high), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS
