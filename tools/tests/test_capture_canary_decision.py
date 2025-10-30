from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import pytest

from scripts.capture_canary_decision import build_decision_payload, parse_args


def _make_args(**overrides) -> argparse.Namespace:
    defaults = {
        "decision": "promote",
        "query_file": None,
        "window_start": None,
        "window_end": None,
        "window_minutes": 10,
        "metrics_uri": None,
        "notes": None,
        "output": Path(tempfile.mkstemp(prefix="capture-test-", suffix=".json")[1]),
        "ndjson": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_build_decision_payload_rejects_inverted_window() -> None:
    args = _make_args(
        window_start="2025-01-02T00:00:00Z",
        window_end="2025-01-01T00:00:00Z",
    )
    with pytest.raises(SystemExit, match="--window-start must be before --window-end"):
        build_decision_payload(args)


def test_parse_args_rejects_non_positive_window_minutes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    output_path = tmp_path / "capture.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "capture",
            "--decision",
            "promote",
            "--output",
            output_path.as_posix(),
            "--window-minutes",
            "0",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        parse_args()
    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "--window-minutes must be positive" in stderr
