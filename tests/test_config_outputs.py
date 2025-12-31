"""Tests for cihub.commands.config_outputs module."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from cihub.commands.config_outputs import (
    _bool_str,
    _get_int,
    _get_str,
    _get_value,
    _tool_enabled,
    _tool_entry,
    _tool_int,
    cmd_config_outputs,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


class TestGetValue:
    """Tests for _get_value helper."""

    def test_returns_default_for_empty_dict(self) -> None:
        assert _get_value({}, ["a", "b"], "default") == "default"

    def test_returns_value_at_path(self) -> None:
        data = {"a": {"b": {"c": "found"}}}
        assert _get_value(data, ["a", "b", "c"], "default") == "found"

    def test_returns_default_when_path_not_found(self) -> None:
        data = {"a": {"b": "value"}}
        assert _get_value(data, ["a", "c"], "default") == "default"

    def test_returns_default_when_cursor_is_not_dict(self) -> None:
        data = {"a": "not_a_dict"}
        assert _get_value(data, ["a", "b"], "default") == "default"

    def test_returns_default_for_none_value(self) -> None:
        data: dict[str, Any] = {"a": None}
        assert _get_value(data, ["a"], "default") == "default"

    def test_returns_zero_if_actual_value(self) -> None:
        data = {"a": 0}
        assert _get_value(data, ["a"], 999) == 0


class TestGetStr:
    """Tests for _get_str helper."""

    def test_returns_string_value(self) -> None:
        data = {"level1": {"level2": "mystring"}}
        assert _get_str(data, ["level1", "level2"], "default") == "mystring"

    def test_converts_int_to_str(self) -> None:
        data = {"version": 123}
        assert _get_str(data, ["version"], "0") == "123"

    def test_returns_default_when_not_found(self) -> None:
        assert _get_str({}, ["missing"], "fallback") == "fallback"


class TestGetInt:
    """Tests for _get_int helper."""

    def test_returns_int_value(self) -> None:
        data = {"threshold": 85}
        assert _get_int(data, ["threshold"], 70) == 85

    def test_converts_str_to_int(self) -> None:
        data = {"threshold": "90"}
        assert _get_int(data, ["threshold"], 70) == 90

    def test_returns_default_for_non_numeric(self) -> None:
        data = {"threshold": "not_a_number"}
        assert _get_int(data, ["threshold"], 70) == 70

    def test_returns_default_when_missing(self) -> None:
        assert _get_int({}, ["missing"], 50) == 50

    def test_returns_default_for_none(self) -> None:
        data: dict[str, Any] = {"threshold": None}
        assert _get_int(data, ["threshold"], 42) == 42


class TestBoolStr:
    """Tests for _bool_str helper."""

    def test_returns_true_for_true(self) -> None:
        assert _bool_str(True) == "true"

    def test_returns_false_for_false(self) -> None:
        assert _bool_str(False) == "false"


class TestToolEntry:
    """Tests for _tool_entry helper."""

    def test_returns_tool_config(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True, "min_coverage": 80}}}}
        result = _tool_entry(config, "python", "pytest")
        assert result == {"enabled": True, "min_coverage": 80}

    def test_returns_empty_dict_for_missing_language(self) -> None:
        config: dict[str, Any] = {}
        assert _tool_entry(config, "python", "pytest") == {}

    def test_returns_empty_dict_for_missing_tools(self) -> None:
        config = {"python": {}}
        assert _tool_entry(config, "python", "pytest") == {}

    def test_returns_empty_dict_for_non_dict_tools(self) -> None:
        config = {"python": {"tools": "not_a_dict"}}
        assert _tool_entry(config, "python", "pytest") == {}

    def test_returns_empty_dict_for_missing_tool(self) -> None:
        config = {"python": {"tools": {"ruff": True}}}
        result = _tool_entry(config, "python", "pytest")
        assert result == {}


class TestToolEnabled:
    """Tests for _tool_enabled helper."""

    def test_returns_true_for_bool_true_entry(self) -> None:
        config = {"python": {"tools": {"ruff": True}}}
        assert _tool_enabled(config, "python", "ruff", False) is True

    def test_returns_false_for_bool_false_entry(self) -> None:
        config = {"python": {"tools": {"ruff": False}}}
        assert _tool_enabled(config, "python", "ruff", True) is False

    def test_returns_enabled_from_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_enabled(config, "python", "pytest", False) is True

    def test_returns_default_when_enabled_not_bool(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": "yes"}}}}
        assert _tool_enabled(config, "python", "pytest", True) is True

    def test_returns_default_for_missing_tool(self) -> None:
        config = {"python": {"tools": {}}}
        assert _tool_enabled(config, "python", "missing", True) is True


class TestToolInt:
    """Tests for _tool_int helper."""

    def test_returns_int_from_tool_config(self) -> None:
        config = {"python": {"tools": {"pytest": {"min_coverage": 85}}}}
        assert _tool_int(config, "python", "pytest", "min_coverage", 70) == 85

    def test_returns_default_for_non_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        assert _tool_int(config, "python", "pytest", "min_coverage", 70) == 70

    def test_returns_default_for_missing_key(self) -> None:
        config = {"python": {"tools": {"pytest": {}}}}
        assert _tool_int(config, "python", "pytest", "min_coverage", 70) == 70

    def test_converts_string_to_int(self) -> None:
        config = {"python": {"tools": {"pytest": {"min_coverage": "80"}}}}
        assert _tool_int(config, "python", "pytest", "min_coverage", 70) == 80

    def test_returns_default_for_non_numeric_string(self) -> None:
        config = {"python": {"tools": {"pytest": {"min_coverage": "high"}}}}
        assert _tool_int(config, "python", "pytest", "min_coverage", 70) == 70


class TestCmdConfigOutputs:
    """Tests for cmd_config_outputs command."""

    def test_loads_config_and_returns_outputs_json_mode(self, tmp_path: Path) -> None:
        """Test JSON mode returns outputs dict."""
        config_file = tmp_path / ".ci-hub.yml"
        config_file.write_text("language: python\n")

        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python", "python": {"version": "3.11"}}
            result = cmd_config_outputs(args)

        assert result.exit_code == EXIT_SUCCESS
        assert result.data is not None
        assert result.data["outputs"]["language"] == "python"
        assert result.data["outputs"]["python_version"] == "3.11"

    def test_outputs_to_stdout_when_no_github_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test outputs go to stdout."""
        args = argparse.Namespace(repo=str(tmp_path), json=False, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_config_outputs(args)

        assert result == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "language=python" in captured.out

    def test_writes_to_github_output_file(self, tmp_path: Path) -> None:
        """Test writes to GITHUB_OUTPUT when flag set."""
        output_file = tmp_path / "github_output.txt"
        args = argparse.Namespace(repo=str(tmp_path), json=False, workdir=None, github_output=True)

        with (
            patch("cihub.commands.config_outputs.load_ci_config") as mock_load,
            patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}),
        ):
            mock_load.return_value = {"language": "java"}
            result = cmd_config_outputs(args)

        assert result == EXIT_SUCCESS
        content = output_file.read_text()
        assert "language=java" in content

    def test_uses_workdir_from_args(self, tmp_path: Path) -> None:
        """Test workdir from args takes precedence."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir="custom/path", github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["workdir"] == "custom/path"

    def test_uses_workdir_from_config(self, tmp_path: Path) -> None:
        """Test workdir from config when not in args."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python", "workdir": "src/app"}
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["workdir"] == "src/app"

    def test_falls_back_to_repo_subdir(self, tmp_path: Path) -> None:
        """Test falls back to repo.subdir when workdir missing."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python", "repo": {"subdir": "backend"}}
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["workdir"] == "backend"

    def test_defaults_workdir_to_dot(self, tmp_path: Path) -> None:
        """Test workdir defaults to '.' when nothing specified."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "python"}
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["workdir"] == "."

    def test_extracts_python_tool_toggles(self, tmp_path: Path) -> None:
        """Test Python tool toggles are extracted."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {
                    "tools": {
                        "pytest": True,
                        "ruff": False,
                        "bandit": {"enabled": True},
                        "mypy": {"enabled": True},
                    }
                },
            }
            result = cmd_config_outputs(args)

        outputs = result.data["outputs"]
        assert outputs["run_pytest"] == "true"
        assert outputs["run_ruff"] == "false"
        assert outputs["run_bandit"] == "true"
        assert outputs["run_mypy"] == "true"

    def test_extracts_java_tool_toggles(self, tmp_path: Path) -> None:
        """Test Java tool toggles are extracted."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "java",
                "java": {
                    "version": "17",
                    "build_tool": "gradle",
                    "tools": {
                        "jacoco": True,
                        "checkstyle": False,
                        "pitest": {"enabled": True},
                    }
                },
            }
            result = cmd_config_outputs(args)

        outputs = result.data["outputs"]
        assert outputs["language"] == "java"
        assert outputs["java_version"] == "17"
        assert outputs["build_tool"] == "gradle"
        assert outputs["run_jacoco"] == "true"
        assert outputs["run_checkstyle"] == "false"
        assert outputs["run_pitest"] == "true"

    def test_extracts_thresholds(self, tmp_path: Path) -> None:
        """Test threshold extraction."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {
                    "tools": {
                        "pytest": {"min_coverage": 85},
                        "mutmut": {"min_mutation_score": 75},
                    }
                },
            }
            result = cmd_config_outputs(args)

        outputs = result.data["outputs"]
        assert outputs["coverage_min"] == "85"
        assert outputs["mutation_score_min"] == "75"

    def test_global_thresholds_override_tool_thresholds(self, tmp_path: Path) -> None:
        """Test global thresholds override language-specific ones."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "python": {"tools": {"pytest": {"min_coverage": 60}}},
                "thresholds": {"coverage_min": 90},
            }
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["coverage_min"] == "90"

    def test_java_language_uses_java_thresholds(self, tmp_path: Path) -> None:
        """Test Java language uses Java-specific thresholds."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "java",
                "java": {
                    "tools": {
                        "jacoco": {"min_coverage": 80},
                        "pitest": {"min_mutation_score": 65},
                    }
                },
            }
            result = cmd_config_outputs(args)

        outputs = result.data["outputs"]
        assert outputs["coverage_min"] == "80"
        assert outputs["mutation_score_min"] == "65"

    def test_returns_failure_on_config_load_error_json_mode(self, tmp_path: Path) -> None:
        """Test returns failure when config fails to load (JSON mode)."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.side_effect = Exception("Config not found")
            result = cmd_config_outputs(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Failed to load config" in result.summary
        assert len(result.problems) == 1

    def test_returns_failure_on_config_load_error_text_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test returns failure when config fails to load (text mode)."""
        args = argparse.Namespace(repo=str(tmp_path), json=False, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.side_effect = Exception("Config not found")
            result = cmd_config_outputs(args)

        assert result == EXIT_FAILURE
        captured = capsys.readouterr()
        assert "Failed to load config" in captured.err

    def test_uses_language_from_repo_section(self, tmp_path: Path) -> None:
        """Test language falls back to repo.language."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {"repo": {"language": "java"}}
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["language"] == "java"

    def test_nvd_api_key_toggle(self, tmp_path: Path) -> None:
        """Test NVD API key toggle logic."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        # When owasp enabled and use_nvd_api_key not explicitly false
        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "java",
                "java": {"tools": {"owasp": {"enabled": True}}},
            }
            result = cmd_config_outputs(args)
        assert result.data["outputs"]["use_nvd_api_key"] == "true"

        # When owasp disabled
        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "java",
                "java": {"tools": {"owasp": False}},
            }
            result = cmd_config_outputs(args)
        assert result.data["outputs"]["use_nvd_api_key"] == "false"

    def test_vuln_thresholds(self, tmp_path: Path) -> None:
        """Test max_critical_vulns and max_high_vulns extraction."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "thresholds": {"max_critical_vulns": 5, "max_high_vulns": 10},
            }
            result = cmd_config_outputs(args)

        outputs = result.data["outputs"]
        assert outputs["max_critical_vulns"] == "5"
        assert outputs["max_high_vulns"] == "10"

    def test_retention_days(self, tmp_path: Path) -> None:
        """Test retention_days extraction."""
        args = argparse.Namespace(repo=str(tmp_path), json=True, workdir=None, github_output=False)

        with patch("cihub.commands.config_outputs.load_ci_config") as mock_load:
            mock_load.return_value = {
                "language": "python",
                "reports": {"retention_days": 14},
            }
            result = cmd_config_outputs(args)

        assert result.data["outputs"]["retention_days"] == "14"
