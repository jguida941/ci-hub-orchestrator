"""Tests for cihub.services.aggregation module."""

from __future__ import annotations

import json
from pathlib import Path

from cihub.services import AggregationResult, aggregate_from_reports_dir


class TestAggregationResult:
    """Tests for AggregationResult dataclass."""

    def test_success_property(self):
        """success reflects exit code."""
        result = AggregationResult(success=True, passed_count=5, failed_count=0)
        assert result.success is True

        result = AggregationResult(success=False, errors=["some error"])
        assert result.success is False


class TestAggregateFromReportsDir:
    """Tests for aggregate_from_reports_dir service function."""

    def test_aggregates_single_report(self, tmp_path: Path):
        """Aggregates a single report.json file."""
        reports_dir = tmp_path / "reports" / "sample-ci-report" / ".cihub"
        reports_dir.mkdir(parents=True)
        report = {
            "schema_version": "2.0",
            "repository": "org/sample",
            "branch": "main",
            "run_id": "123",
            "hub_correlation_id": "hub-1",
            "python_version": "3.12",
            "results": {
                "test": "success",
                "coverage": 80,
                "mutation_score": 70,
                "tests_failed": 0,
            },
            "tool_metrics": {"ruff_errors": 0},
            "tools_configured": {"pytest": True},
            "tools_ran": {"pytest": True},
            "tools_success": {"pytest": True},
            "environment": {"workdir": "."},
        }
        (reports_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        defaults_file = tmp_path / "defaults.yaml"
        defaults_file.write_text(
            "thresholds:\n  max_critical_vulns: 0\n  max_high_vulns: 0\n",
            encoding="utf-8",
        )

        output_file = tmp_path / "hub-report.json"
        summary_file = tmp_path / "summary.md"

        result = aggregate_from_reports_dir(
            reports_dir=tmp_path / "reports",
            output_file=output_file,
            defaults_file=defaults_file,
            hub_run_id="hub-1",
            hub_event="workflow_dispatch",
            total_repos=1,
            summary_file=summary_file,
            strict=False,
        )

        assert result.success is True
        assert result.report_path == output_file
        assert result.summary_path == summary_file
        assert result.dispatched_repos == 1
        assert result.passed_count == 1
        assert result.failed_count == 0
        assert len(result.errors) == 0

    def test_returns_report_data(self, tmp_path: Path):
        """Result includes parsed report data."""
        reports_dir = tmp_path / "reports" / "sample" / ".cihub"
        reports_dir.mkdir(parents=True)
        report = {
            "schema_version": "2.0",
            "repository": "org/sample",
            "branch": "main",
            "run_id": "456",
            "python_version": "3.12",
            "results": {"coverage": 90, "tests_failed": 0},
            "tool_metrics": {},
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
        }
        (reports_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        defaults_file = tmp_path / "defaults.yaml"
        defaults_file.write_text("thresholds: {}\n", encoding="utf-8")

        output_file = tmp_path / "out.json"

        result = aggregate_from_reports_dir(
            reports_dir=tmp_path / "reports",
            output_file=output_file,
            defaults_file=defaults_file,
            hub_run_id="hub-2",
            hub_event="push",
            total_repos=0,
        )

        assert result.success is True
        assert "runs" in result.report_data
        assert len(result.report_data["runs"]) == 1

    def test_handles_invalid_report(self, tmp_path: Path):
        """Handles invalid report.json gracefully."""
        reports_dir = tmp_path / "reports" / "bad" / ".cihub"
        reports_dir.mkdir(parents=True)
        (reports_dir / "report.json").write_text("not valid json {", encoding="utf-8")

        defaults_file = tmp_path / "defaults.yaml"
        defaults_file.write_text("thresholds: {}\n", encoding="utf-8")

        output_file = tmp_path / "out.json"

        result = aggregate_from_reports_dir(
            reports_dir=tmp_path / "reports",
            output_file=output_file,
            defaults_file=defaults_file,
            hub_run_id="hub-3",
            hub_event="push",
            total_repos=1,
        )

        # Aggregation continues but marks the report as invalid
        assert result.dispatched_repos == 1
        assert result.failed_count == 1
        assert result.passed_count == 0

    def test_no_summary_file(self, tmp_path: Path):
        """Works without summary file."""
        reports_dir = tmp_path / "reports" / "sample" / ".cihub"
        reports_dir.mkdir(parents=True)
        report = {
            "schema_version": "2.0",
            "repository": "org/sample",
            "python_version": "3.12",
            "results": {"coverage": 80, "tests_failed": 0},
            "tool_metrics": {},
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
        }
        (reports_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        defaults_file = tmp_path / "defaults.yaml"
        defaults_file.write_text("thresholds: {}\n", encoding="utf-8")

        output_file = tmp_path / "out.json"

        result = aggregate_from_reports_dir(
            reports_dir=tmp_path / "reports",
            output_file=output_file,
            defaults_file=defaults_file,
            hub_run_id="hub-4",
            hub_event="push",
            total_repos=0,
            summary_file=None,
        )

        assert result.success is True
        assert result.summary_path is None


class TestBuildResultEdgeCases:
    """Tests for _build_result edge cases."""

    def test_handles_json_decode_error(self, tmp_path: Path):
        """Handles corrupted JSON in output file."""
        from cihub.services.aggregation import _build_result

        output_file = tmp_path / "corrupted.json"
        output_file.write_text("not valid {json", encoding="utf-8")

        result = _build_result(
            exit_code=0,
            output_file=output_file,
            summary_file=None,
        )

        assert "Failed to read output file" in result.errors[0]
        assert result.report_data == {}

    def test_records_failed_runs(self, tmp_path: Path):
        """Records failed runs in errors when exit code is non-zero."""
        from cihub.services.aggregation import _build_result

        output_file = tmp_path / "report.json"
        output_file.write_text(
            json.dumps({
                "runs": [
                    {"status": "completed", "conclusion": "failure"},
                    {"status": "completed", "conclusion": "failure"},
                ],
            }),
            encoding="utf-8",
        )

        result = _build_result(
            exit_code=1,
            output_file=output_file,
            summary_file=None,
        )

        assert result.success is False
        assert result.failed_count == 2
        assert "2 runs failed" in result.errors[0]

    def test_records_threshold_violation(self, tmp_path: Path):
        """Records threshold violations in errors."""
        from cihub.services.aggregation import _build_result

        output_file = tmp_path / "report.json"
        output_file.write_text(
            json.dumps({
                "runs": [],
                "total_critical_vulns": 5,
            }),
            encoding="utf-8",
        )

        result = _build_result(
            exit_code=1,
            output_file=output_file,
            summary_file=None,
        )

        assert result.threshold_exceeded is True
        assert "Vulnerability thresholds exceeded" in result.errors


class TestAggregateFromDispatch:
    """Tests for aggregate_from_dispatch function."""

    def test_calls_run_aggregation(self, tmp_path: Path):
        """Calls the underlying run_aggregation function."""
        from unittest.mock import patch

        from cihub.services.aggregation import aggregate_from_dispatch

        dispatch_dir = tmp_path / "dispatches"
        dispatch_dir.mkdir()
        output_file = tmp_path / "output.json"
        defaults_file = tmp_path / "defaults.yaml"
        defaults_file.write_text("thresholds: {}\n", encoding="utf-8")

        # Mock the underlying function to just create an empty report
        def mock_run_agg(**kwargs):
            kwargs["output_file"].write_text(
                '{"runs": [], "total_repos": 0, "dispatched_repos": 0}',
                encoding="utf-8",
            )
            return 0

        with patch(
            "cihub.services.aggregation._run_aggregation",
            side_effect=mock_run_agg,
        ) as mock_agg:
            result = aggregate_from_dispatch(
                dispatch_dir=dispatch_dir,
                output_file=output_file,
                defaults_file=defaults_file,
                token="test-token",
                hub_run_id="hub-123",
                hub_event="workflow_dispatch",
                total_repos=5,
                summary_file=None,
                strict=False,
                timeout_sec=60,
            )

        mock_agg.assert_called_once()
        assert result.success is True
