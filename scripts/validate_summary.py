#!/usr/bin/env python3
"""
Validate that workflow summaries and artifacts match report.json tool flags.

Usage:
  python scripts/validate_summary.py --report report.json [--summary summary.md] [--reports-dir all-reports] [--strict]
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
}

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
    "pytest": ["**/coverage.xml", "**/test-results.xml"],
    "ruff": ["**/ruff-report.json"],
    "bandit": ["**/bandit-report.json"],
    "pip_audit": ["**/pip-audit-report.json"],
    "semgrep": ["**/semgrep-report.json"],
    "trivy": ["**/trivy-report.json"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate summaries and artifacts against report.json tool flags"
    )
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--summary", help="Path to summary markdown (optional)")
    parser.add_argument(
        "--reports-dir",
        help="Directory containing tool artifacts (optional)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero on warnings"
    )
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


def parse_summary_tools(summary_text: str) -> dict[str, bool]:
    lines = summary_text.splitlines()
    in_tools = False
    results: dict[str, bool] = {}
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
        if cells[1].lower() == "tool" or cells[2].lower() == "enabled":
            continue
        tool = cells[1]
        enabled = parse_bool(cells[2])
        if enabled is None:
            continue
        results[tool] = enabled
    return results


def iter_existing_patterns(root: Path, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def compare_summary(
    summary_tools: dict[str, bool],
    tools_ran: dict[str, Any],
    mapping: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    for label, key in mapping.items():
        if key not in tools_ran:
            warnings.append(f"report.json missing tools_ran.{key}")
            continue
        expected = bool(tools_ran.get(key))
        if label not in summary_tools:
            warnings.append(f"summary missing tool row: {label}")
            continue
        actual = summary_tools[label]
        if actual != expected:
            warnings.append(
                f"summary mismatch for {label}: summary={actual} report={expected}"
            )
    return warnings


def compare_artifacts(
    reports_dir: Path,
    tools_ran: dict[str, Any],
    artifact_map: dict[str, list[str]],
) -> list[str]:
    warnings: list[str] = []
    for tool, patterns in artifact_map.items():
        enabled = bool(tools_ran.get(tool))
        if not enabled:
            continue
        if not iter_existing_patterns(reports_dir, patterns):
            warnings.append(
                f"artifact missing for enabled tool '{tool}' (patterns: {patterns})"
            )
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
    if not isinstance(tools_ran, dict):
        print("report.json missing tools_ran object", file=sys.stderr)
        return 2

    warnings: list[str] = []

    if args.summary:
        summary_path = Path(args.summary)
        if not summary_path.exists():
            print(f"summary file not found: {summary_path}", file=sys.stderr)
            return 2
        summary_tools = parse_summary_tools(summary_path.read_text(encoding="utf-8"))
        mapping = JAVA_SUMMARY_MAP if language == "java" else PYTHON_SUMMARY_MAP
        warnings.extend(compare_summary(summary_tools, tools_ran, mapping))

    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
        if not reports_dir.exists():
            print(f"reports dir not found: {reports_dir}", file=sys.stderr)
            return 2
        artifact_map = JAVA_ARTIFACTS if language == "java" else PYTHON_ARTIFACTS
        warnings.extend(compare_artifacts(reports_dir, tools_ran, artifact_map))

    if warnings:
        print("Summary validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        return 1 if args.strict else 0

    print("Summary validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
