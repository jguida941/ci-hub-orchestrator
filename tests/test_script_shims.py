"""Tests for deprecated script shims."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest


def test_load_config_shim_calls_loader(monkeypatch) -> None:
    from scripts import load_config

    called: dict[str, bool] = {"hit": False}

    def fake_main() -> None:
        called["hit"] = True

    monkeypatch.setattr("cihub.config.loader._main", fake_main)
    load_config.main()

    assert called["hit"] is True


def test_python_ci_badges_shim_imports_main(capsys) -> None:
    import importlib
    import sys

    # Remove from cache if already imported to ensure deprecation warning prints
    if "scripts.python_ci_badges" in sys.modules:
        del sys.modules["scripts.python_ci_badges"]

    module = importlib.import_module("scripts.python_ci_badges")
    captured = capsys.readouterr()

    assert "deprecated" in captured.err.lower()
    assert hasattr(module, "main")


def test_render_summary_shim_invokes_cli(monkeypatch, tmp_path: Path) -> None:
    from scripts import render_summary

    report_path = tmp_path / "report.json"
    report_path.write_text("{}")

    calls: dict[str, Any] = {}

    def fake_call(cmd: list[str]) -> int:
        calls["cmd"] = cmd
        return 0

    monkeypatch.setattr(sys, "argv", ["render_summary.py", "--report", str(report_path)])
    monkeypatch.setattr("subprocess.call", fake_call)

    assert render_summary.main() == 0
    assert calls["cmd"][:4] == [sys.executable, "-m", "cihub", "report"]


def test_validate_summary_shim_invokes_cli(monkeypatch, tmp_path: Path) -> None:
    from scripts import validate_summary

    report_path = tmp_path / "report.json"
    report_path.write_text("{}")

    calls: dict[str, Any] = {}

    def fake_call(cmd: list[str]) -> int:
        calls["cmd"] = cmd
        return 0

    monkeypatch.setattr(sys, "argv", ["validate_summary.py", "--report", str(report_path)])
    monkeypatch.setattr("subprocess.call", fake_call)

    assert validate_summary.main() == 0
    assert calls["cmd"][:4] == [sys.executable, "-m", "cihub", "report"]


def test_apply_profile_shim_invokes_cli(monkeypatch, tmp_path: Path) -> None:
    from scripts import apply_profile

    profile = tmp_path / "profile.yaml"
    target = tmp_path / "target.yaml"

    calls: dict[str, Any] = {}

    def fake_call(cmd: list[str]) -> int:
        calls["cmd"] = cmd
        return 0

    monkeypatch.setattr(
        sys,
        "argv",
        ["apply_profile.py", str(profile), str(target), "--output", str(tmp_path / "out.yaml")],
    )
    monkeypatch.setattr("subprocess.call", fake_call)

    assert apply_profile.main() == 0
    assert calls["cmd"][:4] == [sys.executable, "-m", "cihub", "config"]


def test_aggregate_reports_shim_invokes_cli(monkeypatch, tmp_path: Path) -> None:
    from scripts import aggregate_reports

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    output_path = tmp_path / "dashboard.html"

    calls: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool = False) -> mock.Mock:
        calls["cmd"] = cmd
        return mock.Mock(returncode=0)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aggregate_reports.py",
            "--reports-dir",
            str(reports_dir),
            "--output",
            str(output_path),
            "--format",
            "html",
        ],
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    assert aggregate_reports.main() == 0
    assert calls["cmd"][:4] == [sys.executable, "-m", "cihub", "report"]


def test_verify_matrix_keys_shim_invokes_cli(monkeypatch) -> None:
    from scripts import verify_hub_matrix_keys

    calls: dict[str, Any] = {}

    def fake_call(cmd: list[str]) -> int:
        calls["cmd"] = cmd
        return 0

    monkeypatch.setattr("subprocess.call", fake_call)
    assert verify_hub_matrix_keys.main() == 0
    assert calls["cmd"] == [sys.executable, "-m", "cihub", "hub-ci", "verify-matrix-keys"]


def test_check_quarantine_imports_shim_invokes_cli(monkeypatch) -> None:
    from scripts import check_quarantine_imports

    calls: dict[str, Any] = {}

    def fake_call(cmd: list[str]) -> int:
        calls["cmd"] = cmd
        return 0

    monkeypatch.setattr("subprocess.call", fake_call)
    assert check_quarantine_imports.main() == 0
    assert calls["cmd"] == [sys.executable, "-m", "cihub", "hub-ci", "quarantine-check"]


def test_correlation_shim_imports() -> None:
    import scripts.correlation as correlation

    assert hasattr(correlation, "generate_correlation_id")


def test_apply_profile_load_yaml(tmp_path: Path) -> None:
    from scripts.apply_profile import load_yaml

    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert load_yaml(empty) == {}

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("- item\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_yaml(invalid)
