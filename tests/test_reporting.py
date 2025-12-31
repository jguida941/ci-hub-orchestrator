"""Tests for cihub.reporting module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cihub.reporting import (
    build_environment_table,
    build_python_metrics,
    build_java_metrics,
    build_thresholds_table,
    build_tools_table,
    detect_language,
    fmt_bool,
    fmt_percent,
    fmt_retention,
    fmt_value,
    fmt_workdir,
    format_number,
    load_report,
    render_bar,
    render_summary_from_path,
)


class TestLoadReport:
    """Tests for load_report function."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        report = {"language": "python", "results": {"coverage": 80}}
        path = tmp_path / "report.json"
        path.write_text(json.dumps(report))

        result = load_report(path)

        assert result["language"] == "python"
        assert result["results"]["coverage"] == 80

    def test_raises_for_non_object(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        path.write_text("[1, 2, 3]")

        with pytest.raises(ValueError, match="must be a JSON object"):
            load_report(path)


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_detects_java(self) -> None:
        report = {"java_version": "21"}
        assert detect_language(report) == "java"

    def test_detects_python(self) -> None:
        report = {"python_version": "3.12"}
        assert detect_language(report) == "python"

    def test_returns_unknown_for_neither(self) -> None:
        report = {}
        assert detect_language(report) == "unknown"


class TestFormatters:
    """Tests for formatting helper functions."""

    def test_fmt_bool_true(self) -> None:
        assert fmt_bool(True) == "true"
        assert fmt_bool(1) == "true"
        assert fmt_bool("yes") == "true"

    def test_fmt_bool_false(self) -> None:
        assert fmt_bool(False) == "false"
        assert fmt_bool(0) == "false"
        assert fmt_bool("") == "false"
        assert fmt_bool(None) == "false"

    def test_fmt_value(self) -> None:
        assert fmt_value(None) == "-"
        assert fmt_value("") == "-"
        assert fmt_value("hello") == "hello"
        assert fmt_value(42) == "42"

    def test_fmt_percent(self) -> None:
        assert fmt_percent(None) == "-"
        assert fmt_percent("") == "-"
        assert fmt_percent(85) == "85%"

    def test_fmt_retention(self) -> None:
        assert fmt_retention(None) == "-"
        assert fmt_retention("") == "-"
        assert fmt_retention(30) == "30 days"

    def test_fmt_workdir(self) -> None:
        assert fmt_workdir(None) == "-"
        assert fmt_workdir("") == "-"
        assert fmt_workdir(".") == "`.` (repo root)"
        assert fmt_workdir("src/app") == "`src/app`"

    def test_format_number(self) -> None:
        assert format_number(42) == 42
        assert format_number(3.7) == 3
        assert format_number("100") == 100
        assert format_number("  50  ") == 50
        assert format_number("abc") == 0
        assert format_number(None) == 0


class TestRenderBar:
    """Tests for render_bar function."""

    def test_renders_none_as_dash(self) -> None:
        assert render_bar(None) == "-"

    def test_renders_zero_percent(self) -> None:
        result = render_bar(0)
        assert "0%" in result

    def test_renders_100_percent(self) -> None:
        result = render_bar(100)
        assert "100%" in result

    def test_clamps_negative_values(self) -> None:
        result = render_bar(-10)
        assert "0%" in result

    def test_clamps_over_100(self) -> None:
        result = render_bar(150)
        assert "100%" in result


class TestBuildToolsTable:
    """Tests for build_tools_table function."""

    def test_builds_python_tools_table(self) -> None:
        report = {
            "tools_configured": {"pytest": True, "ruff": True, "bandit": False},
            "tools_ran": {"pytest": True, "ruff": True},
            "tools_success": {"pytest": True, "ruff": False},
        }
        lines = list(build_tools_table(report, "python"))

        assert "## Tools Enabled" in lines[0]
        assert "| pytest |" in "".join(lines)
        assert "| Ruff |" in "".join(lines)

    def test_builds_java_tools_table(self) -> None:
        report = {
            "tools_configured": {"jacoco": True, "checkstyle": True},
            "tools_ran": {"jacoco": True},
            "tools_success": {"jacoco": True},
            "environment": {"build_tool": "maven"},
        }
        lines = list(build_tools_table(report, "java"))

        assert "## Tools Enabled" in lines[0]
        assert "maven" in "".join(lines)
        assert "| JaCoCo Coverage |" in "".join(lines)


class TestBuildThresholdsTable:
    """Tests for build_thresholds_table function."""

    def test_builds_python_thresholds(self) -> None:
        report = {
            "thresholds": {
                "coverage_min": 70,
                "mutation_score_min": 60,
                "max_ruff_errors": 0,
            }
        }
        lines = list(build_thresholds_table(report, "python"))

        assert "## Thresholds" in lines[0]
        assert "| Min Coverage | 70% |" in "".join(lines)

    def test_builds_java_thresholds(self) -> None:
        report = {
            "thresholds": {
                "coverage_min": 80,
                "owasp_cvss_fail": 7,
            }
        }
        lines = list(build_thresholds_table(report, "java"))

        assert "| OWASP CVSS Fail | 7 |" in "".join(lines)


class TestBuildEnvironmentTable:
    """Tests for build_environment_table function."""

    def test_builds_environment_table(self) -> None:
        report = {
            "java_version": "21",
            "repository": "owner/repo",
            "branch": "main",
            "run_number": "42",
            "environment": {
                "build_tool": "gradle",
                "workdir": "backend",
                "retention_days": 14,
            },
        }
        lines = list(build_environment_table(report))

        table_text = "".join(lines)
        assert "## Environment" in lines[0]
        assert "| Java Version | 21 |" in table_text
        assert "| Repository | owner/repo |" in table_text
        assert "| Run Number | #42 |" in table_text
        assert "| Build Tool | gradle |" in table_text
        assert "| Artifact Retention | 14 days |" in table_text


class TestBuildPythonMetrics:
    """Tests for build_python_metrics function."""

    def test_builds_python_metrics_table(self) -> None:
        report = {
            "results": {
                "tests_passed": 100,
                "tests_failed": 2,
                "tests_skipped": 5,
                "tests_runtime_seconds": 1.234,
                "coverage": 85,
                "coverage_lines_covered": 850,
                "coverage_lines_total": 1000,
                "mutation_score": 75,
                "mutation_killed": 150,
                "mutation_survived": 50,
            },
            "tools_ran": {
                "pytest": True,
                "mutmut": True,
                "ruff": True,
                "bandit": True,
            },
            "tool_metrics": {
                "ruff_errors": 3,
                "bandit_high": 1,
                "bandit_medium": 2,
                "bandit_low": 5,
            },
        }
        lines = list(build_python_metrics(report))
        table_text = "".join(lines)

        assert "## QA Metrics (Python)" in lines[0]
        assert "107 executed" in table_text  # 100 + 2 + 5
        assert "Runtime: 1.234s" in table_text
        assert "850 / 1000 lines covered" in table_text
        assert "150 killed, 50 survived" in table_text

    def test_handles_missing_tools(self) -> None:
        report = {
            "results": {},
            "tools_ran": {},
            "tool_metrics": {},
        }
        lines = list(build_python_metrics(report))
        table_text = "".join(lines)

        # Should show dashes for unran tools
        assert "| Line Coverage (pytest) | - |" in table_text


class TestBuildJavaMetrics:
    """Tests for build_java_metrics function."""

    def test_builds_java_metrics_table(self) -> None:
        report = {
            "results": {
                "tests_passed": 50,
                "tests_failed": 1,
                "tests_skipped": 2,
                "tests_runtime_seconds": 5.5,
                "coverage": 90,
                "coverage_lines_covered": 900,
                "coverage_lines_total": 1000,
                "mutation_score": 80,
                "mutation_killed": 80,
                "mutation_survived": 20,
            },
            "tools_ran": {
                "jacoco": True,
                "pitest": True,
                "owasp": True,
                "spotbugs": True,
            },
            "tool_metrics": {
                "owasp_critical": 0,
                "owasp_high": 2,
                "owasp_medium": 5,
                "spotbugs_issues": 3,
                "checkstyle_issues": 10,
            },
        }
        lines = list(build_java_metrics(report))
        table_text = "".join(lines)

        assert "## QA Metrics (Java)" in lines[0]
        assert "53 executed" in table_text
        assert "900 / 1000 lines covered" in table_text
        assert "0 crit, 2 high, 5 med" in table_text


class TestRenderSummaryFromPath:
    """Tests for render_summary_from_path function."""

    def test_renders_python_summary(self, tmp_path: Path) -> None:
        report = {
            "python_version": "3.12",
            "repository": "myorg/myrepo",
            "branch": "main",
            "results": {
                "tests_passed": 100,
                "coverage": 85,
            },
            "tools_configured": {"pytest": True, "ruff": True},
            "tools_ran": {"pytest": True, "ruff": True},
            "tools_success": {"pytest": True, "ruff": True},
            "thresholds": {"coverage_min": 70},
            "tool_metrics": {},
        }
        path = tmp_path / "report.json"
        path.write_text(json.dumps(report))

        result = render_summary_from_path(path)

        assert "## Environment" in result
        assert "## Tools Enabled" in result
        assert "## QA Metrics (Python)" in result
        assert "## Thresholds" in result

    def test_renders_java_summary(self, tmp_path: Path) -> None:
        report = {
            "java_version": "21",
            "repository": "myorg/myrepo",
            "results": {},
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
            "thresholds": {},
            "tool_metrics": {},
        }
        path = tmp_path / "report.json"
        path.write_text(json.dumps(report))

        result = render_summary_from_path(path)

        assert "## QA Metrics (Java)" in result

    def test_handles_unknown_language(self, tmp_path: Path) -> None:
        report = {
            "repository": "test/repo",
            "results": {},
            "tools_configured": {},
            "tools_ran": {},
            "tools_success": {},
            "thresholds": {},
        }
        path = tmp_path / "report.json"
        path.write_text(json.dumps(report))

        result = render_summary_from_path(path)

        # Should still render environment table at minimum
        assert "## Environment" in result
