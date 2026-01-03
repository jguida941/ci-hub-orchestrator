"""Parser setup for template sync commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_templates_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    sync_templates = subparsers.add_parser(
        "sync-templates",
        help="Sync caller workflow templates to dispatch-enabled repos",
    )
    add_json_flag(sync_templates)
    sync_templates.add_argument(
        "--repo",
        action="append",
        help="Target repo (owner/name). Repeatable.",
    )
    sync_templates.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include repos with dispatch_enabled=false",
    )
    sync_templates.add_argument(
        "--check",
        action="store_true",
        help="Check for template drift without updating",
    )
    sync_templates.add_argument(
        "--dry-run",
        action="store_true",
        help="Show updates without writing",
    )
    sync_templates.add_argument(
        "--commit-message",
        default="chore: sync hub templates",
        help="Commit message for synced templates",
    )
    sync_templates.add_argument(
        "--update-tag",
        action="store_true",
        default=True,
        help="Update v1 tag to current HEAD (default: true)",
    )
    sync_templates.add_argument(
        "--no-update-tag",
        action="store_false",
        dest="update_tag",
        help="Skip updating v1 tag",
    )
    sync_templates.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (for force-push operations)",
    )
    sync_templates.set_defaults(func=handlers.cmd_sync_templates)
