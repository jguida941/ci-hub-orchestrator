"""Tests for cihub.ci_runner module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cihub.ci_runner import (
    ToolResult,
    _count_pip_audit_vulns,
    _detect_mutmut_paths,
    _find_files,
    _parse_checkstyle_files,
    _parse_coverage,
    _parse_dependency_check,
    _parse_jacoco_files,
    _parse_json,
    _parse_junit,
    _parse_junit_files,
    _parse_pitest_files,
    _parse_pmd_files,
    _parse_spotbugs_files,
    run_black,
    run_isort,
    run_mypy,
    run_ruff,
)


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_to_payload(self) -> None:
        result = ToolResult(
            tool="pytest",
            ran=True,
            success=True,
            metrics={"coverage": 85},
            artifacts={"report": "/path/to/report.xml"},
        )
        payload = result.to_payload()

        assert payload["tool"] == "pytest"
        assert payload["ran"] is True
        assert payload["success"] is True
        assert payload["metrics"]["coverage"] == 85
        assert payload["artifacts"]["report"] == "/path/to/report.xml"

    def test_from_payload(self) -> None:
        data = {
            "tool": "ruff",
            "ran": True,
            "success": False,
            "metrics": {"errors": 5},
            "artifacts": {},
        }
        result = ToolResult.from_payload(data)

        assert result.tool == "ruff"
        assert result.ran is True
        assert result.success is False
        assert result.metrics["errors"] == 5

    def test_from_payload_handles_missing_fields(self) -> None:
        result = ToolResult.from_payload({})

        assert result.tool == ""
        assert result.ran is False
        assert result.success is False
        assert result.metrics == {}
        assert result.artifacts == {}

    def test_write_json(self, tmp_path: Path) -> None:
        result = ToolResult(tool="test", ran=True, success=True)
        output_path = tmp_path / "subdir" / "result.json"

        result.write_json(output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["tool"] == "test"


class TestParseJunit:
    """Tests for _parse_junit function."""

    def test_parses_single_testsuite(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <testsuite tests="10" failures="2" errors="1" skipped="1" time="1.5">
        </testsuite>"""
        path = tmp_path / "junit.xml"
        path.write_text(xml)

        result = _parse_junit(path)

        assert result["tests_passed"] == 6
        assert result["tests_failed"] == 3
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.5

    def test_parses_testsuites_container(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <testsuites>
            <testsuite tests="5" failures="1" errors="0" skipped="0" time="0.5"/>
            <testsuite tests="5" failures="0" errors="1" skipped="1" time="0.5"/>
        </testsuites>"""
        path = tmp_path / "junit.xml"
        path.write_text(xml)

        result = _parse_junit(path)

        assert result["tests_passed"] == 7
        assert result["tests_failed"] == 2
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.0

    def test_returns_zeros_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_junit(tmp_path / "missing.xml")

        assert result["tests_passed"] == 0
        assert result["tests_failed"] == 0
        assert result["tests_skipped"] == 0


class TestParseCoverage:
    """Tests for _parse_coverage function."""

    def test_parses_cobertura_format(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <coverage line-rate="0.85" lines-covered="850" lines-valid="1000">
        </coverage>"""
        path = tmp_path / "coverage.xml"
        path.write_text(xml)

        result = _parse_coverage(path)

        assert result["coverage"] == 85
        assert result["coverage_lines_covered"] == 850
        assert result["coverage_lines_total"] == 1000

    def test_handles_lines_total_alias(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <coverage line-rate="0.75" lines-covered="75" lines-total="100">
        </coverage>"""
        path = tmp_path / "coverage.xml"
        path.write_text(xml)

        result = _parse_coverage(path)
        assert result["coverage_lines_total"] == 100

    def test_returns_zeros_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_coverage(tmp_path / "missing.xml")

        assert result["coverage"] == 0
        assert result["coverage_lines_covered"] == 0


class TestParseJson:
    """Tests for _parse_json function."""

    def test_parses_dict(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text('{"key": "value"}')

        result = _parse_json(path)
        assert result == {"key": "value"}

    def test_parses_list(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text('[1, 2, 3]')

        result = _parse_json(path)
        assert result == [1, 2, 3]

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        result = _parse_json(tmp_path / "missing.json")
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not valid json")

        result = _parse_json(path)
        assert result is None

    def test_returns_none_for_primitive(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        path.write_text('"just a string"')

        result = _parse_json(path)
        assert result is None


class TestFindFiles:
    """Tests for _find_files function."""

    def test_finds_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "dir").mkdir()
        (tmp_path / "file1.xml").write_text("")
        (tmp_path / "dir" / "file2.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml", "**/*.xml"])

        assert len(result) == 2

    def test_deduplicates_results(self, tmp_path: Path) -> None:
        (tmp_path / "test.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml", "test.xml"])

        assert len(result) == 1

    def test_returns_sorted_paths(self, tmp_path: Path) -> None:
        (tmp_path / "z.xml").write_text("")
        (tmp_path / "a.xml").write_text("")

        result = _find_files(tmp_path, ["*.xml"])

        assert str(result[0]).endswith("a.xml")


class TestParseJunitFiles:
    """Tests for _parse_junit_files function."""

    def test_aggregates_multiple_files(self, tmp_path: Path) -> None:
        xml1 = '<testsuite tests="5" failures="1" errors="0" skipped="0" time="1.0"/>'
        xml2 = '<testsuite tests="3" failures="0" errors="0" skipped="1" time="0.5"/>'
        (tmp_path / "test1.xml").write_text(xml1)
        (tmp_path / "test2.xml").write_text(xml2)

        paths = [tmp_path / "test1.xml", tmp_path / "test2.xml"]
        result = _parse_junit_files(paths)

        assert result["tests_passed"] == 6
        assert result["tests_failed"] == 1
        assert result["tests_skipped"] == 1
        assert result["tests_runtime_seconds"] == 1.5


class TestParseJacocoFiles:
    """Tests for _parse_jacoco_files function."""

    def test_parses_jacoco_xml(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <report>
            <counter type="LINE" covered="80" missed="20"/>
            <counter type="BRANCH" covered="10" missed="5"/>
        </report>"""
        path = tmp_path / "jacoco.xml"
        path.write_text(xml)

        result = _parse_jacoco_files([path])

        assert result["coverage"] == 80
        assert result["coverage_lines_covered"] == 80
        assert result["coverage_lines_total"] == 100

    def test_handles_parse_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.xml"
        path.write_text("not valid xml")

        result = _parse_jacoco_files([path])

        assert result["coverage"] == 0


class TestParsePitestFiles:
    """Tests for _parse_pitest_files function."""

    def test_parses_mutations(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <mutations>
            <mutation status="KILLED"/>
            <mutation status="KILLED"/>
            <mutation status="SURVIVED"/>
            <mutation status="NO_COVERAGE"/>
        </mutations>"""
        path = tmp_path / "mutations.xml"
        path.write_text(xml)

        result = _parse_pitest_files([path])

        assert result["mutation_killed"] == 2
        assert result["mutation_survived"] == 1
        assert result["mutation_score"] == 50  # 2/(2+1+1)


class TestParseCheckstyleFiles:
    """Tests for _parse_checkstyle_files function."""

    def test_counts_errors(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <checkstyle>
            <file name="Test.java">
                <error severity="warning" message="Missing javadoc"/>
                <error severity="error" message="Wrong indent"/>
            </file>
        </checkstyle>"""
        path = tmp_path / "checkstyle-result.xml"
        path.write_text(xml)

        result = _parse_checkstyle_files([path])

        assert result["checkstyle_issues"] == 2


class TestParseSpotbugsFiles:
    """Tests for _parse_spotbugs_files function."""

    def test_counts_bugs(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <BugCollection>
            <BugInstance type="NP_NULL_ON_SOME_PATH"/>
            <BugInstance type="DM_DEFAULT_ENCODING"/>
        </BugCollection>"""
        path = tmp_path / "spotbugsXml.xml"
        path.write_text(xml)

        result = _parse_spotbugs_files([path])

        assert result["spotbugs_issues"] == 2


class TestParsePmdFiles:
    """Tests for _parse_pmd_files function."""

    def test_counts_violations(self, tmp_path: Path) -> None:
        xml = """<?xml version="1.0"?>
        <pmd>
            <file name="Test.java">
                <violation>Some violation</violation>
                <violation>Another violation</violation>
            </file>
        </pmd>"""
        path = tmp_path / "pmd.xml"
        path.write_text(xml)

        result = _parse_pmd_files([path])

        assert result["pmd_violations"] == 2


class TestParseDependencyCheck:
    """Tests for _parse_dependency_check function."""

    def test_counts_vulnerabilities_by_severity(self, tmp_path: Path) -> None:
        data = {
            "dependencies": [
                {
                    "vulnerabilities": [
                        {"severity": "CRITICAL"},
                        {"severity": "HIGH"},
                    ]
                },
                {
                    "vulnerabilities": [
                        {"severity": "MEDIUM"},
                        {"severity": "LOW"},
                    ]
                }
            ]
        }
        path = tmp_path / "dependency-check.json"
        path.write_text(json.dumps(data))

        result = _parse_dependency_check(path)

        assert result["owasp_critical"] == 1
        assert result["owasp_high"] == 1
        assert result["owasp_medium"] == 1
        assert result["owasp_low"] == 1

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        result = _parse_dependency_check(tmp_path / "missing.json")

        assert result["owasp_critical"] == 0


class TestCountPipAuditVulns:
    """Tests for _count_pip_audit_vulns function."""

    def test_counts_vulns_list_format(self) -> None:
        data = [
            {"name": "package1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
            {"name": "package2", "vulnerabilities": [{"id": "CVE-3"}]},
        ]
        assert _count_pip_audit_vulns(data) == 3

    def test_returns_zero_for_non_list(self) -> None:
        assert _count_pip_audit_vulns({"some": "dict"}) == 0
        assert _count_pip_audit_vulns(None) == 0


class TestDetectMutmutPaths:
    """Tests for _detect_mutmut_paths function."""

    def test_detects_src_directory(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()

        result = _detect_mutmut_paths(tmp_path)

        assert result == "src/"

    def test_detects_package_with_init(self, tmp_path: Path) -> None:
        (tmp_path / "mypackage").mkdir()
        (tmp_path / "mypackage" / "__init__.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "mypackage/"

    def test_ignores_test_directories(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "__init__.py").write_text("")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "app/"

    def test_returns_dot_when_no_package_found(self, tmp_path: Path) -> None:
        (tmp_path / "file.py").write_text("")

        result = _detect_mutmut_paths(tmp_path)

        assert result == "."


class TestRunRuff:
    """Tests for run_ruff function."""

    def test_runs_ruff_and_parses_output(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '[{"code": "E501", "message": "Line too long"}]'
        mock_proc.stderr = ""

        with patch("cihub.ci_runner._run_command", return_value=mock_proc):
            result = run_ruff(tmp_path, output_dir)

        assert result.tool == "ruff"
        assert result.ran is True
        assert result.success is True
        assert result.metrics["ruff_errors"] == 1

    def test_counts_security_issues(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '[{"code": "S101"}, {"code": "S105"}, {"code": "E501"}]'
        mock_proc.stderr = ""

        with patch("cihub.ci_runner._run_command", return_value=mock_proc):
            result = run_ruff(tmp_path, output_dir)

        assert result.metrics["ruff_security"] == 2
        assert result.metrics["ruff_errors"] == 3


class TestRunBlack:
    """Tests for run_black function."""

    def test_counts_reformat_needed(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "would reformat file1.py\nwould reformat file2.py\n"
        mock_proc.stderr = ""

        with patch("cihub.ci_runner._run_command", return_value=mock_proc):
            result = run_black(tmp_path, output_dir)

        assert result.tool == "black"
        assert result.success is False
        assert result.metrics["black_issues"] == 2


class TestRunIsort:
    """Tests for run_isort function."""

    def test_counts_error_lines(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "ERROR: file1.py\nERROR: file2.py\nSkipping"
        mock_proc.stderr = ""

        with patch("cihub.ci_runner._run_command", return_value=mock_proc):
            result = run_isort(tmp_path, output_dir)

        assert result.tool == "isort"
        assert result.metrics["isort_issues"] == 2


class TestRunMypy:
    """Tests for run_mypy function."""

    def test_counts_errors(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "file.py:1: error: Missing return\nfile.py:5: error: Type mismatch"
        mock_proc.stderr = ""

        with patch("cihub.ci_runner._run_command", return_value=mock_proc):
            result = run_mypy(tmp_path, output_dir)

        assert result.tool == "mypy"
        assert result.metrics["mypy_errors"] == 2
