"""Report build and summary commands."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config
from cihub.ci_report import (
    RunContext,
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.cli import (
    CommandResult,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.reporting import render_summary_from_path
from cihub.services import (
    ValidationRules,
    aggregate_from_dispatch,
    aggregate_from_reports_dir,
    validate_report,
)


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def _get_repo_name(config: dict[str, Any], repo_path: Path) -> str:
    repo_env = os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        return repo_env
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    owner = repo_info.get("owner")
    name = repo_info.get("name")
    if owner and name:
        return f"{owner}/{name}"
    remote = get_git_remote(repo_path)
    if remote:
        parsed = parse_repo_from_remote(remote)
        if parsed[0] and parsed[1]:
            return f"{parsed[0]}/{parsed[1]}"
    return ""


def _build_context(
    repo_path: Path,
    config: dict[str, Any],
    workdir: str,
    correlation_id: str | None,
    build_tool: str | None = None,
    project_type: str | None = None,
    docker_compose_file: str | None = None,
    docker_health_endpoint: str | None = None,
) -> RunContext:
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    branch = os.environ.get("GITHUB_REF_NAME") or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=_get_repo_name(config, repo_path),
        branch=branch,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_number=os.environ.get("GITHUB_RUN_NUMBER"),
        commit=os.environ.get("GITHUB_SHA") or "",
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _detect_java_project_type(workdir: Path) -> str:
    pom = workdir / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<modules>" in content:
            modules = len(re.findall(r"<module>.*?</module>", content))
            return f"Multi-module ({modules} modules)" if modules else "Multi-module"
        return "Single module"

    settings_gradle = workdir / "settings.gradle"
    settings_kts = workdir / "settings.gradle.kts"
    if settings_gradle.exists() or settings_kts.exists():
        return "Multi-module"
    if (workdir / "build.gradle").exists() or (workdir / "build.gradle.kts").exists():
        return "Single module"
    return "Unknown"


def _load_tool_outputs(tool_dir: Path) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for path in tool_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tool = str(data.get("tool") or path.stem)
            outputs[tool] = data
        except json.JSONDecodeError:
            continue
    return outputs


# ============================================================================
# Report Validation (service-backed)
# ============================================================================

def _validate_report(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Validate report.json structure and content."""
    report_path = Path(args.report)
    if not report_path.exists():
        message = f"Report file not found: {report_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON in report: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    errors: list[str] = []
    expect_mode = getattr(args, "expect", "clean")
    coverage_min = getattr(args, "coverage_min", 70)

    summary_text = None
    if getattr(args, "summary", None):
        summary_path = Path(args.summary)
        if not summary_path.exists():
            errors.append(f"summary file not found: {summary_path}")
        else:
            summary_text = summary_path.read_text(encoding="utf-8")

    reports_dir = None
    if getattr(args, "reports_dir", None):
        reports_dir = Path(args.reports_dir)
        if not reports_dir.exists():
            errors.append(f"reports dir not found: {reports_dir}")
            reports_dir = None

    rules = ValidationRules(
        expect_clean=expect_mode == "clean",
        coverage_min=coverage_min,
        strict=bool(getattr(args, "strict", False)),
    )
    result = validate_report(
        report,
        rules,
        summary_text=summary_text,
        reports_dir=reports_dir,
    )

    errors.extend(result.errors)
    warnings = list(result.warnings)

    if getattr(args, "debug", False) and result.debug_messages:
        print("Validation debug output:")
        for msg in result.debug_messages:
            print(f"  {msg}")

    if getattr(args, "verbose", False):
        print(f"\nErrors: {len(errors)}, Warnings: {len(warnings)}")

    if errors:
        if not json_mode:
            print(f"Validation FAILED with {len(errors)} errors:")
            for err in errors:
                print(f"  ::error::{err}")
        if warnings:
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Validation failed: {len(errors)} errors",
                problems=[{"severity": "error", "message": e} for e in errors]
                + [{"severity": "warning", "message": w} for w in warnings],
            )
        return EXIT_FAILURE

    if warnings:
        if not json_mode:
            print(f"Validation passed with {len(warnings)} warnings:")
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if rules.strict:
            if json_mode:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"Validation failed (strict): {len(warnings)} warnings",
                    problems=[{"severity": "warning", "message": w} for w in warnings],
                )
            return EXIT_FAILURE

    if not json_mode:
        print("Validation PASSED")
    if json_mode:
        return CommandResult(exit_code=EXIT_SUCCESS, summary="Validation passed")
    return EXIT_SUCCESS



def cmd_report(args: argparse.Namespace) -> int | CommandResult:
    json_mode = getattr(args, "json", False)
    if args.subcommand == "aggregate":
        summary_file = Path(args.summary_file) if args.summary_file else None
        if summary_file is None:
            summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_env:
                summary_file = Path(summary_env)

        total_repos = args.total_repos or int(os.environ.get("TOTAL_REPOS", 0) or 0)
        hub_run_id = args.hub_run_id or os.environ.get("HUB_RUN_ID", os.environ.get("GITHUB_RUN_ID", ""))
        hub_event = args.hub_event or os.environ.get("HUB_EVENT", os.environ.get("GITHUB_EVENT_NAME", ""))

        reports_dir = getattr(args, "reports_dir", None)
        if reports_dir:
            result = aggregate_from_reports_dir(
                reports_dir=Path(reports_dir),
                output_file=Path(args.output),
                defaults_file=Path(args.defaults_file),
                hub_run_id=hub_run_id,
                hub_event=hub_event,
                total_repos=total_repos,
                summary_file=summary_file,
                strict=bool(args.strict),
            )
            exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE
            if json_mode:
                summary = "Aggregation complete" if result.success else "Aggregation failed"
                return CommandResult(
                    exit_code=exit_code,
                    summary=summary,
                    artifacts={
                        "report": str(result.report_path) if result.report_path else "",
                        "summary": str(result.summary_path) if result.summary_path else "",
                    },
                )
            return exit_code

        token = args.token
        token_env = args.token_env or "HUB_DISPATCH_TOKEN"  # noqa: S105
        if not token:
            token = os.environ.get(token_env)
        if not token and token_env != "GITHUB_TOKEN":
            token = os.environ.get("GITHUB_TOKEN")
        if not token:
            message = f"Missing token (expected {token_env} or GITHUB_TOKEN)"
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(message)
            return EXIT_FAILURE

        result = aggregate_from_dispatch(
            dispatch_dir=Path(args.dispatch_dir),
            output_file=Path(args.output),
            defaults_file=Path(args.defaults_file),
            token=token,
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            summary_file=summary_file,
            strict=bool(args.strict),
            timeout_sec=int(args.timeout),
        )
        exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE

        if json_mode:
            summary = "Aggregation complete" if result.success else "Aggregation failed"
            return CommandResult(
                exit_code=exit_code,
                summary=summary,
                artifacts={
                    "report": str(result.report_path) if result.report_path else "",
                    "summary": str(result.summary_path) if result.summary_path else "",
                },
            )
        return exit_code
    if args.subcommand == "outputs":
        report_path = Path(args.report)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            message = f"Failed to read report: {exc}"
            if json_mode:
                return CommandResult(exit_code=EXIT_FAILURE, summary=message)
            print(message)
            return EXIT_FAILURE

        results = report.get("results", {}) or {}
        status = results.get("build") or results.get("test")
        if status not in {"success", "failure", "skipped"}:
            tests_failed = int(results.get("tests_failed", 0))
            status = "failure" if tests_failed > 0 else "success"

        output_path = Path(args.output) if args.output else None
        if output_path is None:
            output_path_env = os.environ.get("GITHUB_OUTPUT")
            if output_path_env:
                output_path = Path(output_path_env)
        if output_path is None:
            message = "No output target specified for report outputs"
            if json_mode:
                return CommandResult(exit_code=EXIT_USAGE, summary=message)
            print(message)
            return EXIT_USAGE

        output_text = (
            f"build_status={status}\n"
            f"coverage={results.get('coverage', 0)}\n"
            f"mutation_score={results.get('mutation_score', 0)}\n"
        )
        output_path.write_text(output_text, encoding="utf-8")

        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Report outputs written",
                artifacts={"outputs": str(output_path)},
            )
        print(f"Wrote outputs: {output_path}")
        return EXIT_SUCCESS

    if args.subcommand == "summary":
        report_path = Path(args.report)
        summary_text = render_summary_from_path(report_path)
        output_path = Path(args.output) if args.output else None
        if output_path:
            output_path.write_text(summary_text, encoding="utf-8")
        else:
            print(summary_text)
        github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if github_summary and args.write_github_summary:
            Path(github_summary).write_text(summary_text, encoding="utf-8")
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary="Summary rendered",
                artifacts={"summary": str(output_path) if output_path else ""},
            )
        return EXIT_SUCCESS

    if args.subcommand == "validate":
        return _validate_report(args, json_mode)

    if args.subcommand != "build":
        message = f"Unknown report subcommand: {args.subcommand}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message)
        return EXIT_USAGE

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
