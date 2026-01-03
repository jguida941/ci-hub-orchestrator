"""Parser setup for config-related commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_config_outputs_command(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    config_outputs = subparsers.add_parser(
        "config-outputs",
        help="Emit config outputs for GitHub Actions",
    )
    add_json_flag(config_outputs)
    config_outputs.add_argument("--repo", default=".", help="Path to repo (default: .)")
    config_outputs.add_argument("--workdir", help="Override workdir/subdir")
    config_outputs.add_argument(
        "--github-output",
        action="store_true",
        help="Write outputs to GITHUB_OUTPUT",
    )
    config_outputs.set_defaults(func=handlers.cmd_config_outputs)


def add_config_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    config = subparsers.add_parser(
        "config",
        help="Manage hub-side repo configs (config/repos/*.yaml)",
    )
    add_json_flag(config)
    config.add_argument(
        "--repo",
        help="Repo config name (required for most subcommands)",
    )
    config.add_argument(
        "--dry-run",
        action="store_true",
        help="Show updates without writing",
    )
    config_sub = config.add_subparsers(dest="subcommand")
    config.set_defaults(func=handlers.cmd_config)

    config_edit = config_sub.add_parser("edit", help="Edit config via wizard")
    add_json_flag(config_edit)
    config_edit.set_defaults(func=handlers.cmd_config)

    config_show = config_sub.add_parser("show", help="Show config")
    add_json_flag(config_show)
    config_show.add_argument(
        "--effective",
        action="store_true",
        help="Show merged defaults + repo config",
    )
    config_show.set_defaults(func=handlers.cmd_config)

    config_set = config_sub.add_parser("set", help="Set a config value")
    add_json_flag(config_set)
    config_set.add_argument("path", help="Dot path (e.g., repo.use_central_runner)")
    config_set.add_argument("value", help="Value (YAML literal)")
    config_set.set_defaults(func=handlers.cmd_config)

    config_enable = config_sub.add_parser("enable", help="Enable a tool")
    add_json_flag(config_enable)
    config_enable.add_argument("tool", help="Tool name (e.g., jacoco)")
    config_enable.set_defaults(func=handlers.cmd_config)

    config_disable = config_sub.add_parser("disable", help="Disable a tool")
    add_json_flag(config_disable)
    config_disable.add_argument("tool", help="Tool name (e.g., jacoco)")
    config_disable.set_defaults(func=handlers.cmd_config)

    config_apply_profile = config_sub.add_parser("apply-profile", help="Apply a profile to a repo config")
    add_json_flag(config_apply_profile)
    config_apply_profile.add_argument(
        "--profile",
        required=True,
        help="Path to profile YAML (e.g., templates/profiles/python-fast.yaml)",
    )
    config_apply_profile.add_argument(
        "--target",
        help="Path to target repo config YAML (overrides --repo)",
    )
    config_apply_profile.add_argument(
        "--output",
        help="Optional output path (defaults to target path)",
    )
    config_apply_profile.set_defaults(func=handlers.cmd_config)
