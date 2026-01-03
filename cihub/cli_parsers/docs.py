"""Parser setup for docs commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_docs_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    docs = subparsers.add_parser("docs", help="Generate reference documentation")
    docs.set_defaults(func=handlers.cmd_docs)
    docs_sub = docs.add_subparsers(dest="subcommand", required=True)

    docs_generate = docs_sub.add_parser("generate", help="Generate CLI and config reference docs")
    add_json_flag(docs_generate)
    docs_generate.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_generate.add_argument(
        "--check",
        action="store_true",
        help="Fail if docs would change",
    )
    docs_generate.set_defaults(func=handlers.cmd_docs)

    docs_check = docs_sub.add_parser("check", help="Check reference docs are up to date")
    add_json_flag(docs_check)
    docs_check.add_argument(
        "--output",
        default="docs/reference",
        help="Output directory (default: docs/reference)",
    )
    docs_check.set_defaults(func=handlers.cmd_docs)

    docs_links = docs_sub.add_parser("links", help="Check documentation for broken links")
    add_json_flag(docs_links)
    docs_links.add_argument(
        "--external",
        action="store_true",
        help="Also check external (http/https) links (requires lychee)",
    )
    docs_links.set_defaults(func=handlers.cmd_docs_links)
