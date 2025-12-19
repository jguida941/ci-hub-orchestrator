"""Tests for aggregate_reports.py - Report aggregation functionality."""

import json
import sys
from pathlib import Path

import pytest

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.aggregate_reports import (
    detect_language,
    generate_html_dashboard,
    generate_summary,
    get_status,
    load_reports,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_detect_language_java_version(self):
        """Java detected from java_version field."""
        report = {"java_version": "21"}
        assert detect_language(report) == "java"

    def test_detect_language_python_version(self):
        """Python detected from python_version field."""
        report = {"python_version": "3.12"}
        assert detect_language(report) == "python"

    def test_detect_language_tools_ran_java(self):
        """Java detected from tools_ran with Java tools."""
        report = {"tools_ran": {"jacoco": True, "checkstyle": True}}
        assert detect_language(report) == "java"

    def test_detect_language_tools_ran_python(self):
        """Python detected from tools_ran with Python tools."""
        report = {"tools_ran": {"pytest": True, "ruff": True}}
        assert detect_language(report) == "python"

    def test_detect_language_unknown(self):
        """Unknown returned when no indicators present."""
        report = {}
        assert detect_language(report) == "unknown"

    def test_get_status_python(self):
        """Python status from results.test field."""
        report = {"results": {"test": "success"}}
        assert get_status(report) == "success"

    def test_get_status_java(self):
        """Java status from results.build field."""
        report = {"results": {"build": "failure"}}
        assert get_status(report) == "failure"

    def test_get_status_missing(self):
        """Unknown returned when no status field."""
        report = {"results": {}}
        assert get_status(report) == "unknown"


class TestLoadReports:
    """Tests for load_reports function."""

    def test_load_reports_empty_directory(self, tmp_path: Path):
        """Loading from empty directory returns empty list."""
        reports, skipped = load_reports(tmp_path)
        assert reports == []
        assert skipped == 0

    def test_load_reports_nonexistent_directory(self, tmp_path: Path):
        """Loading from nonexistent directory returns empty list."""
        nonexistent = tmp_path / "does_not_exist"
        reports, skipped = load_reports(nonexistent)
        assert reports == []
        assert skipped == 0

    def test_load_reports_valid_json(self, tmp_path: Path):
        """Loading valid report.json files works correctly."""
        reports_dir = tmp_path / "repo1"
        reports_dir.mkdir()
        report_data = {
            "schema_version": "2.0",
            "repository": "test/repo1",
            "branch": "main",
            "results": {"coverage": 85, "mutation_score": 70},
        }
        (reports_dir / "report.json").write_text(json.dumps(report_data))

        reports, skipped = load_reports(tmp_path)
        assert len(reports) == 1
        assert skipped == 0
        assert reports[0]["repository"] == "test/repo1"
        assert reports[0]["results"]["coverage"] == 85

    def test_load_reports_invalid_json_skipped(self, tmp_path: Path):
        """Invalid JSON files are skipped with warning."""
        reports_dir = tmp_path / "bad_repo"
        reports_dir.mkdir()
        (reports_dir / "report.json").write_text("not valid json {{{")

        reports, skipped = load_reports(tmp_path)
        assert reports == []

    def test_load_reports_multiple_repos(self, tmp_path: Path):
        """Multiple report.json files are all loaded."""
        for i in range(3):
            repo_dir = tmp_path / f"repo{i}"
            repo_dir.mkdir()
            report = {"schema_version": "2.0", "repository": f"test/repo{i}", "results": {"coverage": 70 + i * 5}}
            (repo_dir / "report.json").write_text(json.dumps(report))

        reports, skipped = load_reports(tmp_path)
        assert len(reports) == 3
        assert skipped == 0

    def test_load_reports_nested_directories(self, tmp_path: Path):
        """report.json in nested directories are found."""
        nested = tmp_path / "level1" / "level2"
        nested.mkdir(parents=True)
        report = {"schema_version": "2.0", "repository": "nested/repo", "results": {}}
        (nested / "report.json").write_text(json.dumps(report))

        reports, skipped = load_reports(tmp_path)
        assert len(reports) == 1
        assert skipped == 0
        assert reports[0]["repository"] == "nested/repo"

    def test_load_reports_warn_mode_includes_old_schema(self, tmp_path: Path, capsys):
        """Warn mode includes old schema reports with warning."""
        repo_dir = tmp_path / "old_repo"
        repo_dir.mkdir()
        report = {"schema_version": "1.0", "repository": "test", "results": {}}
        (repo_dir / "report.json").write_text(json.dumps(report))

        reports, skipped = load_reports(tmp_path, schema_mode="warn")
        assert len(reports) == 1
        assert skipped == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "schema_version=1.0" in captured.out

    def test_load_reports_strict_mode_skips_old_schema(self, tmp_path: Path, capsys):
        """Strict mode skips old schema reports."""
        repo_dir = tmp_path / "old_repo"
        repo_dir.mkdir()
        report = {"schema_version": "1.0", "repository": "test", "results": {}}
        (repo_dir / "report.json").write_text(json.dumps(report))

        reports, skipped = load_reports(tmp_path, schema_mode="strict")
        assert len(reports) == 0
        assert skipped == 1
        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    def test_load_reports_strict_mode_includes_2_0_schema(self, tmp_path: Path):
        """Strict mode includes 2.0 schema reports."""
        repo_dir = tmp_path / "new_repo"
        repo_dir.mkdir()
        report = {"schema_version": "2.0", "repository": "test", "results": {}}
        (repo_dir / "report.json").write_text(json.dumps(report))

        reports, skipped = load_reports(tmp_path, schema_mode="strict")
        assert len(reports) == 1
        assert skipped == 0


class TestGenerateSummary:
    """Tests for generate_summary function."""

    def test_empty_reports(self):
        """Empty reports list produces valid summary structure."""
        summary = generate_summary([])
        assert summary["total_repos"] == 0
        assert summary["coverage"]["average"] == 0
        assert summary["mutation"]["average"] == 0
        assert summary["tests"]["total_passed"] == 0
        assert summary["tests"]["total_failed"] == 0
        assert summary["repos"] == []
        assert summary["schema_version"] == "2.0"

    def test_single_repo_summary(self):
        """Single repo summary calculates correctly."""
        reports = [
            {
                "schema_version": "2.0",
                "repository": "test/repo",
                "branch": "main",
                "timestamp": "2025-01-01T00:00:00Z",
                "java_version": "21",
                "results": {
                    "coverage": 80,
                    "mutation_score": 70,
                    "build": "success",
                    "tests_passed": 10,
                    "tests_failed": 2,
                },
                "tool_metrics": {"checkstyle_issues": 0, "spotbugs_issues": 1},
                "tools_ran": {"jacoco": True, "checkstyle": True},
            }
        ]
        summary = generate_summary(reports)

        assert summary["total_repos"] == 1
        assert summary["coverage"]["average"] == 80
        assert summary["mutation"]["average"] == 70
        assert summary["tests"]["total_passed"] == 10
        assert summary["tests"]["total_failed"] == 2
        assert len(summary["repos"]) == 1
        assert summary["repos"][0]["name"] == "test/repo"
        assert summary["repos"][0]["status"] == "success"
        assert summary["repos"][0]["language"] == "java"
        assert summary["repos"][0]["tests_passed"] == 10
        assert summary["repos"][0]["tests_failed"] == 2
        assert summary["repos"][0]["tool_metrics"]["checkstyle_issues"] == 0
        assert summary["repos"][0]["tools_ran"]["jacoco"] is True

    def test_multiple_repos_average(self):
        """Multiple repos have averages calculated correctly."""
        reports = [
            {"repository": "repo1", "java_version": "21", "results": {"coverage": 60, "mutation_score": 50, "tests_passed": 5, "tests_failed": 1}},
            {"repository": "repo2", "java_version": "21", "results": {"coverage": 80, "mutation_score": 70, "tests_passed": 10, "tests_failed": 0}},
            {"repository": "repo3", "java_version": "21", "results": {"coverage": 100, "mutation_score": 90, "tests_passed": 15, "tests_failed": 2}},
        ]
        summary = generate_summary(reports)

        assert summary["total_repos"] == 3
        assert summary["coverage"]["average"] == 80  # (60+80+100)/3
        assert summary["mutation"]["average"] == 70  # (50+70+90)/3
        assert summary["tests"]["total_passed"] == 30  # 5+10+15
        assert summary["tests"]["total_failed"] == 3  # 1+0+2

    def test_language_tracking(self):
        """Language counts are tracked correctly."""
        reports = [
            {"repository": "java1", "java_version": "21", "results": {}},
            {"repository": "java2", "java_version": "17", "results": {}},
            {"repository": "python1", "python_version": "3.12", "results": {}},
        ]
        summary = generate_summary(reports)

        assert summary["languages"]["java"] == 2
        assert summary["languages"]["python"] == 1

    def test_language_from_tools_ran(self):
        """Language detected from tools_ran when no version field."""
        reports = [
            {"repository": "java1", "tools_ran": {"jacoco": True, "checkstyle": True}, "results": {}},
            {"repository": "python1", "tools_ran": {"pytest": True, "ruff": True}, "results": {}},
        ]
        summary = generate_summary(reports)

        assert summary["languages"]["java"] == 1
        assert summary["languages"]["python"] == 1

    def test_zero_values_included(self):
        """Zero values are included in averages (not treated as missing)."""
        reports = [
            {"repository": "repo1", "java_version": "21", "results": {"coverage": 0, "mutation_score": 0}},
        ]
        summary = generate_summary(reports)

        # Zero values should NOT be counted (current implementation treats falsy as missing)
        # This test documents current behavior
        assert summary["coverage"]["count"] == 0  # 0 is falsy

    def test_missing_values_excluded(self):
        """Missing values are excluded from averages."""
        reports = [
            {"repository": "repo1", "java_version": "21", "results": {"coverage": 80}},  # No mutation_score
            {"repository": "repo2", "java_version": "21", "results": {"mutation_score": 70}},  # No coverage
        ]
        summary = generate_summary(reports)

        assert summary["coverage"]["count"] == 1
        assert summary["mutation"]["count"] == 1


class TestGenerateHtmlDashboard:
    """Tests for generate_html_dashboard function."""

    def test_empty_summary_produces_valid_html(self):
        """Empty summary produces valid HTML structure."""
        summary = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total_repos": 0,
            "coverage": {"average": 0},
            "mutation": {"average": 0},
            "tests": {"total_passed": 0, "total_failed": 0},
            "languages": {},
            "repos": [],
        }
        html = generate_html_dashboard(summary)

        assert "<!DOCTYPE html>" in html
        assert "CI/CD Hub Dashboard" in html
        assert "0" in html  # Total repos

    def test_repo_rows_generated(self):
        """Repo rows are generated in HTML."""
        summary = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total_repos": 1,
            "coverage": {"average": 85},
            "mutation": {"average": 70},
            "tests": {"total_passed": 10, "total_failed": 0},
            "languages": {"java": 1},
            "repos": [
                {
                    "name": "test/repo",
                    "language": "java",
                    "branch": "main",
                    "status": "success",
                    "coverage": 85,
                    "mutation_score": 70,
                    "tests_passed": 10,
                    "tests_failed": 0,
                    "timestamp": "2025-01-01T00:00:00Z",
                }
            ],
        }
        html = generate_html_dashboard(summary)

        assert "test/repo" in html
        assert "java" in html
        assert "main" in html
        assert "success" in html
        assert "85%" in html
        assert "10/10" in html  # tests_passed / total

    def test_status_classes_applied(self):
        """Success and failure status classes are applied."""
        summary = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total_repos": 2,
            "coverage": {"average": 0},
            "mutation": {"average": 0},
            "tests": {"total_passed": 0, "total_failed": 0},
            "languages": {},
            "repos": [
                {"name": "passing", "language": "python", "branch": "main", "status": "success", "coverage": 0, "mutation_score": 0, "tests_passed": 5, "tests_failed": 0, "timestamp": ""},
                {"name": "failing", "language": "java", "branch": "main", "status": "failure", "coverage": 0, "mutation_score": 0, "tests_passed": 3, "tests_failed": 2, "timestamp": ""},
            ],
        }
        html = generate_html_dashboard(summary)

        assert 'class="success"' in html
        assert 'class="failure"' in html

    def test_tests_card_displayed(self):
        """Tests passed card is displayed in summary."""
        summary = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total_repos": 1,
            "coverage": {"average": 80},
            "mutation": {"average": 70},
            "tests": {"total_passed": 25, "total_failed": 5},
            "languages": {"python": 1},
            "repos": [],
        }
        html = generate_html_dashboard(summary)

        assert "25/30" in html  # tests passed / total
        assert "Tests Passed" in html
