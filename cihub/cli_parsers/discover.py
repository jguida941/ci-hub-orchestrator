"""Parser setup for discovery commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_discover_command(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    # Discover command - generates matrix for hub-run-all.yml
    discover = subparsers.add_parser("discover", help="Generate repo matrix for hub-run-all.yml")
    add_json_flag(discover)
    discover.add_argument(
        "--hub-root",
        help="Path to hub-release directory (default: auto-detect)",
    )
    discover.add_argument(
        "--repos",
        help="Filter to specific repos (comma-separated)",
    )
    discover.add_argument(
        "--run-group",
        help="Filter by run group (comma-separated: full,smoke,fixtures)",
    )
    discover.add_argument(
        "--central-only",
        action="store_true",
        help="Only include repos with repo.use_central_runner=true",
    )
    discover.add_argument(
        "--dispatch-only",
        action="store_true",
        help="Only include repos with repo.use_central_runner=false",
    )
    discover.add_argument(
        "--github-output",
        action="store_true",
        help="Write matrix and count to GITHUB_OUTPUT",
    )
    discover.set_defaults(func=handlers.cmd_discover)
