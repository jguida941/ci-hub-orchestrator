"""Report build command logic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.ci_config import load_ci_config
from cihub.ci_report import (
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.reporting import render_summary_from_path

from .helpers import (
    _build_context,
    _detect_java_project_type,
    _load_tool_outputs,
    _tool_enabled,
)


def _build_report(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Build a report from tool outputs."""
    repo_path = Path(args.repo or ".").resolve()
    output_dir = Path(args.output_dir or ".cihub")
    tool_dir = Path(args.tool_dir) if args.tool_dir else output_dir / "tool-outputs"
    report_path = Path(args.report) if args.report else output_dir / "report.json"
    summary_path = Path(args.summary) if args.summary else output_dir / "summary.md"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    language = config.get("language") or ""
    tool_outputs = _load_tool_outputs(tool_dir)

    if language == "python":
        tools_configured = {
            tool: _tool_enabled(config, tool, "python")
            for tool in [
                "pytest",
                "mutmut",
                "hypothesis",
                "ruff",
                "black",
                "isort",
                "mypy",
                "bandit",
                "pip_audit",
                "sbom",
                "semgrep",
                "trivy",
                "codeql",
                "docker",
            ]
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))
        if tools_configured.get("hypothesis"):
            tools_ran["hypothesis"] = tools_ran.get("pytest", False)
            tools_success["hypothesis"] = tools_success.get("pytest", False)
        thresholds = resolve_thresholds(config, "python")
        context = _build_context(repo_path, config, args.workdir or ".", args.correlation_id)
        report = build_python_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    elif language == "java":
        tools_configured = {
            tool: _tool_enabled(config, tool, "java")
            for tool in [
                "jacoco",
                "pitest",
                "jqwik",
                "checkstyle",
                "spotbugs",
                "pmd",
                "owasp",
                "semgrep",
                "trivy",
                "codeql",
                "sbom",
                "docker",
            ]
        }
        tools_ran = {tool: False for tool in tools_configured}
        tools_success = {tool: False for tool in tools_configured}
        for tool, data in tool_outputs.items():
            tools_ran[tool] = bool(data.get("ran"))
            tools_success[tool] = bool(data.get("success"))

        if tools_configured.get("jqwik"):
            build_data = tool_outputs.get("build", {}) or {}
            tests_failed = int(build_data.get("metrics", {}).get("tests_failed", 0))
            build_success = bool(build_data.get("success", False))
            tools_ran["jqwik"] = bool(build_data)
            tools_success["jqwik"] = build_success and tests_failed == 0

        thresholds = resolve_thresholds(config, "java")
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        project_type = _detect_java_project_type(repo_path / (args.workdir or "."))
        docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
        context = _build_context(
            repo_path,
            config,
            args.workdir or ".",
            args.correlation_id,
            build_tool=build_tool,
            project_type=project_type,
            docker_compose_file=docker_cfg.get("compose_file"),
            docker_health_endpoint=docker_cfg.get("health_endpoint"),
        )
        report = build_java_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
    else:
        message = f"report build supports python or java (got '{language}')"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_text = render_summary_from_path(report_path)
    summary_path.write_text(summary_text, encoding="utf-8")

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Report built",
            artifacts={"report": str(report_path), "summary": str(summary_path)},
        )
    print(f"Wrote report: {report_path}")
    print(f"Wrote summary: {summary_path}")
    return EXIT_SUCCESS
