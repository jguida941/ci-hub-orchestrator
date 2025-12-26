"""Config management command handler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from cihub.cli import CommandResult, hub_root
from cihub.config.io import (
    ensure_dirs,
    load_defaults,
    load_repo_config,
    save_repo_config,
)
from cihub.config.merge import build_effective_config
from cihub.config.paths import PathConfig
from cihub.wizard import HAS_WIZARD, WizardCancelled


class ConfigError(RuntimeError):
    """Config command error."""


def _load_repo(paths: PathConfig, repo: str) -> dict[str, Any]:
    repo_path = Path(paths.repo_file(repo))
    if not repo_path.exists():
        raise ConfigError(f"Repo config not found: {repo_path}")
    config = load_repo_config(paths, repo)
    if not config:
        raise ConfigError(f"Repo config is empty: {repo_path}")
    return config


def _dump_config(data: dict[str, Any]) -> None:
    print(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))


def _set_nested(config: dict[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ConfigError("Empty path")
    cursor = config
    for key in parts[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[parts[-1]] = value


def _resolve_tool_path(
    config: dict[str, Any],
    defaults: dict[str, Any],
    tool: str,
) -> str:
    language = None
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if repo_block.get("language"):
        language = repo_block.get("language")
    elif config.get("language"):
        language = config.get("language")

    java_tools = defaults.get("java", {}).get("tools", {}) or {}
    python_tools = defaults.get("python", {}).get("tools", {}) or {}

    if language == "java":
        if tool not in java_tools:
            raise ConfigError(f"Unknown tool: {tool}")
        return f"java.tools.{tool}.enabled"
    if language == "python":
        if tool not in python_tools:
            raise ConfigError(f"Unknown tool: {tool}")
        return f"python.tools.{tool}.enabled"

    java_has = tool in java_tools
    python_has = tool in python_tools
    if java_has and not python_has:
        return f"java.tools.{tool}.enabled"
    if python_has and not java_has:
        return f"python.tools.{tool}.enabled"
    if java_has and python_has:
        raise ConfigError(
            "Tool exists in both java and python; set repo.language first"
        )
    raise ConfigError(f"Unknown tool: {tool}")


def _apply_wizard(paths: PathConfig, existing: dict[str, Any]) -> dict[str, Any]:
    if not HAS_WIZARD:
        raise ConfigError("Install wizard deps: pip install cihub[wizard]")
    from rich.console import Console  # noqa: I001
    from cihub.wizard.core import WizardRunner  # noqa: I001

    runner = WizardRunner(Console(), paths)
    return runner.run_config_wizard(existing)


def cmd_config(args: argparse.Namespace) -> int | CommandResult:
    paths = PathConfig(str(hub_root()))
    ensure_dirs(paths)
    json_mode = getattr(args, "json", False)

    repo = args.repo
    if not repo:
        message = "--repo is required"
        if json_mode:
            return CommandResult(exit_code=2, summary=message)
        print(message, file=sys.stderr)
        return 2

    defaults = load_defaults(paths)

    try:
        if args.subcommand in (None, "edit"):
            if json_mode:
                message = "config edit is not supported with --json"
                return CommandResult(
                    exit_code=2,
                    summary=message,
                    problems=[{"severity": "error", "message": message}],
                )
            existing = _load_repo(paths, repo)
            try:
                updated = _apply_wizard(paths, existing)
            except WizardCancelled:
                if json_mode:
                    return CommandResult(exit_code=130, summary="Cancelled")
                print("Cancelled.", file=sys.stderr)
                return 130
            if args.dry_run:
                _dump_config(updated)
                return 0
            save_repo_config(paths, repo, updated, dry_run=False)
            print(f"[OK] Updated {paths.repo_file(repo)}", file=sys.stderr)
            return 0

        if args.subcommand == "show":
            config = _load_repo(paths, repo)
            if args.effective:
                effective = build_effective_config(defaults, None, config)
                data = effective
            else:
                data = config
            if json_mode:
                return CommandResult(
                    exit_code=0,
                    summary="Config loaded",
                    data={"config": data},
                )
            _dump_config(data)
            return 0

        if args.subcommand == "set":
            config = _load_repo(paths, repo)
            value = yaml.safe_load(args.value)
            _set_nested(config, args.path, value)
            if args.dry_run:
                if json_mode:
                    return CommandResult(
                        exit_code=0,
                        summary="Dry run complete",
                        data={"config": config},
                    )
                _dump_config(config)
                return 0
            save_repo_config(paths, repo, config, dry_run=False)
            if json_mode:
                return CommandResult(
                    exit_code=0,
                    summary="Config updated",
                    data={"config": config},
                    files_modified=[str(paths.repo_file(repo))],
                )
            print(f"[OK] Updated {paths.repo_file(repo)}", file=sys.stderr)
            return 0

        if args.subcommand in {"enable", "disable"}:
            config = _load_repo(paths, repo)
            tool_path = _resolve_tool_path(config, defaults, args.tool)
            _set_nested(config, tool_path, args.subcommand == "enable")
            if args.dry_run:
                if json_mode:
                    return CommandResult(
                        exit_code=0,
                        summary="Dry run complete",
                        data={"config": config},
                    )
                _dump_config(config)
                return 0
            save_repo_config(paths, repo, config, dry_run=False)
            if json_mode:
                return CommandResult(
                    exit_code=0,
                    summary="Config updated",
                    data={"config": config},
                    files_modified=[str(paths.repo_file(repo))],
                )
            print(f"[OK] Updated {paths.repo_file(repo)}", file=sys.stderr)
            return 0

        raise ConfigError(f"Unsupported config command: {args.subcommand}")
    except ConfigError as exc:
        if json_mode:
            return CommandResult(
                exit_code=1,
                summary=str(exc),
                problems=[
                    {
                        "severity": "error",
                        "message": str(exc),
                        "code": "CIHUB-CONFIG-001",
                    }
                ],
            )
        print(str(exc), file=sys.stderr)
        return 1
