"""Parser setup for triage commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_triage_command(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    triage = subparsers.add_parser("triage", help="Generate triage bundle outputs")
    add_json_flag(triage)
    triage.add_argument(
        "--output-dir",
        help="Output directory (default: .cihub)",
    )
    triage.add_argument(
        "--report",
        help="Path to report.json (default: <output-dir>/report.json)",
    )
    triage.add_argument(
        "--summary",
        help="Path to summary.md (default: <output-dir>/summary.md)",
    )
    triage.set_defaults(func=handlers.cmd_triage)
