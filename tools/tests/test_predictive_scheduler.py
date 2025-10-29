from __future__ import annotations

import json
from pathlib import Path

from tools import predictive_scheduler as scheduler


def _telemetry(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "telemetry.ndjson"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle)
            handle.write("\n")
    return path


def test_summarize_builds_runner_recommendation(tmp_path):
    telemetry = _telemetry(
        tmp_path,
        [
            {
                "job": "project-tests",
                "duration_ms": 240000,
                "queue_ms": 1000,
                "tests_total": 1200,
                "cache_hit": True,
                "changed_files": 10,
                "runner_type": "hosted",
                "runner_size": "small",
            },
            {
                "job": "project-tests",
                "duration_ms": 360000,
                "queue_ms": 1000,
                "tests_total": 1500,
                "cache_hit": False,
                "changed_files": 20,
                "runner_type": "hosted",
                "runner_size": "medium",
            },
        ],
    )
    samples = scheduler.load_samples(telemetry)
    report = scheduler.summarize("project-tests", samples)
    assert report["job"] == "project-tests"
    assert report["recommendation"]["runner_size"] in {"small", "medium"}
    assert report["stats"]["avg_duration_ms"] > 0


def test_percentile_handles_single_value():
    assert scheduler.percentile([100], 0.95) == 100
    assert scheduler.percentile([], 0.95) == 0.0

