"""Report outputs command logic."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


def _report_outputs(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Extract outputs from a report.json file."""
    report_path = Path(args.report)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        message = f"Failed to read report: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(message)
        return EXIT_FAILURE

    results = report.get("results", {}) or {}
    status = results.get("build") or results.get("test")
    if status not in {"success", "failure", "skipped"}:
        tests_failed = int(results.get("tests_failed", 0))
        status = "failure" if tests_failed > 0 else "success"

    output_path = Path(args.output) if args.output else None
    if output_path is None:
        output_path_env = os.environ.get("GITHUB_OUTPUT")
        if output_path_env:
            output_path = Path(output_path_env)
    if output_path is None:
        message = "No output target specified for report outputs"
        if json_mode:
            return CommandResult(exit_code=EXIT_USAGE, summary=message)
        print(message)
        return EXIT_USAGE

    output_text = (
        f"build_status={status}\n"
        f"coverage={results.get('coverage', 0)}\n"
        f"mutation_score={results.get('mutation_score', 0)}\n"
    )
    output_path.write_text(output_text, encoding="utf-8")

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary="Report outputs written",
            artifacts={"outputs": str(output_path)},
        )
    print(f"Wrote outputs: {output_path}")
    return EXIT_SUCCESS
