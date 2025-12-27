"""Report building helpers for cihub ci."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cihub import __version__


@dataclass(frozen=True)
class RunContext:
    repository: str | None
    branch: str | None
    run_id: str | None
    run_number: str | None
    commit: str | None
    correlation_id: str | None
    workflow_ref: str | None
    workdir: str | None
    build_tool: str | None
    retention_days: int | None
    project_type: str | None
    docker_compose_file: str | None
    docker_health_endpoint: str | None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _set_threshold(
    thresholds: dict[str, Any], key: str, value: Any
) -> None:
    if value is None:
        return
    thresholds.setdefault(key, value)


def resolve_thresholds(config: dict[str, Any], language: str) -> dict[str, Any]:
    thresholds = dict(config.get("thresholds", {}) or {})
    if language == "python":
        tools = config.get("python", {}).get("tools", {}) or {}
        pytest_cfg = tools.get("pytest", {}) or {}
        mutmut_cfg = tools.get("mutmut", {}) or {}
        ruff_cfg = tools.get("ruff", {}) or {}
        black_cfg = tools.get("black", {}) or {}
        isort_cfg = tools.get("isort", {}) or {}
        semgrep_cfg = tools.get("semgrep", {}) or {}
        trivy_cfg = tools.get("trivy", {}) or {}

        _set_threshold(thresholds, "coverage_min", pytest_cfg.get("min_coverage"))
        _set_threshold(
            thresholds, "mutation_score_min", mutmut_cfg.get("min_mutation_score")
        )
        _set_threshold(thresholds, "max_ruff_errors", ruff_cfg.get("max_errors"))
        _set_threshold(thresholds, "max_black_issues", black_cfg.get("max_issues"))
        _set_threshold(thresholds, "max_isort_issues", isort_cfg.get("max_issues"))
        _set_threshold(
            thresholds, "max_semgrep_findings", semgrep_cfg.get("max_findings")
        )
        _set_threshold(thresholds, "trivy_cvss_fail", trivy_cfg.get("fail_on_cvss"))
        if "max_pip_audit_vulns" not in thresholds:
            max_high = thresholds.get("max_high_vulns")
            if max_high is not None:
                thresholds["max_pip_audit_vulns"] = max_high
    else:
        tools = config.get("java", {}).get("tools", {}) or {}
        jacoco_cfg = tools.get("jacoco", {}) or {}
        pitest_cfg = tools.get("pitest", {}) or {}
        checkstyle_cfg = tools.get("checkstyle", {}) or {}
        spotbugs_cfg = tools.get("spotbugs", {}) or {}
        pmd_cfg = tools.get("pmd", {}) or {}
        owasp_cfg = tools.get("owasp", {}) or {}
        semgrep_cfg = tools.get("semgrep", {}) or {}

        _set_threshold(thresholds, "coverage_min", jacoco_cfg.get("min_coverage"))
        _set_threshold(
            thresholds, "mutation_score_min", pitest_cfg.get("min_mutation_score")
        )
        _set_threshold(
            thresholds, "max_checkstyle_errors", checkstyle_cfg.get("max_errors")
        )
        _set_threshold(thresholds, "max_spotbugs_bugs", spotbugs_cfg.get("max_bugs"))
        _set_threshold(thresholds, "max_pmd_violations", pmd_cfg.get("max_violations"))
        _set_threshold(thresholds, "owasp_cvss_fail", owasp_cfg.get("fail_on_cvss"))
        _set_threshold(
            thresholds, "max_semgrep_findings", semgrep_cfg.get("max_findings")
        )
    return thresholds


def _get_metric(
    tool_results: dict[str, dict[str, Any]],
    tool: str,
    key: str,
    default: int | float = 0,
) -> int | float:
    metrics = tool_results.get(tool, {}).get("metrics", {})
    return metrics.get(key, default)


def build_python_report(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    tools_configured: dict[str, bool],
    tools_ran: dict[str, bool],
    tools_success: dict[str, bool],
    thresholds: dict[str, Any],
    context: RunContext,
) -> dict[str, Any]:
    pytest_enabled = tools_configured.get("pytest", False)
    tests_failed = int(_get_metric(tool_results, "pytest", "tests_failed", 0))
    tests_passed = int(_get_metric(tool_results, "pytest", "tests_passed", 0))
    tests_skipped = int(_get_metric(tool_results, "pytest", "tests_skipped", 0))
    tests_runtime = _get_metric(tool_results, "pytest", "tests_runtime_seconds", 0.0)

    coverage = int(_get_metric(tool_results, "pytest", "coverage", 0))
    coverage_lines_covered = int(
        _get_metric(tool_results, "pytest", "coverage_lines_covered", 0)
    )
    coverage_lines_total = int(
        _get_metric(tool_results, "pytest", "coverage_lines_total", 0)
    )

    mutation_score = int(_get_metric(tool_results, "mutmut", "mutation_score", 0))
    mutation_killed = int(_get_metric(tool_results, "mutmut", "mutation_killed", 0))
    mutation_survived = int(_get_metric(tool_results, "mutmut", "mutation_survived", 0))

    bandit_high = int(_get_metric(tool_results, "bandit", "bandit_high", 0))
    bandit_med = int(_get_metric(tool_results, "bandit", "bandit_medium", 0))
    bandit_low = int(_get_metric(tool_results, "bandit", "bandit_low", 0))
    pip_audit_vulns = int(_get_metric(tool_results, "pip_audit", "pip_audit_vulns", 0))
    trivy_critical = int(_get_metric(tool_results, "trivy", "trivy_critical", 0))
    trivy_high = int(_get_metric(tool_results, "trivy", "trivy_high", 0))
    trivy_medium = int(_get_metric(tool_results, "trivy", "trivy_medium", 0))
    trivy_low = int(_get_metric(tool_results, "trivy", "trivy_low", 0))

    test_status = "skipped"
    if pytest_enabled:
        test_status = "success" if tests_failed == 0 else "failure"

    results = {
        "test": test_status,
        "coverage": coverage,
        "coverage_lines_covered": coverage_lines_covered,
        "coverage_lines_total": coverage_lines_total,
        "mutation_score": mutation_score,
        "mutation_killed": mutation_killed,
        "mutation_survived": mutation_survived,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "tests_skipped": tests_skipped,
        "tests_runtime_seconds": tests_runtime,
        "critical_vulns": trivy_critical,
        "high_vulns": bandit_high + trivy_high,
        "medium_vulns": bandit_med + trivy_medium,
        "low_vulns": bandit_low + trivy_low,
    }

    tool_metrics = {
        "ruff_errors": _get_metric(tool_results, "ruff", "ruff_errors", 0),
        "mypy_errors": _get_metric(tool_results, "mypy", "mypy_errors", 0),
        "bandit_high": _get_metric(tool_results, "bandit", "bandit_high", 0),
        "bandit_medium": _get_metric(tool_results, "bandit", "bandit_medium", 0),
        "bandit_low": _get_metric(tool_results, "bandit", "bandit_low", 0),
        "black_issues": _get_metric(tool_results, "black", "black_issues", 0),
        "isort_issues": _get_metric(tool_results, "isort", "isort_issues", 0),
        "pip_audit_vulns": pip_audit_vulns,
        "semgrep_findings": _get_metric(tool_results, "semgrep", "semgrep_findings", 0),
        "trivy_critical": trivy_critical,
        "trivy_high": trivy_high,
        "trivy_medium": trivy_medium,
        "trivy_low": trivy_low,
    }

    dependency_severity = {
        "critical": trivy_critical,
        "high": trivy_high,
        "medium": trivy_medium,
        "low": trivy_low,
    }

    report = {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": __version__,
            "workflow_ref": context.workflow_ref or "",
            "generated_at": _timestamp(),
        },
        "repository": context.repository or "",
        "run_id": context.run_id or "",
        "run_number": context.run_number or "",
        "commit": context.commit or "",
        "branch": context.branch or "",
        "hub_correlation_id": context.correlation_id or "",
        "timestamp": _timestamp(),
        "python_version": config.get("python", {}).get("version", ""),
        "results": results,
        "tool_metrics": tool_metrics,
        "tools_configured": tools_configured,
        "tools_ran": tools_ran,
        "tools_success": tools_success,
        "thresholds": thresholds,
        "environment": {
            "workdir": context.workdir,
            "retention_days": context.retention_days,
        },
        "dependency_severity": dependency_severity,
    }
    return report


def build_java_report(
    config: dict[str, Any],
    tool_results: dict[str, dict[str, Any]],
    tools_configured: dict[str, bool],
    tools_ran: dict[str, bool],
    tools_success: dict[str, bool],
    thresholds: dict[str, Any],
    context: RunContext,
) -> dict[str, Any]:
    build_payload = tool_results.get("build", {})
    build_success = bool(build_payload.get("success", False))

    tests_passed = int(_get_metric(tool_results, "build", "tests_passed", 0))
    tests_failed = int(_get_metric(tool_results, "build", "tests_failed", 0))
    tests_skipped = int(_get_metric(tool_results, "build", "tests_skipped", 0))
    tests_runtime = _get_metric(tool_results, "build", "tests_runtime_seconds", 0.0)

    coverage = int(_get_metric(tool_results, "jacoco", "coverage", 0))
    coverage_lines_covered = int(
        _get_metric(tool_results, "jacoco", "coverage_lines_covered", 0)
    )
    coverage_lines_total = int(
        _get_metric(tool_results, "jacoco", "coverage_lines_total", 0)
    )

    mutation_score = int(_get_metric(tool_results, "pitest", "mutation_score", 0))
    mutation_killed = int(_get_metric(tool_results, "pitest", "mutation_killed", 0))
    mutation_survived = int(_get_metric(tool_results, "pitest", "mutation_survived", 0))

    owasp_critical = int(_get_metric(tool_results, "owasp", "owasp_critical", 0))
    owasp_high = int(_get_metric(tool_results, "owasp", "owasp_high", 0))
    owasp_medium = int(_get_metric(tool_results, "owasp", "owasp_medium", 0))
    owasp_low = int(_get_metric(tool_results, "owasp", "owasp_low", 0))

    trivy_critical = int(_get_metric(tool_results, "trivy", "trivy_critical", 0))
    trivy_high = int(_get_metric(tool_results, "trivy", "trivy_high", 0))
    trivy_medium = int(_get_metric(tool_results, "trivy", "trivy_medium", 0))
    trivy_low = int(_get_metric(tool_results, "trivy", "trivy_low", 0))

    build_status = "success"
    if not build_success or tests_failed > 0:
        build_status = "failure"

    results = {
        "build": build_status,
        "coverage": coverage,
        "coverage_lines_covered": coverage_lines_covered,
        "coverage_lines_total": coverage_lines_total,
        "mutation_score": mutation_score,
        "mutation_killed": mutation_killed,
        "mutation_survived": mutation_survived,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "tests_skipped": tests_skipped,
        "tests_runtime_seconds": tests_runtime,
        "critical_vulns": owasp_critical + trivy_critical,
        "high_vulns": owasp_high + trivy_high,
        "medium_vulns": owasp_medium + trivy_medium,
        "low_vulns": owasp_low + trivy_low,
    }

    tool_metrics = {
        "checkstyle_issues": _get_metric(
            tool_results, "checkstyle", "checkstyle_issues", 0
        ),
        "spotbugs_issues": _get_metric(tool_results, "spotbugs", "spotbugs_issues", 0),
        "pmd_violations": _get_metric(tool_results, "pmd", "pmd_violations", 0),
        "owasp_critical": owasp_critical,
        "owasp_high": owasp_high,
        "owasp_medium": owasp_medium,
        "owasp_low": owasp_low,
        "semgrep_findings": _get_metric(
            tool_results, "semgrep", "semgrep_findings", 0
        ),
        "trivy_critical": trivy_critical,
        "trivy_high": trivy_high,
        "trivy_medium": trivy_medium,
        "trivy_low": trivy_low,
    }

    dependency_severity = {
        "critical": owasp_critical + trivy_critical,
        "high": owasp_high + trivy_high,
        "medium": owasp_medium + trivy_medium,
        "low": owasp_low + trivy_low,
    }

    report = {
        "schema_version": "2.0",
        "metadata": {
            "workflow_version": __version__,
            "workflow_ref": context.workflow_ref or "",
            "generated_at": _timestamp(),
        },
        "repository": context.repository or "",
        "run_id": context.run_id or "",
        "run_number": context.run_number or "",
        "commit": context.commit or "",
        "branch": context.branch or "",
        "hub_correlation_id": context.correlation_id or "",
        "timestamp": _timestamp(),
        "java_version": config.get("java", {}).get("version", ""),
        "results": results,
        "tool_metrics": tool_metrics,
        "tools_configured": tools_configured,
        "tools_ran": tools_ran,
        "tools_success": tools_success,
        "thresholds": thresholds,
        "environment": {
            "workdir": context.workdir,
            "retention_days": context.retention_days,
            "build_tool": context.build_tool,
            "project_type": context.project_type,
            "docker_compose_file": context.docker_compose_file,
            "docker_health_endpoint": context.docker_health_endpoint,
        },
        "dependency_severity": dependency_severity,
    }
    return report
