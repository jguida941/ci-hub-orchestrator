#!/usr/bin/env python3
"""
Validate that workflow summaries and artifacts match report.json tool flags.

Usage:
  python scripts/validate_summary.py --report report.json \
    [--summary summary.md] [--reports-dir all-reports] [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

JAVA_SUMMARY_MAP = {
    "JaCoCo Coverage": "jacoco",
    "PITest": "pitest",
    "Checkstyle": "checkstyle",
    "PMD": "pmd",
    "SpotBugs": "spotbugs",
    "OWASP Dependency-Check": "owasp",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    # Added for unified summary format
    "jqwik": "jqwik",
    "CodeQL": "codeql",
    "Docker": "docker",
}

PYTHON_SUMMARY_MAP = {
    "pytest": "pytest",
    "mutmut": "mutmut",
    "Ruff": "ruff",
    "Black": "black",
    "isort": "isort",
    "mypy": "mypy",
    "Bandit": "bandit",
    "pip-audit": "pip_audit",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    # Added for unified summary format
    "Hypothesis": "hypothesis",
    "CodeQL": "codeql",
    "Docker": "docker",
}

# PRIMARY VALIDATION: Check metrics in report.json for proof of execution
# Format: list of dot-paths (e.g., "results.coverage")
# Empty list = trust step outcome (no metrics to check)
JAVA_TOOL_METRICS = {
    "jacoco": ["results.coverage"],
    "pitest": ["results.mutation_score"],
    "checkstyle": ["tool_metrics.checkstyle_issues"],
    "spotbugs": ["tool_metrics.spotbugs_issues"],
    "pmd": ["tool_metrics.pmd_violations"],
    "owasp": ["tool_metrics.owasp_critical", "tool_metrics.owasp_high"],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "jqwik": ["results.tests_passed"],  # jqwik runs as part of tests
    "codeql": [],  # uploads to GitHub Security tab
    "docker": [],  # produces images
}

PYTHON_TOOL_METRICS = {
    "pytest": ["results.tests_passed", "results.coverage"],
    "mutmut": ["results.mutation_score"],
    "ruff": ["tool_metrics.ruff_errors"],
    "black": ["tool_metrics.black_issues"],
    "isort": ["tool_metrics.isort_issues"],
    "mypy": ["tool_metrics.mypy_errors"],
    "bandit": ["tool_metrics.bandit_high", "tool_metrics.bandit_medium"],
    "pip_audit": ["tool_metrics.pip_audit_vulns"],
    "semgrep": ["tool_metrics.semgrep_findings"],
    "trivy": ["tool_metrics.trivy_critical", "tool_metrics.trivy_high"],
    "hypothesis": ["results.tests_passed"],  # hypothesis runs as part of tests
    "codeql": [],  # uploads to GitHub Security tab
    "docker": [],  # produces images
}

# BACKUP VALIDATION: File artifacts (when --reports-dir provided)
JAVA_ARTIFACTS = {
    "jacoco": ["**/target/site/jacoco/jacoco.xml"],
    "checkstyle": ["**/checkstyle-result.xml"],
    "spotbugs": ["**/spotbugsXml.xml"],
    "pmd": ["**/pmd.xml"],
    "owasp": ["**/dependency-check-report.json"],
    "pitest": ["**/target/pit-reports/mutations.xml"],
    "semgrep": ["**/semgrep-report.json"],
    "trivy": ["**/trivy-report.json"],
}

PYTHON_ARTIFACTS = {
    "pytest": ["**/coverage.xml", "**/test-results.xml", "**/pytest-junit.xml"],
    "ruff": ["**/ruff-report.json"],
    "bandit": ["**/bandit-report.json"],
    "pip_audit": ["**/pip-audit-report.json"],
    "black": ["**/black-output.txt"],
    "isort": ["**/isort-output.txt"],
    "mypy": ["**/mypy-output.txt"],
    "mutmut": ["**/mutmut-run.log"],
    "hypothesis": ["**/hypothesis-output.txt"],
    "semgrep": ["**/semgrep-report.json"],
    "trivy": ["**/trivy-report.json"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate summaries and artifacts against report.json tool flags")
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--summary", help="Path to summary markdown (optional)")
    parser.add_argument(
        "--reports-dir",
        help="Directory containing tool artifacts (optional)",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings")
    parser.add_argument("--debug", action="store_true", help="Show debug output for validation")
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report.json must be a JSON object")
    return data


def detect_language(report: dict[str, Any]) -> str:
    if "java_version" in report:
        return "java"
    if "python_version" in report:
        return "python"
    raise ValueError("Unable to determine language from report.json")


def parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None


def parse_summary_tools(
    summary_text: str,
) -> tuple[dict[str, bool], dict[str, bool], dict[str, bool]]:
    """Parse Tools Enabled table, returning (configured, ran, success) dicts."""
    lines = summary_text.splitlines()
    in_tools = False
    configured: dict[str, bool] = {}
    ran: dict[str, bool] = {}
    success: dict[str, bool] = {}
    for line in lines:
        if line.strip() == "## Tools Enabled":
            in_tools = True
            continue
        if in_tools and line.startswith("## "):
            break
        if not in_tools:
            continue
        if "|" not in line:
            continue
        if line.strip().startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        # Skip header row
        if cells[1].lower() == "tool" or cells[2].lower() in ("enabled", "configured"):
            continue
        tool = cells[1]
        # New 5-column format: Category | Tool | Configured | Ran | Success
        if len(cells) >= 5:
            conf_val = parse_bool(cells[2])
            ran_val = parse_bool(cells[3])
            success_val = parse_bool(cells[4])
            if conf_val is not None:
                configured[tool] = conf_val
            if ran_val is not None:
                ran[tool] = ran_val
            if success_val is not None:
                success[tool] = success_val
        # Old 4-column format: Category | Tool | Configured | Ran
        elif len(cells) >= 4:
            conf_val = parse_bool(cells[2])
            ran_val = parse_bool(cells[3])
            if conf_val is not None:
                configured[tool] = conf_val
            if ran_val is not None:
                ran[tool] = ran_val
                success[tool] = ran_val  # Assume success = ran for old format
        else:
            # Old 3-column format: Category | Tool | Enabled
            enabled = parse_bool(cells[2])
            if enabled is not None:
                configured[tool] = enabled
                ran[tool] = enabled
                success[tool] = enabled
    return configured, ran, success


def iter_existing_patterns(root: Path, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def get_nested_value(data: dict, path: str) -> Any:
    """Get a nested value from dict using dot notation (e.g., 'results.coverage')."""
    keys = path.split(".")
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def check_metrics_exist(
    report: dict[str, Any],
    tool: str,
    metric_paths: list[str],
) -> tuple[bool, list[str]]:
    """Check if any expected metric exists in report.json for a tool.

    Returns (found, debug_messages) tuple.
    """
    if not metric_paths:
        # No metrics to check, trust step outcome
        return True, [f"Debug: {tool} has no metrics, trusting step outcome"]

    found_metrics = []
    for path in metric_paths:
        value = get_nested_value(report, path)
        if value is not None:
            found_metrics.append(f"{path}={value}")

    if found_metrics:
        return True, [f"Debug: {tool} verified via metrics: {', '.join(found_metrics)}"]
    return False, [f"Debug: {tool} missing expected metrics: {metric_paths}"]


def compare_summary(
    summary_configured: dict[str, bool],
    summary_ran: dict[str, bool],
    tools_configured: dict[str, Any],
    tools_ran: dict[str, Any],
    mapping: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    for label, key in mapping.items():
        # Check configured values
        if tools_configured and key in tools_configured:
            expected_conf = bool(tools_configured.get(key))
            if label in summary_configured:
                actual_conf = summary_configured[label]
                if actual_conf != expected_conf:
                    warnings.append(f"configured mismatch for {label}: summary={actual_conf} report={expected_conf}")

        # Check ran values
        if key not in tools_ran:
            warnings.append(f"report.json missing tools_ran.{key}")
            continue
        expected_ran = bool(tools_ran.get(key))
        if label not in summary_ran:
            warnings.append(f"summary missing tool row: {label}")
            continue
        actual_ran = summary_ran[label]
        if actual_ran != expected_ran:
            warnings.append(f"ran mismatch for {label}: summary={actual_ran} report={expected_ran}")
    return warnings


def validate_tool_execution(
    report: dict[str, Any],
    tools_ran: dict[str, Any],
    tools_success: dict[str, Any],
    metrics_map: dict[str, list[str]],
    artifact_map: dict[str, list[str]] | None = None,
    reports_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Validate tool execution using metrics (primary) and artifacts (backup).

    Returns (warnings, debug_messages) tuple.
    """
    warnings: list[str] = []
    debug: list[str] = []

    for tool, metric_paths in metrics_map.items():
        ran = bool(tools_ran.get(tool))
        succeeded = bool(tools_success.get(tool))

        if not ran:
            debug.append(f"Debug: {tool} did not run, skipping validation")
            continue

        # PRIMARY: Check metrics in report.json
        metrics_found, metric_debug = check_metrics_exist(report, tool, metric_paths)
        debug.extend(metric_debug)

        if metrics_found:
            # Metrics verified, optionally check artifacts for consistency
            if artifact_map and reports_dir and tool in artifact_map:
                patterns = artifact_map[tool]
                if patterns and not iter_existing_patterns(reports_dir, patterns):
                    debug.append(
                        f"Debug: {tool} has metrics but missing artifacts "
                        f"(patterns: {patterns}) - metrics take precedence"
                    )
            continue

        # BACKUP: Metrics not found, check artifacts
        if artifact_map and reports_dir and tool in artifact_map:
            patterns = artifact_map[tool]
            if patterns and iter_existing_patterns(reports_dir, patterns):
                debug.append(
                    f"Debug: {tool} missing metrics but artifacts found - "
                    "consider adding metrics for primary validation"
                )
                continue

        # Neither metrics nor artifacts found
        if succeeded:
            warnings.append(
                f"tool '{tool}' marked as ran+success but no proof found (expected metrics: {metric_paths})"
            )
        else:
            debug.append(f"Debug: {tool} ran but failed, no metrics expected")

    return warnings, debug


def compare_configured_vs_ran(
    tools_configured: dict[str, Any],
    tools_ran: dict[str, Any],
) -> list[str]:
    """Check for drift between what was configured and what actually ran."""
    warnings: list[str] = []
    for tool, configured in tools_configured.items():
        if tool not in tools_ran:
            continue
        ran = tools_ran.get(tool, False)
        if configured and not ran:
            warnings.append(f"DRIFT: '{tool}' was configured=true but did NOT run (ran=false)")
    return warnings


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"report.json not found: {report_path}", file=sys.stderr)
        return 2

    report = load_report(report_path)
    language = detect_language(report)
    tools_ran = report.get("tools_ran", {})
    tools_configured = report.get("tools_configured", {})
    tools_success = report.get("tools_success", {})
    if not isinstance(tools_ran, dict):
        print("report.json missing tools_ran object", file=sys.stderr)
        return 2

    warnings: list[str] = []
    debug_messages: list[str] = []
    summary_success: dict[str, bool] = {}

    # Check for drift between configured and ran
    if tools_configured:
        warnings.extend(compare_configured_vs_ran(tools_configured, tools_ran))

    if args.summary:
        summary_path = Path(args.summary)
        if not summary_path.exists():
            print(f"summary file not found: {summary_path}", file=sys.stderr)
            return 2
        summary_configured, summary_ran, summary_success = parse_summary_tools(summary_path.read_text(encoding="utf-8"))
        mapping = JAVA_SUMMARY_MAP if language == "java" else PYTHON_SUMMARY_MAP
        warnings.extend(compare_summary(summary_configured, summary_ran, tools_configured, tools_ran, mapping))

    # Validate tool execution using metrics (primary) and artifacts (backup)
    metrics_map = JAVA_TOOL_METRICS if language == "java" else PYTHON_TOOL_METRICS
    artifact_map = JAVA_ARTIFACTS if language == "java" else PYTHON_ARTIFACTS

    # Use success status from report.json if available, otherwise from summary
    mapping = JAVA_SUMMARY_MAP if language == "java" else PYTHON_SUMMARY_MAP
    effective_success = dict(tools_success)
    for label, key in mapping.items():
        if key not in effective_success and label in summary_success:
            effective_success[key] = summary_success[label]

    # Setup reports_dir if provided
    reports_dir = None
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
        if not reports_dir.exists():
            print(f"reports dir not found: {reports_dir}", file=sys.stderr)
            return 2

    # Run validation
    tool_warnings, tool_debug = validate_tool_execution(
        report=report,
        tools_ran=tools_ran,
        tools_success=effective_success,
        metrics_map=metrics_map,
        artifact_map=artifact_map,
        reports_dir=reports_dir,
    )
    warnings.extend(tool_warnings)
    debug_messages.extend(tool_debug)

    # Print debug messages if requested
    if args.debug and debug_messages:
        print("Validation debug output:")
        for msg in debug_messages:
            print(f"  {msg}")

    if warnings:
        print("Summary validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        return 1 if args.strict else 0

    print("Summary validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
