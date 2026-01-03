"""Parser setup for report commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_report_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    report = subparsers.add_parser("report", help="Build reports and summaries")
    add_json_flag(report)
    report.set_defaults(func=handlers.cmd_report)
    report_sub = report.add_subparsers(dest="subcommand", required=True)

    report_build = report_sub.add_parser("build", help="Build report.json from tool outputs")
    add_json_flag(report_build)
    report_build.add_argument("--repo", default=".", help="Path to repo (default: .)")
    report_build.add_argument("--workdir", help="Override workdir/subdir")
    report_build.add_argument("--correlation-id", help="Hub correlation id")
    report_build.add_argument(
        "--output-dir",
        default=".cihub",
        help="Output directory for reports (default: .cihub)",
    )
    report_build.add_argument(
        "--tool-dir",
        help="Directory containing tool output JSON files",
    )
    report_build.add_argument("--report", help="Override report.json path")
    report_build.add_argument("--summary", help="Override summary.md path")
    report_build.set_defaults(func=handlers.cmd_report)

    report_summary = report_sub.add_parser("summary", help="Render summary from report.json")
    add_json_flag(report_summary)
    report_summary.add_argument("--report", required=True, help="Path to report.json")
    report_summary.add_argument("--output", help="Output summary.md path")
    report_summary.add_argument(
        "--write-github-summary",
        action="store_true",
        help="Write to GITHUB_STEP_SUMMARY if set",
    )
    report_summary.set_defaults(func=handlers.cmd_report)

    report_outputs = report_sub.add_parser("outputs", help="Write workflow outputs from report.json")
    add_json_flag(report_outputs)
    report_outputs.add_argument("--report", required=True, help="Path to report.json")
    report_outputs.add_argument("--output", help="Path to write outputs (defaults to GITHUB_OUTPUT)")
    report_outputs.set_defaults(func=handlers.cmd_report)

    report_aggregate = report_sub.add_parser("aggregate", help="Aggregate hub reports across repos")
    add_json_flag(report_aggregate)
    report_aggregate.add_argument(
        "--reports-dir",
        help="Directory containing downloaded report artifacts (hub-run-all mode)",
    )
    report_aggregate.add_argument(
        "--dispatch-dir",
        default="dispatch-artifacts",
        help="Directory containing dispatch metadata artifacts",
    )
    report_aggregate.add_argument(
        "--output",
        default="hub-report.json",
        help="Path to write aggregated report JSON",
    )
    report_aggregate.add_argument("--summary-file", help="Path to write summary markdown")
    report_aggregate.add_argument(
        "--details-output",
        help="Path to write per-repo detail markdown",
    )
    report_aggregate.add_argument(
        "--write-github-summary",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    report_aggregate.add_argument(
        "--include-details",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include per-repo details in the summary output",
    )
    report_aggregate.add_argument(
        "--defaults-file",
        default="config/defaults.yaml",
        help="Defaults file for threshold checks",
    )
    report_aggregate.add_argument("--token", help="GitHub token for artifact access")
    report_aggregate.add_argument(
        "--token-env",
        default="HUB_DISPATCH_TOKEN",
        help="Env var name to read token from (default: HUB_DISPATCH_TOKEN)",
    )
    report_aggregate.add_argument("--total-repos", type=int, help="Total expected repos")
    report_aggregate.add_argument("--hub-run-id", help="Override hub run id")
    report_aggregate.add_argument("--hub-event", help="Override hub event name")
    report_aggregate.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Polling timeout in seconds (default: 1800)",
    )
    report_aggregate.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any repo fails or thresholds exceeded",
    )
    report_aggregate.set_defaults(func=handlers.cmd_report)

    report_validate = report_sub.add_parser("validate", help="Validate report.json structure and content")
    add_json_flag(report_validate)
    report_validate.add_argument("--report", required=True, help="Path to report.json")
    report_validate.add_argument(
        "--expect",
        choices=["clean", "issues"],
        default="clean",
        help="Expected mode: 'clean' for passing builds, 'issues' for failing fixtures",
    )
    report_validate.add_argument(
        "--coverage-min",
        type=int,
        default=70,
        help="Minimum coverage percentage (default: 70)",
    )
    report_validate.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (not just errors)",
    )
    report_validate.add_argument(
        "--verbose",
        action="store_true",
        help="Show all checks (including passed ones)",
    )
    report_validate.add_argument("--summary", help="Path to summary.md for cross-checking")
    report_validate.add_argument("--reports-dir", help="Directory containing tool artifacts")
    report_validate.add_argument(
        "--debug",
        action="store_true",
        help="Show debug output for validation",
    )
    report_validate.set_defaults(func=handlers.cmd_report)

    report_dashboard = report_sub.add_parser(
        "dashboard", help="Generate HTML or JSON dashboard from aggregated reports"
    )
    add_json_flag(report_dashboard)
    report_dashboard.add_argument(
        "--reports-dir",
        required=True,
        help="Directory containing report.json files to aggregate",
    )
    report_dashboard.add_argument(
        "--output",
        required=True,
        help="Output file path (e.g., dashboard.html or report.json)",
    )
    report_dashboard.add_argument(
        "--format",
        choices=["json", "html"],
        default="html",
        help="Output format (default: html)",
    )
    report_dashboard.add_argument(
        "--schema-mode",
        choices=["warn", "strict"],
        default="warn",
        help="Schema validation: 'warn' includes non-2.0, 'strict' skips them",
    )
    report_dashboard.set_defaults(func=handlers.cmd_report)

    report_security_summary = report_sub.add_parser("security-summary", help="Render hub security summaries")
    report_security_summary.add_argument(
        "--mode",
        choices=["repo", "zap", "overall"],
        default="repo",
        help="Summary mode",
    )
    report_security_summary.add_argument("--repo", default="", help="Repository name")
    report_security_summary.add_argument("--language", default="python", help="Repository language")
    report_security_summary.add_argument("--has-source", default="false", help="Source code present")
    report_security_summary.add_argument("--pip-audit-vulns", type=int, default=0, help="pip-audit vuln count")
    report_security_summary.add_argument("--bandit-high", type=int, default=0, help="Bandit high count")
    report_security_summary.add_argument("--ruff-issues", type=int, default=0, help="Ruff security issue count")
    report_security_summary.add_argument("--owasp-critical", type=int, default=0, help="OWASP critical count")
    report_security_summary.add_argument("--owasp-high", type=int, default=0, help="OWASP high count")
    report_security_summary.add_argument("--repo-present", default="false", help="Repo checkout succeeded")
    report_security_summary.add_argument("--run-zap", default="false", help="ZAP run requested")
    report_security_summary.add_argument("--has-docker", default="false", help="Docker Compose present")
    report_security_summary.add_argument("--repo-count", type=int, default=0, help="Total repos scanned")
    report_security_summary.add_argument("--run-number", type=int, default=0, help="Run number")
    report_security_summary.add_argument("--summary", help="Write summary to file")
    report_security_summary.add_argument(
        "--write-github-summary",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    report_security_summary.set_defaults(func=handlers.cmd_report)

    report_smoke_summary = report_sub.add_parser("smoke-summary", help="Render smoke test summaries")
    report_smoke_summary.add_argument(
        "--mode",
        choices=["repo", "overall"],
        default="repo",
        help="Summary mode",
    )
    report_smoke_summary.add_argument("--owner", default="", help="Repo owner")
    report_smoke_summary.add_argument("--repo", default="", help="Repo name")
    report_smoke_summary.add_argument("--branch", default="", help="Repo branch")
    report_smoke_summary.add_argument("--language", default="python", help="Repo language")
    report_smoke_summary.add_argument("--config", default="", help="Config name")
    report_smoke_summary.add_argument("--tests-total", type=int, default=0, help="Total tests")
    report_smoke_summary.add_argument("--tests-failed", type=int, default=0, help="Failed tests")
    report_smoke_summary.add_argument("--coverage", type=int, default=0, help="Coverage percent")
    report_smoke_summary.add_argument("--coverage-lines", default="0 / 0", help="Coverage lines")
    report_smoke_summary.add_argument("--checkstyle-violations", type=int, default=0, help="Checkstyle violations")
    report_smoke_summary.add_argument("--spotbugs-issues", type=int, default=0, help="SpotBugs issues")
    report_smoke_summary.add_argument("--ruff-errors", type=int, default=0, help="Ruff errors")
    report_smoke_summary.add_argument("--ruff-security", type=int, default=0, help="Ruff security issues")
    report_smoke_summary.add_argument("--black-issues", type=int, default=0, help="Black issues")
    report_smoke_summary.add_argument("--repo-count", type=int, default=0, help="Total repos")
    report_smoke_summary.add_argument("--run-number", type=int, default=0, help="Run number")
    report_smoke_summary.add_argument("--event-name", default="", help="Trigger event")
    report_smoke_summary.add_argument("--test-result", default="success", help="Matrix job result")
    report_smoke_summary.add_argument("--summary", help="Write summary to file")
    report_smoke_summary.add_argument(
        "--write-github-summary",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    report_smoke_summary.set_defaults(func=handlers.cmd_report)

    report_kyverno_summary = report_sub.add_parser("kyverno-summary", help="Render Kyverno summaries")
    report_kyverno_summary.add_argument("--policies-dir", default="policies", help="Policies directory")
    report_kyverno_summary.add_argument("--validated", type=int, default=0, help="Validated policy count")
    report_kyverno_summary.add_argument("--failed", type=int, default=0, help="Failed policy count")
    report_kyverno_summary.add_argument("--run-tests", default="false", help="Whether tests were run")
    report_kyverno_summary.add_argument(
        "--title",
        default="# Kyverno Policy Validation",
        help="Summary title",
    )
    report_kyverno_summary.add_argument("--summary", help="Write summary to file")
    report_kyverno_summary.add_argument(
        "--write-github-summary",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    report_kyverno_summary.set_defaults(func=handlers.cmd_report)

    report_orchestrator_summary = report_sub.add_parser("orchestrator-summary", help="Render orchestrator summaries")
    report_orchestrator_summary.add_argument(
        "--mode",
        choices=["load-config", "trigger-record"],
        default="load-config",
        help="Summary mode",
    )
    report_orchestrator_summary.add_argument("--repo-count", type=int, default=0, help="Repo count")
    report_orchestrator_summary.add_argument("--owner", default="", help="Repo owner")
    report_orchestrator_summary.add_argument("--repo", default="", help="Repo name")
    report_orchestrator_summary.add_argument("--language", default="", help="Repo language")
    report_orchestrator_summary.add_argument("--branch", default="", help="Repo branch")
    report_orchestrator_summary.add_argument("--workflow-id", default="", help="Workflow ID")
    report_orchestrator_summary.add_argument("--run-id", default="", help="Run ID")
    report_orchestrator_summary.add_argument("--status", default="Triggered", help="Run status")
    report_orchestrator_summary.add_argument("--summary", help="Write summary to file")
    report_orchestrator_summary.add_argument(
        "--write-github-summary",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write summary to GITHUB_STEP_SUMMARY",
    )
    report_orchestrator_summary.set_defaults(func=handlers.cmd_report)
