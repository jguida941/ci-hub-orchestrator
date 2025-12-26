"""New command handler (hub-side config creation)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from cihub.cli import CommandResult, build_repo_config, hub_root
from cihub.config.io import (
    ensure_dirs,
    load_defaults,
    load_profile_strict,
    save_yaml_file,
)
from cihub.config.merge import deep_merge
from cihub.config.paths import PathConfig
from cihub.wizard import HAS_WIZARD, WizardCancelled


def _apply_repo_defaults(config: dict, defaults: dict) -> dict:
    repo_defaults = defaults.get("repo", {}) if isinstance(defaults, dict) else {}
    repo_block = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    for key in ("use_central_runner", "repo_side_execution"):
        if key in repo_defaults and key not in repo_block:
            repo_block[key] = repo_defaults[key]
    config["repo"] = repo_block
    return config


def _validate_profile_language(profile_cfg: dict, language: str) -> None:
    if not profile_cfg:
        return
    has_java = "java" in profile_cfg
    has_python = "python" in profile_cfg
    if has_java and language != "java":
        raise ValueError("Profile is Java-only; use --language java")
    if has_python and language != "python":
        raise ValueError("Profile is Python-only; use --language python")


def cmd_new(args: argparse.Namespace) -> int | CommandResult:
    paths = PathConfig(str(hub_root()))
    ensure_dirs(paths)
    json_mode = getattr(args, "json", False)

    if json_mode and args.interactive:
        return CommandResult(
            exit_code=2,
            summary="--interactive is not supported with --json",
        )

    name = args.name
    repo_file = Path(paths.repo_file(name))
    if repo_file.exists():
        message = f"Config already exists: {repo_file}"
        if json_mode:
            return CommandResult(exit_code=2, summary=message)
        print(message, file=sys.stderr)
        return 2

    defaults = load_defaults(paths)

    if args.interactive:
        if not HAS_WIZARD:
            print("Install wizard deps: pip install cihub[wizard]", file=sys.stderr)
            return 1
        from rich.console import Console  # noqa: I001
        from cihub.wizard.core import WizardRunner  # noqa: I001

        runner = WizardRunner(Console(), paths)
        try:
            config = runner.run_new_wizard(name, profile=args.profile)
        except WizardCancelled:
            print("Cancelled.", file=sys.stderr)
            return 130
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    else:
        if not args.owner or not args.language:
            print(
                "--owner and --language are required unless --interactive is set",
                file=sys.stderr,
            )
            return 2
        config = build_repo_config(
            args.language,
            args.owner,
            name,
            args.branch or "main",
            subdir=args.subdir,
        )
        config = _apply_repo_defaults(config, defaults)
        if args.profile:
            try:
                profile_cfg = load_profile_strict(paths, args.profile)
            except FileNotFoundError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            _validate_profile_language(profile_cfg, args.language)
            config = deep_merge(config, profile_cfg)

    payload = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
    if args.dry_run:
        if json_mode:
            return CommandResult(
                exit_code=0,
                summary="Dry run complete",
                data={"config": config},
                files_generated=[str(repo_file)],
            )
        print(f"# Would write: {repo_file}")
        print(payload)
        return 0

    if not args.yes:
        if json_mode:
            return CommandResult(
                exit_code=2,
                summary="Confirmation required; re-run with --yes",
            )
        confirm = input(f"Write {repo_file}? [y/N] ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("Cancelled.")
            return 3

    save_yaml_file(repo_file, config, dry_run=False)
    if json_mode:
        return CommandResult(
            exit_code=0,
            summary="Config created",
            data={"config": config},
            files_generated=[str(repo_file)],
        )
    print(f"[OK] Created {repo_file}")
    return 0
