"""Parser setup for dispatch commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_dispatch_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    # -------------------------------------------------------------------------
    # dispatch - workflow dispatch and metadata helpers
    # -------------------------------------------------------------------------
    dispatch = subparsers.add_parser("dispatch", help="Workflow dispatch helpers for hub orchestration")
    dispatch.set_defaults(func=handlers.cmd_dispatch)
    dispatch_sub = dispatch.add_subparsers(dest="subcommand", required=True)

    dispatch_trigger = dispatch_sub.add_parser("trigger", help="Dispatch a workflow and poll for run ID")
    add_json_flag(dispatch_trigger)
    dispatch_trigger.add_argument("--owner", required=True, help="Repository owner")
    dispatch_trigger.add_argument("--repo", required=True, help="Repository name")
    dispatch_trigger.add_argument("--ref", required=True, help="Git ref (branch) to dispatch on")
    dispatch_trigger.add_argument(
        "--workflow", default="hub-ci.yml", help="Workflow file to dispatch (default: hub-ci.yml)"
    )
    dispatch_trigger.add_argument("--correlation-id", help="Hub correlation ID to pass as input")
    dispatch_trigger.add_argument(
        "--dispatch-enabled",
        type=lambda x: x.lower() != "false",
        default=True,
        help="Whether dispatch is enabled (default: true)",
    )
    dispatch_trigger.add_argument("--token", help="GitHub token (or use HUB_DISPATCH_TOKEN env)")
    dispatch_trigger.add_argument("--token-env", default="HUB_DISPATCH_TOKEN", help="Environment variable for token")
    dispatch_trigger.add_argument(
        "--timeout", type=int, default=1800, help="Timeout in seconds for polling (default: 1800)"
    )

    dispatch_metadata = dispatch_sub.add_parser("metadata", help="Generate dispatch metadata JSON file")
    add_json_flag(dispatch_metadata)
    dispatch_metadata.add_argument("--config-basename", required=True, help="Config file basename")
    dispatch_metadata.add_argument("--owner", required=True, help="Repository owner")
    dispatch_metadata.add_argument("--repo", required=True, help="Repository name")
    dispatch_metadata.add_argument("--output-dir", default="dispatch-results", help="Output directory")
    dispatch_metadata.add_argument("--subdir", help="Repository subdirectory")
    dispatch_metadata.add_argument("--language", help="Repository language")
    dispatch_metadata.add_argument("--branch", help="Git branch")
    dispatch_metadata.add_argument("--workflow", help="Workflow file name")
    dispatch_metadata.add_argument("--run-id", help="Workflow run ID")
    dispatch_metadata.add_argument("--correlation-id", help="Hub correlation ID")
    dispatch_metadata.add_argument("--status", default="unknown", help="Job status")
