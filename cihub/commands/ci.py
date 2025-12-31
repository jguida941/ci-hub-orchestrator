"""CI command handler for CLI-driven workflows."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from cihub.ci_config import load_ci_config, load_hub_config
from cihub.ci_report import (
    RunContext,
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.ci_runner import (
    ToolResult,
    run_bandit,
    run_black,
    run_checkstyle,
    run_isort,
    run_jacoco,
    run_java_build,
    run_mutmut,
    run_mypy,
    run_owasp,
    run_pip_audit,
    run_pitest,
    run_pmd,
    run_pytest,
    run_ruff,
    run_semgrep,
    run_spotbugs,
    run_trivy,
)
from cihub.cli import (
    CommandResult,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
    resolve_executable,
    validate_subdir,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.reporting import render_summary

PYTHON_TOOLS = [
    "pytest",
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
    "hypothesis",
    "mutmut",
]

JAVA_TOOLS = [
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

PYTHON_RUNNERS = {
    "pytest": run_pytest,
    "ruff": run_ruff,
    "black": run_black,
    "isort": run_isort,
    "mypy": run_mypy,
    "bandit": run_bandit,
    "pip_audit": run_pip_audit,
    "mutmut": run_mutmut,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
}

JAVA_RUNNERS = {
    "jacoco": run_jacoco,
    "pitest": run_pitest,
    "checkstyle": run_checkstyle,
    "spotbugs": run_spotbugs,
    "pmd": run_pmd,
    "owasp": run_owasp,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
}


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


def _get_git_commit(repo_path: Path) -> str:
    try:
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [git_bin, "-C", str(repo_path), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return output.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _resolve_workdir(
    repo_path: Path,
    config: dict[str, Any],
    override: str | None,
) -> str:
    if override:
        validate_subdir(override)
        return override
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    subdir = repo_info.get("subdir")
    if isinstance(subdir, str) and subdir:
        validate_subdir(subdir)
        return subdir
    return "."


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


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def _run_dep_command(
    cmd: list[str],
    workdir: Path,
    label: str,
    problems: list[dict[str, Any]],
) -> bool:
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    message = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
    problems.append(
        {
            "severity": "error",
            "message": f"{label} failed: {message}",
            "code": "CIHUB-CI-DEPS",
        }
    )
    return False


def _install_python_dependencies(
    config: dict[str, Any],
    workdir: Path,
    problems: list[dict[str, Any]],
) -> None:
    deps_cfg = config.get("python", {}).get("dependencies", {}) or {}
    if isinstance(deps_cfg, dict):
        if deps_cfg.get("install") is False:
            return
        commands = deps_cfg.get("commands")
    else:
        commands = None

    python_bin = sys.executable or resolve_executable("python")
    if commands:
        for cmd in commands:
            if not cmd:
                continue
            if isinstance(cmd, list):
                parts = [str(part) for part in cmd if str(part)]
            else:
                cmd_str = str(cmd).strip()
                if not cmd_str:
                    continue
                parts = shlex.split(cmd_str)
            if not parts:
                continue
            _run_dep_command(parts, workdir, " ".join(parts), problems)
        return

    if (workdir / "requirements.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements.txt"],
            workdir,
            "requirements.txt",
            problems,
        )
    if (workdir / "requirements-dev.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements-dev.txt"],
            workdir,
            "requirements-dev.txt",
            problems,
        )
    if (workdir / "pyproject.toml").exists():
        ok = _run_dep_command(
            [python_bin, "-m", "pip", "install", "-e", ".[dev]"],
            workdir,
            "pyproject.toml [dev]",
            problems,
        )
        if not ok:
            _run_dep_command(
                [python_bin, "-m", "pip", "install", "-e", "."],
                workdir,
                "pyproject.toml",
                problems,
            )


def _run_python_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    problems: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    mutants_dir = workdir_path / "mutants"
    if mutants_dir.exists():
        try:
            shutil.rmtree(mutants_dir)
        except OSError as exc:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Failed to remove mutmut artifacts: {exc}",
                    "code": "CIHUB-CI-MUTMUT-CLEANUP",
                }
            )

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    for tool in PYTHON_TOOLS:
        if tool == "hypothesis":
            continue
        enabled = _tool_enabled(config, tool, "python")
        if not enabled:
            continue
        runner = PYTHON_RUNNERS.get(tool)
        if runner is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": (f"Tool '{tool}' is enabled but is not supported by cihub; run it via a workflow step."),
                    "code": "CIHUB-CI-UNSUPPORTED",
                }
            )
            ToolResult(tool=tool, ran=False, success=False).write_json(tool_output_dir / f"{tool}.json")
            continue
        try:
            if tool == "mutmut":
                timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
                result = runner(workdir_path, output_dir, int(timeout) * 60)  # type: ignore[operator]
            else:
                result = runner(workdir_path, output_dir)  # type: ignore[operator]
        except FileNotFoundError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found: {exc}",
                    "code": "CIHUB-CI-MISSING-TOOL",
                }
            )
            result = ToolResult(tool=tool, ran=False, success=False)
        tool_outputs[tool] = result.to_payload()
        tools_ran[tool] = result.ran
        tools_success[tool] = result.success
        result.write_json(tool_output_dir / f"{tool}.json")

    if _tool_enabled(config, "hypothesis", "python"):
        tools_ran["hypothesis"] = tools_ran.get("pytest", False)
        tools_success["hypothesis"] = tools_success.get("pytest", False)

    return tool_outputs, tools_ran, tools_success


def _run_java_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    build_tool: str,
    problems: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    jacoco_enabled = _tool_enabled(config, "jacoco", "java")
    build_result = run_java_build(workdir_path, output_dir, build_tool, jacoco_enabled)
    tool_outputs["build"] = build_result.to_payload()
    build_result.write_json(tool_output_dir / "build.json")

    use_nvd_api_key = bool(config.get("java", {}).get("tools", {}).get("owasp", {}).get("use_nvd_api_key", True))

    for tool in JAVA_TOOLS:
        if tool == "jqwik":
            continue
        enabled = _tool_enabled(config, tool, "java")
        if not enabled:
            continue
        runner = JAVA_RUNNERS.get(tool)
        if runner is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": (f"Tool '{tool}' is enabled but is not supported by cihub; run it via a workflow step."),
                    "code": "CIHUB-CI-UNSUPPORTED",
                }
            )
            ToolResult(tool=tool, ran=False, success=False).write_json(tool_output_dir / f"{tool}.json")
            continue
        try:
            if tool == "pitest":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "checkstyle":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "spotbugs":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "pmd":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "owasp":
                result = runner(workdir_path, output_dir, build_tool, use_nvd_api_key)  # type: ignore[operator]
            else:
                result = runner(workdir_path, output_dir)  # type: ignore[operator]
        except FileNotFoundError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found: {exc}",
                    "code": "CIHUB-CI-MISSING-TOOL",
                }
            )
            result = ToolResult(tool=tool, ran=False, success=False)

        tool_outputs[tool] = result.to_payload()
        tools_ran[tool] = result.ran
        tools_success[tool] = result.success
        result.write_json(tool_output_dir / f"{tool}.json")

    if _tool_enabled(config, "jqwik", "java"):
        tests_failed = int(build_result.metrics.get("tests_failed", 0))
        tools_ran["jqwik"] = True
        tools_success["jqwik"] = build_result.success and tests_failed == 0

    return tool_outputs, tools_ran, tools_success


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
        commit=os.environ.get("GITHUB_SHA") or _get_git_commit(repo_path),
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _evaluate_python_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}

    tests_failed = int(results.get("tests_failed", 0))
    if tools_configured.get("pytest") and tests_failed > 0:
        failures.append("pytest failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("pytest") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("mutmut") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_ruff = int(thresholds.get("max_ruff_errors", 0) or 0)
    ruff_errors = int(metrics.get("ruff_errors", 0))
    if tools_configured.get("ruff") and ruff_errors > max_ruff:
        failures.append(f"ruff errors {ruff_errors} > {max_ruff}")

    max_black = int(thresholds.get("max_black_issues", 0) or 0)
    black_issues = int(metrics.get("black_issues", 0))
    if tools_configured.get("black") and black_issues > max_black:
        failures.append(f"black issues {black_issues} > {max_black}")

    max_isort = int(thresholds.get("max_isort_issues", 0) or 0)
    isort_issues = int(metrics.get("isort_issues", 0))
    if tools_configured.get("isort") and isort_issues > max_isort:
        failures.append(f"isort issues {isort_issues} > {max_isort}")

    mypy_errors = int(metrics.get("mypy_errors", 0))
    if tools_configured.get("mypy") and mypy_errors > 0:
        failures.append(f"mypy errors {mypy_errors} > 0")

    max_high = int(thresholds.get("max_high_vulns", 0) or 0)
    bandit_high = int(metrics.get("bandit_high", 0))
    if tools_configured.get("bandit") and bandit_high > max_high:
        failures.append(f"bandit high {bandit_high} > {max_high}")

    pip_vulns = int(metrics.get("pip_audit_vulns", 0))
    max_pip = int(thresholds.get("max_pip_audit_vulns", max_high) or 0)
    if tools_configured.get("pip_audit") and pip_vulns > max_pip:
        failures.append(f"pip-audit vulns {pip_vulns} > {max_pip}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if tools_configured.get("semgrep") and semgrep_findings > max_semgrep:
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    trivy_critical = int(metrics.get("trivy_critical", 0))
    if tools_configured.get("trivy") and trivy_critical > max_critical:
        failures.append(f"trivy critical {trivy_critical} > {max_critical}")

    trivy_high = int(metrics.get("trivy_high", 0))
    if tools_configured.get("trivy") and trivy_high > max_high:
        failures.append(f"trivy high {trivy_high} > {max_high}")

    return failures


def _evaluate_java_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}

    tests_failed = int(results.get("tests_failed", 0))
    if tests_failed > 0:
        failures.append("test failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("jacoco") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("pitest") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_checkstyle = int(thresholds.get("max_checkstyle_errors", 0) or 0)
    checkstyle_issues = int(metrics.get("checkstyle_issues", 0))
    if tools_configured.get("checkstyle") and checkstyle_issues > max_checkstyle:
        failures.append(f"checkstyle issues {checkstyle_issues} > {max_checkstyle}")

    max_spotbugs = int(thresholds.get("max_spotbugs_bugs", 0) or 0)
    spotbugs_issues = int(metrics.get("spotbugs_issues", 0))
    if tools_configured.get("spotbugs") and spotbugs_issues > max_spotbugs:
        failures.append(f"spotbugs issues {spotbugs_issues} > {max_spotbugs}")

    max_pmd = int(thresholds.get("max_pmd_violations", 0) or 0)
    pmd_issues = int(metrics.get("pmd_violations", 0))
    if tools_configured.get("pmd") and pmd_issues > max_pmd:
        failures.append(f"pmd violations {pmd_issues} > {max_pmd}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    max_high = int(thresholds.get("max_high_vulns", 0) or 0)

    owasp_critical = int(metrics.get("owasp_critical", 0))
    owasp_high = int(metrics.get("owasp_high", 0))
    if tools_configured.get("owasp") and (owasp_critical > max_critical or owasp_high > max_high):
        failures.append(f"owasp critical/high {owasp_critical}/{owasp_high} > {max_critical}/{max_high}")

    trivy_critical = int(metrics.get("trivy_critical", 0))
    trivy_high = int(metrics.get("trivy_high", 0))
    if tools_configured.get("trivy") and (trivy_critical > max_critical or trivy_high > max_high):
        failures.append(f"trivy critical/high {trivy_critical}/{trivy_high} > {max_critical}/{max_high}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if tools_configured.get("semgrep") and semgrep_findings > max_semgrep:
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    return failures


def cmd_ci(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo or ".").resolve()
    json_mode = getattr(args, "json", False)
    output_dir = Path(args.output_dir or ".cihub")
    if not output_dir.is_absolute():
        output_dir = repo_path / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        config_from_hub = getattr(args, "config_from_hub", None)
        if config_from_hub:
            # Load config from hub's config/repos/<basename>.yaml (for hub-run-all.yml)
            config = load_hub_config(config_from_hub, repo_path)
        else:
            # Load config from repo's .ci-hub.yml (normal mode)
            config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(message)
        return EXIT_FAILURE

    language = config.get("language") or ""
    workdir = _resolve_workdir(repo_path, config, args.workdir)
    problems: list[dict[str, Any]] = []

    if language == "python":
        if args.install_deps:
            _install_python_dependencies(config, repo_path / workdir, problems)
        try:
            tool_outputs, tools_ran, tools_success = _run_python_tools(config, repo_path, workdir, output_dir, problems)
        except Exception as exc:
            message = f"Tool execution failed: {exc}"
            if json_mode:
                return CommandResult(
                    exit_code=EXIT_INTERNAL_ERROR,
                    summary=message,
                    problems=[{"severity": "error", "message": message}],
                )
            print(message)
            return EXIT_INTERNAL_ERROR

        tools_configured = {tool: _tool_enabled(config, tool, "python") for tool in PYTHON_TOOLS}
        thresholds = resolve_thresholds(config, "python")
        context = _build_context(repo_path, config, workdir, args.correlation_id)
        report = build_python_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
        gate_failures = _evaluate_python_gates(report, thresholds, tools_configured)

    elif language == "java":
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        if build_tool not in {"maven", "gradle"}:
            build_tool = "maven"
        project_type = _detect_java_project_type(repo_path / workdir)
        docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
        docker_compose = docker_cfg.get("compose_file")
        docker_health = docker_cfg.get("health_endpoint")

        try:
            tool_outputs, tools_ran, tools_success = _run_java_tools(
                config, repo_path, workdir, output_dir, build_tool, problems
            )
        except Exception as exc:
            message = f"Tool execution failed: {exc}"
            if json_mode:
                return CommandResult(
                    exit_code=EXIT_INTERNAL_ERROR,
                    summary=message,
                    problems=[{"severity": "error", "message": message}],
                )
            print(message)
            return EXIT_INTERNAL_ERROR

        tools_configured = {tool: _tool_enabled(config, tool, "java") for tool in JAVA_TOOLS}
        thresholds = resolve_thresholds(config, "java")
        context = _build_context(
            repo_path,
            config,
            workdir,
            args.correlation_id,
            build_tool=build_tool,
            project_type=project_type,
            docker_compose_file=docker_compose,
            docker_health_endpoint=docker_health,
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
        gate_failures = _evaluate_java_gates(report, thresholds, tools_configured)

    else:
        message = f"cihub ci supports python or java (got '{language}')"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(message)
        return EXIT_FAILURE

    report_path = Path(args.report) if args.report else output_dir / "report.json"
    if not report_path.is_absolute():
        report_path = repo_path / report_path
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary_text = render_summary(report)
    summary_path = Path(args.summary) if args.summary else output_dir / "summary.md"
    if not summary_path.is_absolute():
        summary_path = repo_path / summary_path
    summary_path.write_text(summary_text, encoding="utf-8")

    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        Path(github_summary).write_text(summary_text, encoding="utf-8")

    if gate_failures:
        problems.extend(
            [
                {
                    "severity": "error",
                    "message": failure,
                    "code": "CIHUB-CI-GATE",
                }
                for failure in gate_failures
            ]
        )

    has_errors = any(p.get("severity") == "error" for p in problems)
    exit_code = EXIT_FAILURE if has_errors else EXIT_SUCCESS
    if json_mode:
        result = CommandResult(
            exit_code=exit_code,
            summary="CI completed with issues" if problems else "CI completed",
            problems=problems,
            artifacts={
                "report": str(report_path),
                "summary": str(summary_path),
            },
            data={
                "report_path": str(report_path),
                "summary_path": str(summary_path),
            },
        )
        return result

    print(f"Wrote report: {report_path}")
    print(f"Wrote summary: {summary_path}")
    if problems:
        print("CI findings:")
        for problem in problems:
            severity = problem.get("severity", "error")
            print(f"  - [{severity}] {problem.get('message')}")
    return exit_code
