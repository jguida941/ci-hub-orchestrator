#!/usr/bin/env python3
"""Deprecated shim for hub aggregation (use `python -m cihub report aggregate`)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cihub.aggregation import run_aggregation


def main():
    parser = argparse.ArgumentParser(description="Hub Orchestrator Aggregation (deprecated)")
    parser.add_argument("--dispatch-dir", type=Path, default=Path("dispatch-artifacts"))
    parser.add_argument("--output", type=Path, default=Path("hub-report.json"))
    parser.add_argument("--summary-file", type=Path, default=None)
    parser.add_argument("--defaults-file", type=Path, default=Path("config/defaults.yaml"))
    parser.add_argument("--token-env", default="HUB_DISPATCH_TOKEN", help="Env var containing GitHub token")
    parser.add_argument("--strict", action="store_true", help="Fail on repo failures or threshold violations")
    parser.add_argument("--timeout", type=int, default=1800, help="Polling timeout in seconds")
    args = parser.parse_args()

    token = os.environ.get(args.token_env) or os.environ.get("GITHUB_TOKEN")
    if not token:
        print(f"ERROR: Missing {args.token_env} or GITHUB_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)

    hub_run_id = os.environ.get("HUB_RUN_ID", "")
    hub_event = os.environ.get("HUB_EVENT", "")
    total_repos = int(os.environ.get("TOTAL_REPOS", 0))

    # Handle GITHUB_STEP_SUMMARY
    summary_file = args.summary_file
    if not summary_file:
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            summary_file = Path(summary_env)

    exit_code = run_aggregation(
        dispatch_dir=args.dispatch_dir,
        output_file=args.output,
        summary_file=summary_file,
        defaults_file=args.defaults_file,
        token=token,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        strict=bool(args.strict),
        timeout_sec=int(args.timeout),
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
