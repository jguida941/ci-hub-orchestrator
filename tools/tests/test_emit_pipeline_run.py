"""Tests for scripts.emit_pipeline_run helper functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.emit_pipeline_run import _load_autopsy_findings, _load_canary_evidence


def _write_autopsy_report(path: Path, findings: list[dict[str, object]] | None = None) -> None:
    payload = {"schema": "autopsy.v1", "findings": findings or []}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_canary(path: Path, **overrides: object) -> None:
    payload = {
        "decision": "promote",
        "window": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-01T00:05:00Z"},
        "query": "select 1;",
    }
    payload.update(overrides)
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


def test_load_canary_evidence_success(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path)
    payload = _load_canary_evidence(path)
    assert payload["decision"] == "promote"
    assert payload["window"]["start"] == "2025-01-01T00:00:00Z"


def test_load_canary_evidence_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    with pytest.raises(SystemExit, match="canary evidence file not found"):
        _load_canary_evidence(path)


def test_load_canary_evidence_invalid_decision(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path, decision="invalid")
    with pytest.raises(SystemExit, match="invalid"):
        _load_canary_evidence(path)


def test_load_canary_evidence_missing_decision(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("decision", None)
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="missing required field 'decision'"):
        _load_canary_evidence(path)


def test_load_canary_evidence_invalid_window_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path, window={"start": "not-a-timestamp", "end": "2025-01-01T00:05:00Z"})
    with pytest.raises(SystemExit, match="must be a valid ISO-8601 timestamp"):
        _load_canary_evidence(path)


def test_load_canary_evidence_invalid_recorded_at(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path, recorded_at="yesterday")
    with pytest.raises(SystemExit, match="valid ISO-8601 timestamp"):
        _load_canary_evidence(path)


def test_load_canary_evidence_empty_optional_field(tmp_path: Path) -> None:
    path = tmp_path / "canary.json"
    _write_canary(path, notes="  ")
    with pytest.raises(SystemExit, match="must be a non-empty string"):
        _load_canary_evidence(path)
