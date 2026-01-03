"""Snapshot tests for CLI output.

Uses syrupy to capture CLI output and detect unintended changes.
Run with: pytest tests/test_cli_snapshots.py --snapshot-update to update snapshots.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion

from cihub.cli import main


class TestHelpSnapshots:
    """Snapshot tests for help output - catches unintended CLI changes."""

    def test_main_help_snapshot(self, capsys, snapshot: SnapshotAssertion) -> None:
        """Main help output should be stable."""
        with pytest.raises(SystemExit):
            main(["--help"])
        out = capsys.readouterr().out
        # Snapshot the structure, not exact whitespace
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        assert lines == snapshot

    def test_detect_help_snapshot(self, capsys, snapshot: SnapshotAssertion) -> None:
        """detect --help output should be stable."""
        with pytest.raises(SystemExit):
            main(["detect", "--help"])
        out = capsys.readouterr().out
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        assert lines == snapshot

    def test_init_help_snapshot(self, capsys, snapshot: SnapshotAssertion) -> None:
        """init --help output should be stable."""
        with pytest.raises(SystemExit):
            main(["init", "--help"])
        out = capsys.readouterr().out
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        assert lines == snapshot

    def test_report_help_snapshot(self, capsys, snapshot: SnapshotAssertion) -> None:
        """report --help output should be stable."""
        with pytest.raises(SystemExit):
            main(["report", "--help"])
        out = capsys.readouterr().out
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        assert lines == snapshot


class TestJsonOutputSnapshots:
    """Snapshot tests for JSON output structure."""

    def test_detect_json_structure(self, tmp_path: Path, capsys, snapshot: SnapshotAssertion) -> None:
        """detect --json output structure should be stable."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")

        main(["detect", "--repo", str(tmp_path), "--json"])
        out = capsys.readouterr().out
        data = json.loads(out)

        # Snapshot structure keys, not values (which vary)
        structure = {
            "top_keys": sorted(data.keys()),
            "data_keys": sorted(data.get("data", {}).keys()) if "data" in data else [],
        }
        assert structure == snapshot

    def test_init_json_structure(self, tmp_path: Path, capsys, snapshot: SnapshotAssertion) -> None:
        """init --json output structure should be stable."""
        main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--dry-run",
                "--json",
            ]
        )
        out = capsys.readouterr().out
        data = json.loads(out)

        # Snapshot structure keys
        structure = {
            "top_keys": sorted(data.keys()),
            "has_artifacts": "artifacts" in data,
            "has_files_generated": "files_generated" in data,
        }
        assert structure == snapshot


class TestReportSchemaSnapshots:
    """Snapshot tests for report.json schema structure."""

    def test_report_schema_fields(self, tmp_path: Path, snapshot: SnapshotAssertion) -> None:
        """report.json required fields should be stable."""
        # Create a sample report matching schema v2.0
        report = tmp_path / "report.json"
        report.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "repository": "test/repo",
                    "branch": "main",
                    "python_version": "3.12",
                    "results": {
                        "coverage": 80,
                        "tests_passed": 10,
                        "tests_failed": 0,
                    },
                    "tool_metrics": {},
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": True},
                    "tools_success": {"pytest": True},
                }
            )
        )

        report_dict = json.loads(report.read_text())

        # Snapshot the top-level keys (schema structure)
        structure = {
            "required_keys": sorted(report_dict.keys()),
            "results_keys": sorted(report_dict.get("results", {}).keys()),
        }
        assert structure == snapshot


class TestScaffoldOutputSnapshots:
    """Snapshot tests for scaffold command output."""

    def test_scaffold_list_output(self, capsys, snapshot: SnapshotAssertion) -> None:
        """scaffold --list output should be stable."""
        main(["scaffold", "--list"])
        out = capsys.readouterr().out

        # Snapshot the available fixture types
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        assert lines == snapshot


class TestConfigOutputSnapshots:
    """Snapshot tests for config-related output."""

    def test_discover_matrix_structure(self, capsys, snapshot: SnapshotAssertion) -> None:
        """discover output structure should be stable."""
        main(["discover"])
        out = capsys.readouterr().out

        # Parse and snapshot the matrix structure
        try:
            data = json.loads(out)
            structure = {
                "is_list": isinstance(data, list),
                "sample_keys": sorted(data[0].keys()) if data and isinstance(data[0], dict) else [],
            }
        except (json.JSONDecodeError, IndexError, TypeError):
            structure = {"raw_output_lines": len(out.strip().split("\n"))}

        assert structure == snapshot


class TestErrorOutputSnapshots:
    """Snapshot tests for error messages - ensures consistent UX."""

    def test_detect_error_message(self, tmp_path: Path, capsys, snapshot: SnapshotAssertion) -> None:
        """Error messages should be user-friendly and stable."""
        main(["detect", "--repo", str(tmp_path)])
        err = capsys.readouterr().err

        # Snapshot error format (not specific path)
        error_format = {
            "starts_with_error": err.startswith("Error:"),
            "mentions_language": "language" in err.lower(),
        }
        assert error_format == snapshot

    def test_validate_json_error_structure(self, tmp_path: Path, capsys, snapshot: SnapshotAssertion) -> None:
        """JSON error output structure should be stable."""
        main(["validate", "--repo", str(tmp_path), "--json"])
        out = capsys.readouterr().out

        data = json.loads(out)
        structure = {
            "has_status": "status" in data,
            "has_exit_code": "exit_code" in data,
            "has_problems": "problems" in data,
            "status_value": data.get("status"),
        }
        assert structure == snapshot
