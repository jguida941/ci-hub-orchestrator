"""Tests for report aggregate --reports-dir mode."""

from __future__ import annotations

import json
from pathlib import Path

from cihub.aggregation import run_reports_aggregation


def test_run_reports_aggregation_from_reports_dir(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "sample-ci-report" / ".cihub"
    reports_dir.mkdir(parents=True)
    report = {
        "schema_version": "2.0",
        "repository": "org/sample",
        "branch": "main",
        "run_id": "123",
        "hub_correlation_id": "hub-1",
        "python_version": "3.12",
        "results": {"test": "success", "coverage": 80, "mutation_score": 70, "tests_failed": 0},
        "tool_metrics": {"ruff_errors": 0},
        "tools_configured": {"pytest": True},
        "tools_ran": {"pytest": True},
        "tools_success": {"pytest": True},
        "environment": {"workdir": "."},
    }
    (reports_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

    defaults_file = tmp_path / "defaults.yaml"
    defaults_file.write_text("thresholds:\n  max_critical_vulns: 0\n  max_high_vulns: 0\n", encoding="utf-8")

    output_file = tmp_path / "hub-report.json"
    summary_file = tmp_path / "summary.md"

    exit_code = run_reports_aggregation(
        reports_dir=tmp_path / "reports",
        output_file=output_file,
        summary_file=summary_file,
        defaults_file=defaults_file,
        hub_run_id="hub-1",
        hub_event="workflow_dispatch",
        total_repos=1,
        strict=False,
    )

    assert exit_code == 0
    assert output_file.exists()
    assert summary_file.exists()
    report_out = json.loads(output_file.read_text(encoding="utf-8"))
    assert report_out["dispatched_repos"] == 1
