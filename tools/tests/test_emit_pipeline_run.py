"""Tests for scripts.emit_pipeline_run helper functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.emit_pipeline_run import _load_autopsy_findings


def _write_autopsy_report(path: Path, findings: list[dict[str, object]] | None = None) -> None:
    payload = {"schema": "autopsy.v1", "findings": findings or []}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_autopsy_findings_happy_path(tmp_path: Path) -> None:
    report = tmp_path / "autopsy.json"
    _write_autopsy_report(
        report,
        [
            {
                "tool": "pytest",
                "pattern": "E123",
                "file": "tests/test_example.py",
                "line": 42,
                "message": "Sample failure",
                "severity": "high",
                "suggestion": "Fix the flaky test",
                "extra": "ignored",
            }
        ],
    )

    findings = _load_autopsy_findings(report)

    assert findings == [
        {
            "tool": "pytest",
            "pattern": "E123",
            "file": "tests/test_example.py",
            "line": 42,
            "message": "Sample failure",
            "severity": "high",
            "suggestion": "Fix the flaky test",
        }
    ]


def test_load_autopsy_findings_missing_required_field(tmp_path: Path) -> None:
    report = tmp_path / "autopsy-missing.json"
    _write_autopsy_report(
        report,
        [
            {
                "tool": "pytest",
                "pattern": "E123",
                "file": "tests/test_example.py",
                "line": 42,
                "message": "Sample failure",
                # severity missing
            }
        ],
    )

    with pytest.raises(SystemExit, match="missing required fields"):
        _load_autopsy_findings(report)


def test_load_autopsy_findings_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "not-there.json"
    with pytest.raises(SystemExit, match="autopsy report not found"):
        _load_autopsy_findings(missing)
