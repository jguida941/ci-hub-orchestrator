"""Parser setup for ADR commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_adr_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    adr = subparsers.add_parser("adr", help="Manage Architecture Decision Records")
    adr_sub = adr.add_subparsers(dest="subcommand")
    adr.set_defaults(func=handlers.cmd_adr)

    adr_new = adr_sub.add_parser("new", help="Create a new ADR from template")
    add_json_flag(adr_new)
    adr_new.add_argument("title", help="Title for the new ADR")
    adr_new.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing",
    )
    adr_new.set_defaults(func=handlers.cmd_adr)

    adr_list = adr_sub.add_parser("list", help="List all ADRs with status")
    add_json_flag(adr_list)
    adr_list.add_argument(
        "--status",
        help="Filter by status (e.g., accepted, proposed, deprecated)",
    )
    adr_list.set_defaults(func=handlers.cmd_adr)

    adr_check = adr_sub.add_parser("check", help="Validate ADRs for broken links and missing fields")
    add_json_flag(adr_check)
    adr_check.set_defaults(func=handlers.cmd_adr)
