"""Aggregation service - thin wrapper around existing aggregation logic.

This service wraps cihub.aggregation functions to provide a structured
API for GUI/programmatic access while preserving existing behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cihub.aggregation import run_aggregation as _run_aggregation
from cihub.aggregation import run_reports_aggregation as _run_reports_aggregation
from cihub.services.types import ServiceResult


@dataclass
class AggregationResult(ServiceResult):
    """Result of report aggregation."""

    report_path: Path | None = None
    summary_path: Path | None = None
    report_data: dict[str, Any] = field(default_factory=dict)
    total_repos: int = 0
    dispatched_repos: int = 0
    passed_count: int = 0
    failed_count: int = 0
    threshold_exceeded: bool = False


def aggregate_from_dispatch(
    dispatch_dir: Path,
    output_file: Path,
    defaults_file: Path,
    token: str,
    hub_run_id: str,
    hub_event: str,
    total_repos: int = 0,
    summary_file: Path | None = None,
    strict: bool = False,
    timeout_sec: int = 1800,
) -> AggregationResult:
    """Aggregate reports by fetching artifacts from dispatched workflow runs.

    This wraps cihub.aggregation.run_aggregation() and returns structured result.

    Args:
        dispatch_dir: Directory containing dispatch metadata JSON files.
        output_file: Path to write aggregated report.json.
        defaults_file: Path to defaults.yaml with thresholds.
        token: GitHub token for API access.
        hub_run_id: Hub orchestrator run ID.
        hub_event: Event that triggered the hub run.
        total_repos: Expected total repos (0 = use dispatch count).
        summary_file: Optional path for summary markdown.
        strict: Fail on any failed runs or threshold violations.
        timeout_sec: Timeout for polling workflow completion.

    Returns:
        AggregationResult with success status and report data.
    """
    exit_code = _run_aggregation(
        dispatch_dir=dispatch_dir,
        output_file=output_file,
        summary_file=summary_file,
        defaults_file=defaults_file,
        token=token,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        strict=strict,
        timeout_sec=timeout_sec,
    )

    return _build_result(
        exit_code=exit_code,
        output_file=output_file,
        summary_file=summary_file,
    )


def aggregate_from_reports_dir(
    reports_dir: Path,
    output_file: Path,
    defaults_file: Path,
    hub_run_id: str,
    hub_event: str,
    total_repos: int = 0,
    summary_file: Path | None = None,
    strict: bool = False,
) -> AggregationResult:
    """Aggregate reports from a local directory of report.json files.

    This wraps cihub.aggregation.run_reports_aggregation() and returns structured result.

    Args:
        reports_dir: Directory containing report.json files (searched recursively).
        output_file: Path to write aggregated report.json.
        defaults_file: Path to defaults.yaml with thresholds.
        hub_run_id: Hub orchestrator run ID.
        hub_event: Event that triggered the hub run.
        total_repos: Expected total repos (0 = use found count).
        summary_file: Optional path for summary markdown.
        strict: Fail on any failed runs or threshold violations.

    Returns:
        AggregationResult with success status and report data.
    """
    exit_code = _run_reports_aggregation(
        reports_dir=reports_dir,
        output_file=output_file,
        summary_file=summary_file,
        defaults_file=defaults_file,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
        strict=strict,
    )

    return _build_result(
        exit_code=exit_code,
        output_file=output_file,
        summary_file=summary_file,
    )


def _build_result(
    exit_code: int,
    output_file: Path,
    summary_file: Path | None,
) -> AggregationResult:
    """Build AggregationResult from exit code and written files."""
    errors: list[str] = []
    warnings: list[str] = []
    report_data: dict[str, Any] = {}

    # Read the report data from the output file
    if output_file.exists():
        try:
            report_data = json.loads(output_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Failed to read output file: {exc}")

    # Extract counts from report data
    total_repos = int(report_data.get("total_repos", 0))
    dispatched_repos = int(report_data.get("dispatched_repos", 0))
    runs = report_data.get("runs", [])

    passed_count = len([r for r in runs if r.get("status") == "completed" and r.get("conclusion") == "success"])
    failed_count = len(runs) - passed_count

    # Check for threshold violations
    total_critical = int(report_data.get("total_critical_vulns", 0) or 0)
    total_high = int(report_data.get("total_high_vulns", 0) or 0)
    threshold_exceeded = total_critical > 0 or total_high > 0  # Simplified check

    # Add errors/warnings based on exit code
    if exit_code != 0:
        if failed_count > 0:
            errors.append(f"{failed_count} runs failed")
        if threshold_exceeded:
            errors.append("Vulnerability thresholds exceeded")

    return AggregationResult(
        success=exit_code == 0,
        errors=errors,
        warnings=warnings,
        report_path=output_file if output_file.exists() else None,
        summary_path=summary_file if summary_file and summary_file.exists() else None,
        report_data=report_data,
        total_repos=total_repos,
        dispatched_repos=dispatched_repos,
        passed_count=passed_count,
        failed_count=failed_count,
        threshold_exceeded=threshold_exceeded,
    )
