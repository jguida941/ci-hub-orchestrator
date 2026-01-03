"""Parser setup for POM helper commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_pom_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    fix_pom = subparsers.add_parser(
        "fix-pom",
        help="Add missing Maven plugins/dependencies to pom.xml for Java repos",
    )
    add_json_flag(fix_pom)
    fix_pom.add_argument("--repo", required=True, help="Path to repo")
    fix_pom.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_pom.set_defaults(func=handlers.cmd_fix_pom)

    fix_deps = subparsers.add_parser("fix-deps", help="Add missing Maven dependencies for Java repos")
    add_json_flag(fix_deps)
    fix_deps.add_argument("--repo", required=True, help="Path to repo")
    fix_deps.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default: dry-run diff)",
    )
    fix_deps.set_defaults(func=handlers.cmd_fix_deps)
