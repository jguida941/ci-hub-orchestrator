"""Summary generation helpers for various report types."""

from __future__ import annotations

import argparse
from pathlib import Path

from cihub.utils.progress import _bar

from .helpers import _coerce_bool


def _security_repo_summary(args: argparse.Namespace) -> str:
    has_source = _coerce_bool(args.has_source)
    codeql_status = "Complete" if has_source else "Skipped (no source code)"
    lines = [
        f"# Security & Supply Chain: {args.repo}",
        "",
        f"**Language:** {args.language}",
        "",
        "---",
        "",
        "## Jobs",
        "",
        "| Job | Status | Duration |",
        "|-----|--------|----------|",
    ]
    if args.language == "python":
        lines.extend(
            [
                f"| pip-audit | {args.pip_audit_vulns} vulns | - |",
                f"| bandit | {args.bandit_high} high severity | - |",
                f"| ruff-security | {args.ruff_issues} issues | - |",
                f"| codeql | {codeql_status} | - |",
                "| sbom | Generated | - |",
            ]
        )
    else:
        lines.extend(
            [
                f"| OWASP | {args.owasp_critical} critical, {args.owasp_high} high | - |",
                f"| codeql | {codeql_status} | - |",
                "| sbom | Generated | - |",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Artifacts",
            "",
            "| Name | Size | Digest |",
            "|------|------|--------|",
            f"| sbom-{args.repo}.spdx.json | - | - |",
        ]
    )
    return "\n".join(lines)


def _security_zap_summary(args: argparse.Namespace) -> str:
    repo_present = _coerce_bool(args.repo_present)
    run_zap = _coerce_bool(args.run_zap)
    has_docker = _coerce_bool(args.has_docker)
    if not repo_present:
        status = "Skipped - Repo checkout failed"
    elif not run_zap:
        status = "Skipped - run_zap input is false"
    elif has_docker:
        status = "Scan completed. See artifacts for detailed report."
    else:
        status = "Skipped - No docker-compose.yml found"
    return "\n".join([f"## ZAP DAST Scan: {args.repo}", status])


def _security_overall_summary(args: argparse.Namespace) -> str:
    lines = [
        "# Security & Supply Chain Summary",
        "",
        f"**Repositories Scanned:** {args.repo_count}",
        f"**Run:** #{args.run_number}",
        "",
        "## Tools Executed",
        "",
        "| Tool | Purpose |",
        "|------|---------|",
        "| CodeQL | Static Application Security Testing (SAST) |",
        "| SBOM | Software Bill of Materials generation |",
        "| pip-audit / OWASP | Dependency vulnerability scanning |",
        "| Bandit / Ruff-S | Python security linting |",
        "| ZAP | Dynamic Application Security Testing (DAST) |",
    ]
    return "\n".join(lines)


def _smoke_repo_summary(args: argparse.Namespace) -> str:
    header = [
        f"# Smoke Test Results: {args.owner}/{args.repo}",
        "",
        f"**Branch:** `{args.branch}` | **Language:** `{args.language}` | **Config:** `{args.config}`",
        "",
        "---",
        "",
    ]
    if args.language == "java":
        cov = int(args.coverage)
        lines = [
            "## Java Smoke Test Results",
            "",
            "| Metric | Result | Status |",
            "|--------|--------|--------|",
            f"| **Unit Tests** | {args.tests_total} executed | {'PASS' if args.tests_total > 0 else 'FAIL'} |",
            f"| **Test Failures** | {args.tests_failed} failed | {'WARN' if args.tests_failed > 0 else 'PASS'} |",
            f"| **Coverage (JaCoCo)** | {cov}% {_bar(cov)} | {'PASS' if cov >= 50 else 'WARN'} |",
            (
                f"| **Checkstyle** | {args.checkstyle_violations} violations | "
                f"{'WARN' if args.checkstyle_violations > 0 else 'PASS'} |"
            ),
            (
                f"| **SpotBugs** | {args.spotbugs_issues} potential bugs | "
                f"{'WARN' if args.spotbugs_issues > 0 else 'PASS'} |"
            ),
            "",
            f"**Coverage Details:** {args.coverage_lines} instructions covered",
            "",
            "### Smoke Test Status",
            "**PASS** - Core Java tools executed successfully"
            if args.tests_total > 0 and cov > 0
            else "**FAIL** - Missing test execution or coverage data",
        ]
        return "\n".join(header + lines)

    cov = int(args.coverage)
    lines = [
        "## Python Smoke Test Results",
        "",
        "| Metric | Result | Status |",
        "|--------|--------|--------|",
        f"| **Unit Tests** | {args.tests_total} passed | {'PASS' if args.tests_total > 0 else 'FAIL'} |",
        f"| **Test Failures** | {args.tests_failed} failed | {'WARN' if args.tests_failed > 0 else 'PASS'} |",
        f"| **Coverage (pytest-cov)** | {cov}% {_bar(cov)} | {'PASS' if cov >= 50 else 'WARN'} |",
        f"| **Ruff Lint** | {args.ruff_errors} issues | {'WARN' if args.ruff_errors > 0 else 'PASS'} |",
        (
            f"| **Black Format** | {args.black_issues} files need reformatting | "
            f"{'WARN' if args.black_issues > 0 else 'PASS'} |"
        ),
        "",
        f"**Security:** {args.ruff_security} security-related issues",
        "",
        "### Smoke Test Status",
        "**PASS** - Core Python tools executed successfully"
        if args.tests_total > 0 and cov > 0
        else "**FAIL** - Missing test execution or coverage data",
    ]
    return "\n".join(header + lines)


def _smoke_overall_summary(args: argparse.Namespace) -> str:
    status = "PASSED" if args.test_result == "success" else "FAILED"
    lines = [
        "# Smoke Test Summary",
        "",
        f"**Total Test Repositories:** {args.repo_count}",
        f"**Run Number:** #{args.run_number}",
        f"**Trigger:** {args.event_name}",
        f"**Status:** {status}",
        "",
        "---",
        "",
        "## What Was Tested",
        "",
        "The smoke test validates core hub functionality:",
        "",
        "- Repository discovery and configuration loading",
        "- Language detection (Java and Python)",
        "- Core tool execution (coverage, linting, style checks)",
        "- Artifact generation and upload",
        "- Summary report generation",
    ]
    return "\n".join(lines)


def _kyverno_summary(args: argparse.Namespace) -> str:
    policies_dir = Path(args.policies_dir)
    lines = [
        args.title,
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Policies Validated | {args.validated} |",
        f"| Validation Failures | {args.failed} |",
        f"| Tests Run | {args.run_tests} |",
        "",
        "## Policies Directory",
        f"`{policies_dir}`",
    ]

    if policies_dir.is_dir():
        lines.extend(["", "| Policy | Status |", "|--------|--------|"])
        for policy in sorted(policies_dir.glob("*.y*ml")):
            lines.append(f"| `{policy.name}` | Validated |")

    lines.extend(["", "---"])
    return "\n".join(lines)


def _orchestrator_load_summary(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            "## Hub Orchestrator",
            "",
            f"**Repositories to build:** {args.repo_count}",
        ]
    )


def _orchestrator_trigger_summary(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            f"## {args.repo}",
            "",
            f"- **Owner:** {args.owner}",
            f"- **Language:** {args.language}",
            f"- **Branch:** {args.branch}",
            f"- **Workflow:** {args.workflow_id}",
            f"- **Run ID:** {args.run_id or 'pending'}",
            f"- **Status:** {args.status}",
        ]
    )
