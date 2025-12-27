#!/usr/bin/env python3
"""
Render a unified workflow summary from report.json.

Usage:
  python scripts/render_summary.py --report report.json [--output summary.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

JAVA_TOOL_ROWS = [
    ("Build", "Build", "__build__"),
    ("Testing", "JaCoCo Coverage", "jacoco"),
    ("Testing", "PITest", "pitest"),
    ("Testing", "jqwik", "jqwik"),
    ("Linting", "Checkstyle", "checkstyle"),
    ("Linting", "PMD", "pmd"),
    ("Linting", "SpotBugs", "spotbugs"),
    ("Security", "OWASP Dependency-Check", "owasp"),
    ("Security", "Semgrep", "semgrep"),
    ("Security", "Trivy", "trivy"),
    ("Security", "CodeQL", "codeql"),
    ("Container", "Docker", "docker"),
]

BAR_WIDTH = 20
BAR_FULL = chr(0x2588)
BAR_EMPTY = chr(0x2591)

PYTHON_TOOL_ROWS = [
    ("Testing", "pytest", "pytest"),
    ("Testing", "mutmut", "mutmut"),
    ("Testing", "Hypothesis", "hypothesis"),
    ("Linting", "Ruff", "ruff"),
    ("Linting", "Black", "black"),
    ("Linting", "isort", "isort"),
    ("Linting", "mypy", "mypy"),
    ("Security", "Bandit", "bandit"),
    ("Security", "pip-audit", "pip_audit"),
    ("Security", "Semgrep", "semgrep"),
    ("Security", "Trivy", "trivy"),
    ("Security", "CodeQL", "codeql"),
    ("Container", "Docker", "docker"),
]

THRESHOLD_ROWS = [
    ("Min Coverage", "coverage_min", "%"),
    ("Min Mutation Score", "mutation_score_min", "%"),
    ("OWASP CVSS Fail", "owasp_cvss_fail", ""),
    ("Max Critical Vulns", "max_critical_vulns", ""),
    ("Max High Vulns", "max_high_vulns", ""),
    ("Max Semgrep Findings", "max_semgrep_findings", ""),
    ("Max PMD Violations", "max_pmd_violations", ""),
    ("Max Checkstyle Errors", "max_checkstyle_errors", ""),
    ("Max SpotBugs Bugs", "max_spotbugs_bugs", ""),
    ("Max Ruff Errors", "max_ruff_errors", ""),
    ("Max Black Issues", "max_black_issues", ""),
    ("Max isort Issues", "max_isort_issues", ""),
]

ENV_ROWS = [
    ("Java Version", "java_version"),
    ("Python Version", "python_version"),
    ("Build Tool", "build_tool"),
    ("Repository", "repository"),
    ("Branch", "branch"),
    ("Run Number", "run_number"),
    ("Working Directory", "workdir"),
    ("Project Type", "project_type"),
    ("Artifact Retention", "retention_days"),
    ("Docker Compose", "docker_compose_file"),
    ("Health Endpoint", "docker_health_endpoint"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render workflow summary")
    parser.add_argument("--report", required=True, help="Path to report.json")
    parser.add_argument("--output", help="Path to summary.md (optional)")
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
    return "unknown"


def fmt_bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def fmt_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def fmt_percent(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return f"{value}%"


def fmt_retention(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return f"{value} days"


def fmt_workdir(value: Any) -> str:
    if value in (None, ""):
        return "-"
    if value == ".":
        return "`.` (repo root)"
    return f"`{value}`"


def format_number(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def render_bar(percent: int | None) -> str:
    if percent is None:
        return "-"
    value = max(0, min(100, percent))
    filled = int(value / (100 / BAR_WIDTH))
    bar = f"{BAR_FULL * filled}{BAR_EMPTY * (BAR_WIDTH - filled)}"
    return f"{value}% {bar}"


def build_tools_table(
    report: dict[str, Any], language: str
) -> Iterable[str]:
    tools_configured = report.get("tools_configured", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}
    tools_success = report.get("tools_success", {}) or {}
    results = report.get("results", {}) or {}
    env = report.get("environment", {}) or {}

    rows = JAVA_TOOL_ROWS if language == "java" else PYTHON_TOOL_ROWS
    lines = [
        "## Tools Enabled",
        "| Category | Tool | Configured | Ran | Success |",
        "|----------|------|------------|-----|---------|",
    ]

    for category, label, key in rows:
        if key == "__build__":
            build_tool = env.get("build_tool") or report.get("build_tool") or "build"
            build_status = results.get("build")
            build_success = fmt_bool(build_status == "success")
            lines.append(
                f"| {category} | {build_tool} | true | true | {build_success} |"
            )
            continue
        configured = fmt_bool(tools_configured.get(key, False))
        ran = fmt_bool(tools_ran.get(key, False))
        success = fmt_bool(tools_success.get(key, False))
        lines.append(f"| {category} | {label} | {configured} | {ran} | {success} |")

    lines.append("")
    return lines


def build_thresholds_table(report: dict[str, Any]) -> Iterable[str]:
    thresholds = report.get("thresholds", {}) or {}
    lines = [
        "## Thresholds (effective)",
        "| Setting | Value |",
        "|---------|-------|",
    ]
    for label, key, suffix in THRESHOLD_ROWS:
        value = thresholds.get(key)
        if suffix == "%":
            display = fmt_percent(value)
        else:
            display = fmt_value(value)
        lines.append(f"| {label} | {display} |")
    lines.append("")
    return lines


def build_environment_table(report: dict[str, Any]) -> Iterable[str]:
    env = report.get("environment", {}) or {}
    merged = {
        "java_version": report.get("java_version"),
        "python_version": report.get("python_version"),
        "build_tool": env.get("build_tool") or report.get("build_tool"),
        "repository": report.get("repository"),
        "branch": report.get("branch"),
        "run_number": report.get("run_number"),
        "workdir": env.get("workdir") or report.get("workdir"),
        "project_type": env.get("project_type"),
        "retention_days": env.get("retention_days"),
        "docker_compose_file": env.get("docker_compose_file"),
        "docker_health_endpoint": env.get("docker_health_endpoint"),
    }

    lines = [
        "## Environment",
        "| Setting | Value |",
        "|---------|-------|",
    ]

    for label, key in ENV_ROWS:
        value = merged.get(key)
        if key == "run_number":
            display = f"#{value}" if value else "-"
        elif key == "retention_days":
            display = fmt_retention(value)
        elif key == "workdir":
            display = fmt_workdir(value)
        else:
            display = fmt_value(value)
        lines.append(f"| {label} | {display} |")

    lines.append("")
    return lines


def build_java_metrics(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}

    passed = format_number(results.get("tests_passed"))
    failed = format_number(results.get("tests_failed"))
    skipped = format_number(results.get("tests_skipped"))
    runtime = results.get("tests_runtime_seconds")
    runtime_display = f"{runtime:.3f}s" if isinstance(runtime, (int, float)) else "-"
    total = passed + failed + skipped

    cov = format_number(results.get("coverage"))
    cov_lines_covered = format_number(results.get("coverage_lines_covered"))
    cov_lines_total = format_number(results.get("coverage_lines_total"))
    cov_detail = "-"
    if cov_lines_total > 0:
        cov_detail = f"{cov_lines_covered} / {cov_lines_total} lines covered"

    mut = format_number(results.get("mutation_score"))
    mut_killed = format_number(results.get("mutation_killed"))
    mut_survived = format_number(results.get("mutation_survived"))
    mut_detail = f"{mut_killed} killed, {mut_survived} survived"

    owasp_crit = format_number(tool_metrics.get("owasp_critical"))
    owasp_high = format_number(tool_metrics.get("owasp_high"))
    owasp_med = format_number(tool_metrics.get("owasp_medium"))

    spotbugs = format_number(tool_metrics.get("spotbugs_issues"))
    pmd = format_number(tool_metrics.get("pmd_violations"))
    checkstyle = format_number(tool_metrics.get("checkstyle_issues"))
    semgrep = format_number(tool_metrics.get("semgrep_findings"))
    trivy_crit = format_number(tool_metrics.get("trivy_critical"))
    trivy_high = format_number(tool_metrics.get("trivy_high"))

    jacoco_ran = bool(tools_ran.get("jacoco"))
    pitest_ran = bool(tools_ran.get("pitest"))
    owasp_ran = bool(tools_ran.get("owasp"))
    spotbugs_ran = bool(tools_ran.get("spotbugs"))
    pmd_ran = bool(tools_ran.get("pmd"))
    checkstyle_ran = bool(tools_ran.get("checkstyle"))
    semgrep_ran = bool(tools_ran.get("semgrep"))
    trivy_ran = bool(tools_ran.get("trivy"))

    test_detail = (
        f"Runtime: {runtime_display}, Failures: {failed}, Skipped: {skipped}"
    )
    coverage_value = render_bar(cov) if jacoco_ran else "-"
    coverage_detail = cov_detail if jacoco_ran else "-"
    mutation_value = render_bar(mut) if pitest_ran else "-"
    mutation_detail = mut_detail if pitest_ran else "-"
    owasp_status = "scan complete" if owasp_ran else "-"
    owasp_detail = (
        f"{owasp_crit} crit, {owasp_high} high, {owasp_med} med"
        if owasp_ran
        else "-"
    )
    spotbugs_detail = "Static analysis" if spotbugs_ran else "-"
    pmd_detail = "Code analysis" if pmd_ran else "-"
    checkstyle_detail = "Code style" if checkstyle_ran else "-"
    semgrep_detail = "SAST analysis" if semgrep_ran else "-"
    trivy_detail = "Container scan" if trivy_ran else "-"

    lines = [
        "## QA Metrics (Java)",
        "| Metric | Result | Details |",
        "|--------|--------|---------|",
        f"| Tests | {total} executed | {test_detail} |",
        f"| Line Coverage (JaCoCo) | {coverage_value} | {coverage_detail} |",
        f"| Mutation Score (PITest) | {mutation_value} | {mutation_detail} |",
        f"| Dependency-Check | {owasp_status} | {owasp_detail} |",
        f"| SpotBugs | {spotbugs} bugs | {spotbugs_detail} |",
        f"| PMD | {pmd} violations | {pmd_detail} |",
        f"| Checkstyle | {checkstyle} violations | {checkstyle_detail} |",
        f"| Semgrep | {semgrep} findings | {semgrep_detail} |",
        f"| Trivy | {trivy_crit} crit, {trivy_high} high | {trivy_detail} |",
        "",
    ]
    return lines


def build_python_metrics(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    tools_ran = report.get("tools_ran", {}) or {}

    passed = format_number(results.get("tests_passed"))
    failed = format_number(results.get("tests_failed"))
    skipped = format_number(results.get("tests_skipped"))
    runtime = results.get("tests_runtime_seconds")
    runtime_display = f"{runtime:.3f}s" if isinstance(runtime, (int, float)) else "-"
    total = passed + failed + skipped

    cov = format_number(results.get("coverage"))
    cov_lines_covered = format_number(results.get("coverage_lines_covered"))
    cov_lines_total = format_number(results.get("coverage_lines_total"))
    cov_detail = "-"
    if cov_lines_total > 0:
        cov_detail = f"{cov_lines_covered} / {cov_lines_total} lines covered"

    mut = format_number(results.get("mutation_score"))
    mut_killed = format_number(results.get("mutation_killed"))
    mut_survived = format_number(results.get("mutation_survived"))
    mut_detail = f"{mut_killed} killed, {mut_survived} survived"

    bandit_high = format_number(tool_metrics.get("bandit_high"))
    bandit_med = format_number(tool_metrics.get("bandit_medium"))
    bandit_low = format_number(tool_metrics.get("bandit_low"))
    ruff = format_number(tool_metrics.get("ruff_errors"))
    black = format_number(tool_metrics.get("black_issues"))
    isort = format_number(tool_metrics.get("isort_issues"))
    mypy = format_number(tool_metrics.get("mypy_errors"))
    semgrep = format_number(tool_metrics.get("semgrep_findings"))
    trivy_crit = format_number(tool_metrics.get("trivy_critical"))
    trivy_high = format_number(tool_metrics.get("trivy_high"))

    pytest_ran = bool(tools_ran.get("pytest"))
    mutmut_ran = bool(tools_ran.get("mutmut"))
    ruff_ran = bool(tools_ran.get("ruff"))
    black_ran = bool(tools_ran.get("black"))
    isort_ran = bool(tools_ran.get("isort"))
    mypy_ran = bool(tools_ran.get("mypy"))
    bandit_ran = bool(tools_ran.get("bandit"))
    semgrep_ran = bool(tools_ran.get("semgrep"))
    trivy_ran = bool(tools_ran.get("trivy"))

    test_detail = (
        f"Runtime: {runtime_display}, Failures: {failed}, Skipped: {skipped}"
    )
    coverage_value = render_bar(cov) if pytest_ran else "-"
    coverage_detail = cov_detail if pytest_ran else "-"
    mutation_value = render_bar(mut) if mutmut_ran else "-"
    mutation_detail = mut_detail if mutmut_ran else "-"
    ruff_detail = "Linting" if ruff_ran else "-"
    black_detail = "Format check" if black_ran else "-"
    isort_detail = "Import order" if isort_ran else "-"
    mypy_detail = "Type check" if mypy_ran else "-"
    bandit_detail = "Security scan" if bandit_ran else "-"
    bandit_counts = f"high {bandit_high}, med {bandit_med}, low {bandit_low}"
    semgrep_detail = "SAST analysis" if semgrep_ran else "-"
    trivy_detail = "Container scan" if trivy_ran else "-"

    lines = [
        "## QA Metrics (Python)",
        "| Metric | Result | Details |",
        "|--------|--------|---------|",
        f"| Tests | {total} executed | {test_detail} |",
        f"| Line Coverage (pytest) | {coverage_value} | {coverage_detail} |",
        f"| Mutation Score (mutmut) | {mutation_value} | {mutation_detail} |",
        f"| Ruff | {ruff} issues | {ruff_detail} |",
        f"| Black | {black} issues | {black_detail} |",
        f"| isort | {isort} issues | {isort_detail} |",
        f"| mypy | {mypy} errors | {mypy_detail} |",
        f"| Bandit | {bandit_counts} | {bandit_detail} |",
        f"| Semgrep | {semgrep} findings | {semgrep_detail} |",
        f"| Trivy | {trivy_crit} crit, {trivy_high} high | {trivy_detail} |",
        "",
    ]
    return lines


def build_dependency_severity(report: dict[str, Any]) -> Iterable[str]:
    results = report.get("results", {}) or {}
    severity = report.get("dependency_severity", {}) or {}
    crit = severity.get("critical", results.get("critical_vulns"))
    high = severity.get("high", results.get("high_vulns"))
    med = severity.get("medium", results.get("medium_vulns"))
    low = severity.get("low", results.get("low_vulns"))

    lines = [
        "## Dependency Severity",
        "| Severity | Count |",
        "|----------|-------|",
        f"| Critical | {format_number(crit)} |",
        f"| High | {format_number(high)} |",
        f"| Medium | {format_number(med)} |",
        f"| Low | {format_number(low)} |",
        "",
    ]
    return lines


def build_quality_gates(report: dict[str, Any], language: str) -> Iterable[str]:
    results = report.get("results", {}) or {}
    tool_metrics = report.get("tool_metrics", {}) or {}
    thresholds = report.get("thresholds", {}) or {}
    tools_configured = report.get("tools_configured", {}) or {}

    def gate_status(condition: bool, fail_label: str) -> str:
        return "Passed" if condition else fail_label

    lines = [
        "## Quality Gates",
        "| Check | Status |",
        "|-------|--------|",
    ]

    tests_failed = format_number(results.get("tests_failed"))
    lines.append(f"| Unit Tests | {gate_status(tests_failed == 0, 'Failed')} |")

    if language == "java":
        if tools_configured.get("jacoco", False):
            cov = format_number(results.get("coverage"))
            min_cov = format_number(thresholds.get("coverage_min"))
            cov_status = gate_status(cov >= min_cov, "Failed")
            lines.append(f"| JaCoCo Coverage | {cov_status} |")
        else:
            lines.append("| JaCoCo Coverage | SKIP |")

        if tools_configured.get("pitest", False):
            mut = format_number(results.get("mutation_score"))
            min_mut = format_number(thresholds.get("mutation_score_min"))
            mut_status = gate_status(mut >= min_mut, "Failed")
            lines.append(f"| PITest Mutation | {mut_status} |")
        else:
            lines.append("| PITest Mutation | SKIP |")

        if tools_configured.get("checkstyle", False):
            issues = format_number(tool_metrics.get("checkstyle_issues"))
            max_issues = format_number(thresholds.get("max_checkstyle_errors"))
            lines.append(
                f"| Checkstyle | {gate_status(issues <= max_issues, 'Violations')} |"
            )
        else:
            lines.append("| Checkstyle | SKIP |")

        if tools_configured.get("spotbugs", False):
            issues = format_number(tool_metrics.get("spotbugs_issues"))
            max_issues = format_number(thresholds.get("max_spotbugs_bugs"))
            lines.append(
                f"| SpotBugs | {gate_status(issues <= max_issues, 'Bugs found')} |"
            )
        else:
            lines.append("| SpotBugs | SKIP |")

        if tools_configured.get("pmd", False):
            issues = format_number(tool_metrics.get("pmd_violations"))
            max_issues = format_number(thresholds.get("max_pmd_violations"))
            lines.append(
                f"| PMD | {gate_status(issues <= max_issues, 'Violations')} |"
            )
        else:
            lines.append("| PMD | SKIP |")

        if tools_configured.get("owasp", False):
            crit = format_number(tool_metrics.get("owasp_critical"))
            high = format_number(tool_metrics.get("owasp_high"))
            max_crit = format_number(thresholds.get("max_critical_vulns"))
            max_high = format_number(thresholds.get("max_high_vulns"))
            ok = crit <= max_crit and high <= max_high
            lines.append(f"| OWASP Check | {gate_status(ok, 'Vulnerabilities')} |")
        else:
            lines.append("| OWASP Check | SKIP |")

        if tools_configured.get("semgrep", False):
            findings = format_number(tool_metrics.get("semgrep_findings"))
            max_findings = format_number(thresholds.get("max_semgrep_findings"))
            lines.append(
                f"| Semgrep | {gate_status(findings <= max_findings, 'Findings')} |"
            )
        else:
            lines.append("| Semgrep | SKIP |")

    else:
        if tools_configured.get("pytest", False):
            lines.append(f"| pytest | {gate_status(tests_failed == 0, 'Failed')} |")
        else:
            lines.append("| pytest | SKIP |")

        if tools_configured.get("mutmut", False):
            mut = format_number(results.get("mutation_score"))
            min_mut = format_number(thresholds.get("mutation_score_min"))
            lines.append(f"| mutmut | {gate_status(mut >= min_mut, 'Failed')} |")
        else:
            lines.append("| mutmut | SKIP |")

        if tools_configured.get("ruff", False):
            issues = format_number(tool_metrics.get("ruff_errors"))
            max_issues = format_number(thresholds.get("max_ruff_errors"))
            lines.append(
                f"| Ruff | {gate_status(issues <= max_issues, 'Issues')} |"
            )
        else:
            lines.append("| Ruff | SKIP |")

        if tools_configured.get("black", False):
            issues = format_number(tool_metrics.get("black_issues"))
            max_issues = format_number(thresholds.get("max_black_issues"))
            lines.append(
                f"| Black | {gate_status(issues <= max_issues, 'Issues')} |"
            )
        else:
            lines.append("| Black | SKIP |")

        if tools_configured.get("isort", False):
            issues = format_number(tool_metrics.get("isort_issues"))
            max_issues = format_number(thresholds.get("max_isort_issues"))
            lines.append(
                f"| isort | {gate_status(issues <= max_issues, 'Issues')} |"
            )
        else:
            lines.append("| isort | SKIP |")

        if tools_configured.get("mypy", False):
            issues = format_number(tool_metrics.get("mypy_errors"))
            lines.append(
                f"| mypy | {gate_status(issues == 0, 'Errors')} |"
            )
        else:
            lines.append("| mypy | SKIP |")

        if tools_configured.get("bandit", False):
            high = format_number(tool_metrics.get("bandit_high"))
            max_high = format_number(thresholds.get("max_high_vulns"))
            lines.append(
                f"| Bandit | {gate_status(high <= max_high, 'Findings')} |"
            )
        else:
            lines.append("| Bandit | SKIP |")

        if tools_configured.get("pip_audit", False):
            vulns = format_number(tool_metrics.get("pip_audit_vulns"))
            max_high = format_number(thresholds.get("max_high_vulns"))
            lines.append(
                f"| pip-audit | {gate_status(vulns <= max_high, 'Findings')} |"
            )
        else:
            lines.append("| pip-audit | SKIP |")

        if tools_configured.get("semgrep", False):
            findings = format_number(tool_metrics.get("semgrep_findings"))
            max_findings = format_number(thresholds.get("max_semgrep_findings"))
            lines.append(
                f"| Semgrep | {gate_status(findings <= max_findings, 'Findings')} |"
            )
        else:
            lines.append("| Semgrep | SKIP |")

    lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    report_path = Path(args.report)
    report = load_report(report_path)
    language = detect_language(report)

    sections: list[str] = [
        "# Configuration Summary",
        "",
    ]
    sections.extend(build_tools_table(report, language))
    sections.extend(build_thresholds_table(report))
    sections.extend(build_environment_table(report))
    if language == "java":
        sections.extend(build_java_metrics(report))
    elif language == "python":
        sections.extend(build_python_metrics(report))
    sections.extend(build_dependency_severity(report))
    sections.extend(build_quality_gates(report, language))

    output_text = "\n".join(sections).strip() + "\n"
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
    else:
        sys.stdout.write(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
