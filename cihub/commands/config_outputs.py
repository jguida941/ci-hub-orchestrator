"""Emit GitHub Actions outputs from .ci-hub.yml."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


def _get_value(data: dict[str, Any], path: list[str], default: Any) -> Any:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(key)
    if cursor is None:
        return default
    return cursor


def _get_str(data: dict[str, Any], path: list[str], default: str) -> str:
    return str(_get_value(data, path, default))


def _get_int(data: dict[str, Any], path: list[str], default: int) -> int:
    value = _get_value(data, path, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _tool_entry(config: dict[str, Any], language: str, tool: str) -> Any:
    tools = config.get(language, {}).get("tools", {}) or {}
    if not isinstance(tools, dict):
        return {}
    return tools.get(tool, {})


def _tool_enabled(
    config: dict[str, Any],
    language: str,
    tool: str,
    default: bool,
) -> bool:
    entry = _tool_entry(config, language, tool)
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        enabled = entry.get("enabled")
        if isinstance(enabled, bool):
            return enabled
    return default


def _tool_int(
    config: dict[str, Any],
    language: str,
    tool: str,
    key: str,
    default: int,
) -> int:
    entry = _tool_entry(config, language, tool)
    if isinstance(entry, dict):
        value = entry.get(key, default)
    else:
        value = default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cmd_config_outputs(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo)
    json_mode = getattr(args, "json", False)

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(message, file=sys.stderr)
        return EXIT_FAILURE

    language = config.get("language") or _get_str(config, ["repo", "language"], "python") or "python"

    workdir = args.workdir or _get_str(config, ["workdir"], "")
    if not workdir:
        workdir = _get_str(config, ["repo", "subdir"], ".")
    if not workdir:
        workdir = "."

    python_thresholds = {
        "coverage_min": _tool_int(config, "python", "pytest", "min_coverage", 70),
        "mutation_score_min": _tool_int(config, "python", "mutmut", "min_mutation_score", 70),
        "owasp_cvss_fail": _tool_int(config, "python", "trivy", "fail_on_cvss", 7),
        "max_semgrep_findings": _tool_int(config, "python", "semgrep", "max_findings", 0),
        "max_ruff_errors": _tool_int(config, "python", "ruff", "max_errors", 0),
        "max_black_issues": _tool_int(config, "python", "black", "max_issues", 0),
        "max_isort_issues": _tool_int(config, "python", "isort", "max_issues", 0),
    }

    java_thresholds = {
        "coverage_min": _tool_int(config, "java", "jacoco", "min_coverage", 70),
        "mutation_score_min": _tool_int(config, "java", "pitest", "min_mutation_score", 70),
        "owasp_cvss_fail": _tool_int(config, "java", "owasp", "fail_on_cvss", 7),
        "max_semgrep_findings": _tool_int(config, "java", "semgrep", "max_findings", 0),
        "max_checkstyle_errors": _tool_int(config, "java", "checkstyle", "max_errors", 0),
        "max_spotbugs_bugs": _tool_int(config, "java", "spotbugs", "max_bugs", 0),
        "max_pmd_violations": _tool_int(config, "java", "pmd", "max_violations", 0),
    }

    global_thresholds = config.get("thresholds", {}) or {}
    for key in ("coverage_min", "mutation_score_min", "owasp_cvss_fail"):
        if key in global_thresholds and global_thresholds[key] is not None:
            threshold_value = int(global_thresholds[key])
            python_thresholds[key] = threshold_value
            java_thresholds[key] = threshold_value

    max_critical = _get_int(config, ["thresholds", "max_critical_vulns"], 0)
    max_high = _get_int(config, ["thresholds", "max_high_vulns"], 0)

    lang_for_shared = "java" if language == "java" else "python"

    outputs: dict[str, str] = {
        "language": str(language),
        "python_version": _get_str(config, ["python", "version"], "3.12"),
        "java_version": _get_str(config, ["java", "version"], "21"),
        "build_tool": _get_str(config, ["java", "build_tool"], "maven"),
        "workdir": workdir,
        "retention_days": str(_get_int(config, ["reports", "retention_days"], 30)),
        # Python tool toggles
        "run_pytest": _bool_str(_tool_enabled(config, "python", "pytest", True)),
        "run_ruff": _bool_str(_tool_enabled(config, "python", "ruff", True)),
        "run_bandit": _bool_str(_tool_enabled(config, "python", "bandit", True)),
        "run_pip_audit": _bool_str(_tool_enabled(config, "python", "pip_audit", True)),
        "run_mypy": _bool_str(_tool_enabled(config, "python", "mypy", False)),
        "run_black": _bool_str(_tool_enabled(config, "python", "black", True)),
        "run_isort": _bool_str(_tool_enabled(config, "python", "isort", True)),
        "run_mutmut": _bool_str(_tool_enabled(config, "python", "mutmut", True)),
        "run_hypothesis": _bool_str(_tool_enabled(config, "python", "hypothesis", True)),
        "run_semgrep": _bool_str(_tool_enabled(config, lang_for_shared, "semgrep", False)),
        "run_trivy": _bool_str(_tool_enabled(config, lang_for_shared, "trivy", False)),
        "run_codeql": _bool_str(_tool_enabled(config, lang_for_shared, "codeql", False)),
        "run_docker": _bool_str(_tool_enabled(config, lang_for_shared, "docker", False)),
        # Java tool toggles
        "run_jacoco": _bool_str(_tool_enabled(config, "java", "jacoco", True)),
        "run_checkstyle": _bool_str(_tool_enabled(config, "java", "checkstyle", True)),
        "run_spotbugs": _bool_str(_tool_enabled(config, "java", "spotbugs", True)),
        "run_owasp": _bool_str(_tool_enabled(config, "java", "owasp", True)),
        "use_nvd_api_key": _bool_str(
            _tool_enabled(config, "java", "owasp", True)
            and _get_value(config, ["java", "tools", "owasp", "use_nvd_api_key"], True) is not False
        ),
        "run_pmd": _bool_str(_tool_enabled(config, "java", "pmd", True)),
        "run_pitest": _bool_str(_tool_enabled(config, "java", "pitest", True)),
        "run_jqwik": _bool_str(_tool_enabled(config, "java", "jqwik", False)),
        # Thresholds
        "coverage_min": str(python_thresholds["coverage_min"]),
        "mutation_score_min": str(python_thresholds["mutation_score_min"]),
        "owasp_cvss_fail": str(python_thresholds["owasp_cvss_fail"]),
        "max_semgrep_findings": str(python_thresholds["max_semgrep_findings"]),
        "max_ruff_errors": str(python_thresholds["max_ruff_errors"]),
        "max_black_issues": str(python_thresholds["max_black_issues"]),
        "max_isort_issues": str(python_thresholds["max_isort_issues"]),
        "max_checkstyle_errors": str(java_thresholds["max_checkstyle_errors"]),
        "max_spotbugs_bugs": str(java_thresholds["max_spotbugs_bugs"]),
        "max_pmd_violations": str(java_thresholds["max_pmd_violations"]),
        "max_critical_vulns": str(max_critical),
        "max_high_vulns": str(max_high),
    }

    if language == "java":
        outputs["coverage_min"] = str(java_thresholds["coverage_min"])
        outputs["mutation_score_min"] = str(java_thresholds["mutation_score_min"])
        outputs["owasp_cvss_fail"] = str(java_thresholds["owasp_cvss_fail"])
        outputs["max_semgrep_findings"] = str(java_thresholds["max_semgrep_findings"])

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Config outputs generated",
            data={"outputs": outputs},
        )

    output_path = os.environ.get("GITHUB_OUTPUT") if args.github_output else None
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            for key, value in outputs.items():
                handle.write(f"{key}={value}\n")
        return EXIT_SUCCESS

    for key, value in outputs.items():
        print(f"{key}={value}")
    return EXIT_SUCCESS
