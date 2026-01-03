"""Tests for cihub.services.report_summary module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from cihub.services.report_summary import (
    ReportSummaryResult,
    render_summary_from_path,
    render_summary_from_report,
)


def test_result_dataclass_defaults() -> None:
    """Test ReportSummaryResult has correct defaults."""
    result = ReportSummaryResult(success=True)
    assert result.summary_text == ""
    assert result.report == {}
    assert result.report_path is None


def test_render_summary_from_report_success() -> None:
    """Test successful report rendering."""
    report = {
        "status": "success",
        "language": "python",
        "timestamp": "2025-01-01T00:00:00Z",
        "thresholds": {},
    }
    result = render_summary_from_report(report)

    assert result.success is True
    assert result.errors == []
    assert result.summary_text != ""
    assert result.report == report


def test_render_summary_from_report_without_metrics() -> None:
    """Test rendering without metrics."""
    report = {
        "status": "success",
        "language": "python",
        "timestamp": "2025-01-01T00:00:00Z",
        "thresholds": {},
    }
    result = render_summary_from_report(report, include_metrics=False)

    assert result.success is True
    assert result.summary_text != ""


def test_render_summary_from_report_handles_exception() -> None:
    """Test that exceptions are caught and returned as errors."""
    with mock.patch(
        "cihub.services.report_summary.render_summary",
        side_effect=ValueError("Bad data"),
    ):
        result = render_summary_from_report({})

    assert result.success is False
    assert "Bad data" in result.errors[0]


def test_render_summary_from_path_success(tmp_path: Path) -> None:
    """Test rendering from a valid report file."""
    report_path = tmp_path / "report.json"
    report = {
        "status": "success",
        "language": "python",
        "timestamp": "2025-01-01T00:00:00Z",
        "thresholds": {},
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = render_summary_from_path(report_path)

    assert result.success is True
    assert result.summary_text != ""
    assert result.report == report
    assert result.report_path == report_path


def test_render_summary_from_path_file_not_found(tmp_path: Path) -> None:
    """Test handling of missing file."""
    missing = tmp_path / "missing.json"
    result = render_summary_from_path(missing)

    assert result.success is False
    assert len(result.errors) > 0
    assert result.report_path == missing


def test_render_summary_from_path_invalid_json(tmp_path: Path) -> None:
    """Test handling of invalid JSON file."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json", encoding="utf-8")

    result = render_summary_from_path(bad_file)

    assert result.success is False
    assert len(result.errors) > 0
    assert result.report_path == bad_file


def test_render_summary_from_path_render_exception(tmp_path: Path) -> None:
    """Test handling exception during render."""
    report_path = tmp_path / "report.json"
    report_path.write_text('{"status": "success"}', encoding="utf-8")

    with mock.patch(
        "cihub.services.report_summary.render_summary",
        side_effect=RuntimeError("Render failed"),
    ):
        result = render_summary_from_path(report_path)

    assert result.success is False
    assert "Render failed" in result.errors[0]
    assert result.report_path == report_path
