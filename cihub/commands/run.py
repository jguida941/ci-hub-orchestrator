"""Run a single tool and emit JSON output."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from cihub.ci_config import load_ci_config
from cihub.ci_runner import (
    ToolResult,
    run_bandit,
    run_black,
    run_isort,
    run_mutmut,
    run_mypy,
    run_pip_audit,
    run_pytest,
    run_ruff,
    run_semgrep,
    run_trivy,
)
from cihub.cli import CommandResult, validate_subdir
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE

RUNNERS: dict[str, Callable[..., ToolResult]] = {
    "pytest": run_pytest,
    "ruff": run_ruff,
    "black": run_black,
    "isort": run_isort,
    "mypy": run_mypy,
    "bandit": run_bandit,
    "pip_audit": run_pip_audit,
    "pip-audit": run_pip_audit,
    "mutmut": run_mutmut,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
}


def _tool_enabled(config: dict[str, Any], tool: str) -> bool:
    python_block = config.get("python", {})
    tools = python_block.get("tools", {}) if isinstance(python_block, dict) else {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def cmd_run(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo or ".").resolve()
    json_mode = getattr(args, "json", False)
    tool = args.tool
    tool_key = "pip_audit" if tool == "pip-audit" else tool
    output_dir = Path(args.output_dir or ".cihub")
    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)
    output_name = tool_key
    output_path = Path(args.output) if args.output else tool_output_dir / f"{output_name}.json"

    try:
        config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    workdir = args.workdir or config.get("repo", {}).get("subdir") or "."
    validate_subdir(workdir)
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        message = f"Workdir not found: {workdir_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    runner = RUNNERS.get(tool)
    if runner is None:
        message = f"Unsupported tool: {tool}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message)
        return EXIT_USAGE

    if not args.force and not _tool_enabled(config, tool_key):
        result = ToolResult(tool=tool_key, ran=False, success=False)
        result.write_json(output_path)
        if json_mode:
            return CommandResult(
                exit_code=EXIT_SUCCESS,
                summary=f"{tool_key} skipped (disabled)",
                artifacts={"output": str(output_path)},
            )
        print(f"{tool_key} skipped (disabled)")
        return EXIT_SUCCESS

    try:
        if tool == "mutmut":
            timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
            result = runner(workdir_path, output_dir, int(timeout) * 60)
        else:
            result = runner(workdir_path, output_dir)
    except FileNotFoundError as exc:
        message = f"Tool '{tool}' not found: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    result.write_json(output_path)
    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS if result.success else EXIT_FAILURE,
            summary=f"{tool} {'passed' if result.success else 'failed'}",
            artifacts={"output": str(output_path)},
            data=result.to_payload(),
        )
    print(f"Wrote output: {output_path}")
    return EXIT_SUCCESS if result.success else EXIT_FAILURE
