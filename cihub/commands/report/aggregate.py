"""Report aggregation command logic."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import aggregate_from_dispatch, aggregate_from_reports_dir

from .helpers import _resolve_include_details, _resolve_write_summary


def _aggregate_report(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Aggregate reports from dispatch metadata or reports directory."""
    write_summary = _resolve_write_summary(getattr(args, "write_github_summary", None))
    include_details = _resolve_include_details(getattr(args, "include_details", None))
    summary_file = Path(args.summary_file) if args.summary_file else None
    details_file = Path(args.details_output) if args.details_output else None
    if summary_file is None and write_summary:
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            summary_file = Path(summary_env)

    total_repos = args.total_repos or int(os.environ.get("TOTAL_REPOS", 0) or 0)
    hub_run_id = args.hub_run_id or os.environ.get("HUB_RUN_ID", os.environ.get("GITHUB_RUN_ID", ""))
    hub_event = args.hub_event or os.environ.get("HUB_EVENT", os.environ.get("GITHUB_EVENT_NAME", ""))

    reports_dir = getattr(args, "reports_dir", None)
    if reports_dir:
        result = aggregate_from_reports_dir(
            reports_dir=Path(reports_dir),
            output_file=Path(args.output),
            defaults_file=Path(args.defaults_file),
            hub_run_id=hub_run_id,
            hub_event=hub_event,
            total_repos=total_repos,
            summary_file=summary_file,
            details_file=details_file,
            include_details=include_details,
            strict=bool(args.strict),
        )
        exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE
        if json_mode:
            summary = "Aggregation complete" if result.success else "Aggregation failed"
            return CommandResult(
                exit_code=exit_code,
                summary=summary,
                artifacts={
                    "report": str(result.report_path) if result.report_path else "",
                    "summary": str(result.summary_path) if result.summary_path else "",
                    "details": str(result.details_path) if result.details_path else "",
                },
            )
        return exit_code

    token = args.token
    token_env = args.token_env or "HUB_DISPATCH_TOKEN"  # noqa: S105
    if not token:
        token = os.environ.get(token_env)
    if not token and token_env != "GITHUB_TOKEN":  # noqa: S105
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        message = f"Missing token (expected {token_env} or GITHUB_TOKEN)"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    result = aggregate_from_dispatch(
        dispatch_dir=Path(args.dispatch_dir),
        output_file=Path(args.output),
        defaults_file=Path(args.defaults_file),
        token=token,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        summary_file=summary_file,
        details_file=details_file,
        include_details=include_details,
        strict=bool(args.strict),
        timeout_sec=int(args.timeout),
    )
    exit_code = EXIT_SUCCESS if result.success else EXIT_FAILURE

    if json_mode:
        summary = "Aggregation complete" if result.success else "Aggregation failed"
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            artifacts={
                "report": str(result.report_path) if result.report_path else "",
                "summary": str(result.summary_path) if result.summary_path else "",
                "details": str(result.details_path) if result.details_path else "",
            },
        )
    return exit_code
