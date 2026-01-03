"""
CI/CD Hub - Workflow Input Generation

Generates inputs for GitHub Actions workflow dispatch from merged configuration.
"""

from __future__ import annotations

from typing import Any


def generate_workflow_inputs(config: dict) -> dict:
    """
    Generate inputs for GitHub Actions workflow dispatch.

    Returns:
    - Dispatch inputs: tool toggles, essential settings, thresholds
    - Internal metadata: _dispatch_enabled, _run_group, _force_all_tools (_-prefixed)

    Returns a flat dict. Keys prefixed with _ are for internal use, not dispatch.
    Expects config to be normalized via normalize_config at load boundaries.
    """

    # Determine language
    language = config.get("language") or config.get("repo", {}).get("language", "java")

    inputs: dict[str, Any] = {
        "language": language,
        "hub_correlation_id": "",
    }

    thresholds: dict[str, Any] = {}

    if language == "java":
        java = config.get("java", {})
        inputs["java_version"] = java.get("version", "21")
        inputs["build_tool"] = java.get("build_tool", "maven")

        tools = java.get("tools", {})

        # Tool toggles (dispatch inputs)
        inputs["run_jacoco"] = tools.get("jacoco", {}).get("enabled", True)
        inputs["run_checkstyle"] = tools.get("checkstyle", {}).get("enabled", True)
        inputs["run_spotbugs"] = tools.get("spotbugs", {}).get("enabled", True)
        inputs["run_owasp"] = tools.get("owasp", {}).get("enabled", True)
        inputs["use_nvd_api_key"] = tools.get("owasp", {}).get("use_nvd_api_key", True)
        inputs["run_pitest"] = tools.get("pitest", {}).get("enabled", True)
        inputs["run_jqwik"] = tools.get("jqwik", {}).get("enabled", False)
        inputs["run_pmd"] = tools.get("pmd", {}).get("enabled", True)
        inputs["run_semgrep"] = tools.get("semgrep", {}).get("enabled", False)
        inputs["run_sbom"] = tools.get("sbom", {}).get("enabled", False)
        inputs["run_trivy"] = tools.get("trivy", {}).get("enabled", False)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", False)
        inputs["run_docker"] = tools.get("docker", {}).get("enabled", False)

        # Thresholds (direct dispatch inputs)
        thresholds["coverage_min"] = tools.get("jacoco", {}).get("min_coverage", 70)
        thresholds["mutation_score_min"] = tools.get("pitest", {}).get("min_mutation_score", 70)
        thresholds["owasp_cvss_fail"] = tools.get("owasp", {}).get("fail_on_cvss", 7)
        thresholds["trivy_cvss_fail"] = tools.get("trivy", {}).get(
            "fail_on_cvss",
            thresholds["owasp_cvss_fail"],
        )
        thresholds["max_checkstyle_errors"] = tools.get("checkstyle", {}).get("max_errors", 0)
        thresholds["max_spotbugs_bugs"] = tools.get("spotbugs", {}).get("max_bugs", 0)
        thresholds["max_pmd_violations"] = tools.get("pmd", {}).get("max_violations", 0)
        thresholds["max_semgrep_findings"] = tools.get("semgrep", {}).get("max_findings", 0)

    elif language == "python":
        python = config.get("python", {})
        inputs["python_version"] = python.get("version", "3.12")

        tools = python.get("tools", {})

        # Tool toggles (dispatch inputs)
        inputs["run_pytest"] = tools.get("pytest", {}).get("enabled", True)
        inputs["run_ruff"] = tools.get("ruff", {}).get("enabled", True)
        inputs["run_bandit"] = tools.get("bandit", {}).get("enabled", True)
        inputs["run_pip_audit"] = tools.get("pip_audit", {}).get("enabled", True)
        inputs["run_mypy"] = tools.get("mypy", {}).get("enabled", False)
        inputs["run_black"] = tools.get("black", {}).get("enabled", True)
        inputs["run_isort"] = tools.get("isort", {}).get("enabled", True)
        inputs["run_mutmut"] = tools.get("mutmut", {}).get("enabled", False)
        inputs["run_hypothesis"] = tools.get("hypothesis", {}).get("enabled", True)
        inputs["run_sbom"] = tools.get("sbom", {}).get("enabled", False)
        inputs["run_semgrep"] = tools.get("semgrep", {}).get("enabled", False)
        inputs["run_trivy"] = tools.get("trivy", {}).get("enabled", False)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", False)
        inputs["run_docker"] = tools.get("docker", {}).get("enabled", False)

        # Thresholds (direct dispatch inputs)
        thresholds["coverage_min"] = tools.get("pytest", {}).get("min_coverage", 70)
        thresholds["mutation_score_min"] = tools.get("mutmut", {}).get("min_mutation_score", 70)
        # For Trivy CVSS gate - check trivy config, global thresholds, or default to 7
        thresholds["trivy_cvss_fail"] = tools.get("trivy", {}).get("fail_on_cvss", 7)
        # Back-compat: mirror to owasp_cvss_fail for older workflows/outputs
        thresholds["owasp_cvss_fail"] = thresholds["trivy_cvss_fail"]
        thresholds["max_ruff_errors"] = tools.get("ruff", {}).get("max_errors", 0)
        thresholds["max_black_issues"] = tools.get("black", {}).get("max_issues", 0)
        thresholds["max_isort_issues"] = tools.get("isort", {}).get("max_issues", 0)
        thresholds["max_semgrep_findings"] = tools.get("semgrep", {}).get("max_findings", 0)

    # Global thresholds override tool-specific ones
    global_thresholds = config.get("thresholds", {})
    if "coverage_min" in global_thresholds:
        thresholds["coverage_min"] = global_thresholds["coverage_min"]
    if "mutation_score_min" in global_thresholds:
        thresholds["mutation_score_min"] = global_thresholds["mutation_score_min"]
    if "owasp_cvss_fail" in global_thresholds:
        thresholds["owasp_cvss_fail"] = global_thresholds["owasp_cvss_fail"]
    if "trivy_cvss_fail" in global_thresholds:
        thresholds["trivy_cvss_fail"] = global_thresholds["trivy_cvss_fail"]
    if "trivy_cvss_fail" not in thresholds and "owasp_cvss_fail" in thresholds:
        thresholds["trivy_cvss_fail"] = thresholds["owasp_cvss_fail"]
    if language == "python" and "trivy_cvss_fail" in thresholds:
        thresholds["owasp_cvss_fail"] = thresholds["trivy_cvss_fail"]
    thresholds["max_critical_vulns"] = global_thresholds.get("max_critical_vulns", 0)
    thresholds["max_high_vulns"] = global_thresholds.get("max_high_vulns", 0)

    inputs.update(thresholds)
    reports_cfg = config.get("reports", {}) or {}
    github_summary = reports_cfg.get("github_summary", {}) or {}
    inputs["write_github_summary"] = bool(github_summary.get("enabled", True))

    # Debug and triage inputs (dispatch inputs)
    cihub_cfg = config.get("cihub", {}) or {}
    inputs["cihub_debug"] = cihub_cfg.get("debug", False)
    inputs["cihub_verbose"] = cihub_cfg.get("verbose", False)
    inputs["cihub_debug_context"] = cihub_cfg.get("debug_context", False)
    inputs["cihub_emit_triage"] = cihub_cfg.get("emit_triage", False)

    # Metadata for internal use (not dispatch inputs)
    repo = config.get("repo", {})
    inputs["_dispatch_enabled"] = repo.get("dispatch_enabled", True)
    inputs["_run_group"] = repo.get("run_group", "full")
    inputs["_force_all_tools"] = repo.get("force_all_tools", False)

    return inputs