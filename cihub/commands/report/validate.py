"""Report validation commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cihub.cli import CommandResult
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import ValidationRules, validate_report


def _validate_report(args: argparse.Namespace, json_mode: bool) -> int | CommandResult:
    """Validate report.json structure and content."""
    report_path = Path(args.report)
    if not report_path.exists():
        message = f"Report file not found: {report_path}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON in report: {exc}"
        if json_mode:
            return CommandResult(exit_code=EXIT_FAILURE, summary=message)
        print(f"Error: {message}")
        return EXIT_FAILURE

    errors: list[str] = []
    expect_mode = getattr(args, "expect", "clean")
    coverage_min = getattr(args, "coverage_min", 70)

    summary_text = None
    if getattr(args, "summary", None):
        summary_path = Path(args.summary)
        if not summary_path.exists():
            errors.append(f"summary file not found: {summary_path}")
        else:
            summary_text = summary_path.read_text(encoding="utf-8")

    reports_dir = None
    if getattr(args, "reports_dir", None):
        reports_dir = Path(args.reports_dir)
        if not reports_dir.exists():
            errors.append(f"reports dir not found: {reports_dir}")
            reports_dir = None

    rules = ValidationRules(
        expect_clean=expect_mode == "clean",
        coverage_min=coverage_min,
        strict=bool(getattr(args, "strict", False)),
    )
    result = validate_report(
        report,
        rules,
        summary_text=summary_text,
        reports_dir=reports_dir,
    )

    errors.extend(result.errors)
    warnings = list(result.warnings)

    if getattr(args, "debug", False) and result.debug_messages:
        print("Validation debug output:")
        for msg in result.debug_messages:
            print(f"  {msg}")

    if getattr(args, "verbose", False):
        print(f"\nErrors: {len(errors)}, Warnings: {len(warnings)}")

    if errors:
        if not json_mode:
            print(f"Validation FAILED with {len(errors)} errors:")
            for err in errors:
                print(f"  ::error::{err}")
        if warnings:
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=f"Validation failed: {len(errors)} errors",
                problems=[{"severity": "error", "message": e} for e in errors]
                + [{"severity": "warning", "message": w} for w in warnings],
            )
        return EXIT_FAILURE

    if warnings:
        if not json_mode:
            print(f"Validation passed with {len(warnings)} warnings:")
            for warn in warnings:
                print(f"  ::warning::{warn}")
        if rules.strict:
            if json_mode:
                return CommandResult(
                    exit_code=EXIT_FAILURE,
                    summary=f"Validation failed (strict): {len(warnings)} warnings",
                    problems=[{"severity": "warning", "message": w} for w in warnings],
                )
            return EXIT_FAILURE

    if not json_mode:
        print("Validation PASSED")
    if json_mode:
        return CommandResult(exit_code=EXIT_SUCCESS, summary="Validation passed")
    return EXIT_SUCCESS
