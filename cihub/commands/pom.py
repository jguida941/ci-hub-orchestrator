"""POM-related command handlers."""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from cihub.cli import (
    CommandResult,
    apply_dependency_fixes,
    apply_pom_fixes,
    load_effective_config,
)
from cihub.exit_codes import EXIT_SUCCESS, EXIT_USAGE


def cmd_fix_pom(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        message = f"Config not found: {config_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_USAGE
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        message = "fix-pom is only supported for Java repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        message = "fix-pom only supports Maven repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if json_mode:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = apply_pom_fixes(repo_path, config, apply=args.apply)
            status = max(status, apply_dependency_fixes(repo_path, config, apply=args.apply))
        summary = "POM fix applied" if args.apply else "POM fix dry-run complete"
        return CommandResult(
            exit_code=status,
            summary=summary,
            data={"applied": bool(args.apply)},
        )
    status = apply_pom_fixes(repo_path, config, apply=args.apply)
    status = max(status, apply_dependency_fixes(repo_path, config, apply=args.apply))
    return status


def cmd_fix_deps(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        message = f"Config not found: {config_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message, file=sys.stderr)
        return EXIT_USAGE
    config = load_effective_config(repo_path)
    if config.get("language") != "java":
        message = "fix-deps is only supported for Java repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if config.get("java", {}).get("build_tool", "maven") != "maven":
        message = "fix-deps only supports Maven repos."
        if json_mode:
            return CommandResult(exit_code=EXIT_SUCCESS, summary=message)
        print(message)
        return EXIT_SUCCESS
    if json_mode:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = apply_dependency_fixes(repo_path, config, apply=args.apply)
        summary = "Dependencies applied" if args.apply else "Dependency dry-run complete"
        return CommandResult(
            exit_code=status,
            summary=summary,
            data={"applied": bool(args.apply)},
        )
    return apply_dependency_fixes(repo_path, config, apply=args.apply)
