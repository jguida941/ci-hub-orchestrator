"""Tests for cihub.ci_report module."""

from __future__ import annotations

from typing import Any

import pytest

from cihub.ci_report import (
    RunContext,
    _get_metric,
    _set_threshold,
    build_java_report,
    build_python_report,
    resolve_thresholds,
)


class TestRunContext:
    """Tests for RunContext dataclass."""

    def test_creates_context(self) -> None:
        ctx = RunContext(
            repository="org/repo",
            branch="main",
            run_id="123",
            run_number="42",
            commit="abc123",
            correlation_id="corr-id",
            workflow_ref="workflow.yml",
            workdir=".",
            build_tool="maven",
            retention_days=30,
            project_type="Single module",
            docker_compose_file=None,
            docker_health_endpoint=None,
        )
        assert ctx.repository == "org/repo"
        assert ctx.branch == "main"
        assert ctx.run_id == "123"
        assert ctx.build_tool == "maven"

    def test_context_is_frozen(self) -> None:
        ctx = RunContext(
            repository="test",
            branch=None,
            run_id=None,
            run_number=None,
            commit=None,
            correlation_id=None,
            workflow_ref=None,
            workdir=None,
            build_tool=None,
            retention_days=None,
            project_type=None,
            docker_compose_file=None,
            docker_health_endpoint=None,
        )
        with pytest.raises(AttributeError):
            ctx.repository = "changed"  # type: ignore[misc]


class TestSetThreshold:
    """Tests for _set_threshold helper."""

    def test_sets_value_when_not_present(self) -> None:
        thresholds: dict[str, Any] = {}
        _set_threshold(thresholds, "coverage_min", 70)
        assert thresholds["coverage_min"] == 70

    def test_does_not_overwrite_existing(self) -> None:
        thresholds = {"coverage_min": 80}
        _set_threshold(thresholds, "coverage_min", 70)
        assert thresholds["coverage_min"] == 80

    def test_ignores_none_value(self) -> None:
        thresholds: dict[str, Any] = {}
        _set_threshold(thresholds, "coverage_min", None)
        assert "coverage_min" not in thresholds


class TestResolveThresholds:
    """Tests for resolve_thresholds function."""

    def test_resolves_python_thresholds(self) -> None:
        config = {
            "thresholds": {"coverage_min": 75},
            "python": {
                "tools": {
                    "pytest": {"min_coverage": 80},
                    "mutmut": {"min_mutation_score": 65},
                    "ruff": {"max_errors": 5},
                }
            },
        }
        result = resolve_thresholds(config, "python")

        assert result["coverage_min"] == 75  # From thresholds (not overwritten)
        assert result["mutation_score_min"] == 65
        assert result["max_ruff_errors"] == 5

    def test_resolves_java_thresholds(self) -> None:
        config = {
            "java": {
                "tools": {
                    "jacoco": {"min_coverage": 85},
                    "pitest": {"min_mutation_score": 70},
                    "checkstyle": {"max_errors": 0},
                    "spotbugs": {"max_bugs": 5},
                    "owasp": {"fail_on_cvss": 7},
                }
            },
        }
        result = resolve_thresholds(config, "java")

        assert result["coverage_min"] == 85
        assert result["mutation_score_min"] == 70
        assert result["max_checkstyle_errors"] == 0
        assert result["max_spotbugs_bugs"] == 5
        assert result["owasp_cvss_fail"] == 7

    def test_handles_empty_config(self) -> None:
        result = resolve_thresholds({}, "python")
        assert result == {}

    def test_python_pip_audit_fallback(self) -> None:
        config = {
            "thresholds": {"max_high_vulns": 10},
            "python": {"tools": {}},
        }
        result = resolve_thresholds(config, "python")
        assert result["max_pip_audit_vulns"] == 10


class TestGetMetric:
    """Tests for _get_metric helper."""

    def test_gets_metric_value(self) -> None:
        tool_results = {"pytest": {"metrics": {"coverage": 85}}}
        assert _get_metric(tool_results, "pytest", "coverage") == 85

    def test_returns_default_when_tool_missing(self) -> None:
        assert _get_metric({}, "pytest", "coverage", 0) == 0

    def test_returns_default_when_metric_missing(self) -> None:
        tool_results = {"pytest": {"metrics": {}}}
        assert _get_metric(tool_results, "pytest", "coverage", 50) == 50

    def test_converts_string_to_int(self) -> None:
        tool_results = {"pytest": {"metrics": {"tests_passed": "100"}}}
        assert _get_metric(tool_results, "pytest", "tests_passed") == 100

    def test_converts_string_to_float(self) -> None:
        tool_results = {"pytest": {"metrics": {"runtime": "1.5"}}}
        assert _get_metric(tool_results, "pytest", "runtime") == 1.5

    def test_returns_default_for_invalid_string(self) -> None:
        tool_results = {"pytest": {"metrics": {"count": "not_a_number"}}}
        assert _get_metric(tool_results, "pytest", "count", 0) == 0


class TestBuildPythonReport:
    """Tests for build_python_report function."""

    def _make_context(self) -> RunContext:
        return RunContext(
            repository="test/repo",
            branch="main",
            run_id="1",
            run_number="1",
            commit="abc",
            correlation_id=None,
            workflow_ref="workflow.yml",
            workdir=".",
            build_tool=None,
            retention_days=30,
            project_type=None,
            docker_compose_file=None,
            docker_health_endpoint=None,
        )

    def test_builds_basic_report(self) -> None:
        report = build_python_report(
            config={"python": {"version": "3.12"}},
            tool_results={},
            tools_configured={"pytest": True, "ruff": True},
            tools_ran={"pytest": True},
            tools_success={"pytest": True},
            thresholds={"coverage_min": 70},
            context=self._make_context(),
        )

        assert report["schema_version"] == "2.0"
        assert report["python_version"] == "3.12"
        assert report["repository"] == "test/repo"
        assert report["thresholds"]["coverage_min"] == 70

    def test_calculates_test_status(self) -> None:
        # When tests pass
        report = build_python_report(
            config={},
            tool_results={"pytest": {"metrics": {"tests_failed": 0, "tests_passed": 10}}},
            tools_configured={"pytest": True},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["test"] == "success"

        # When tests fail
        report = build_python_report(
            config={},
            tool_results={"pytest": {"metrics": {"tests_failed": 2, "tests_passed": 8}}},
            tools_configured={"pytest": True},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["test"] == "failure"

    def test_aggregates_vulnerability_counts(self) -> None:
        report = build_python_report(
            config={},
            tool_results={
                "bandit": {"metrics": {"bandit_high": 2, "bandit_medium": 3}},
                "trivy": {"metrics": {"trivy_high": 1, "trivy_critical": 5}},
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )

        assert report["results"]["high_vulns"] == 3  # bandit + trivy
        assert report["results"]["critical_vulns"] == 5


class TestBuildJavaReport:
    """Tests for build_java_report function."""

    def _make_context(self) -> RunContext:
        return RunContext(
            repository="test/repo",
            branch="main",
            run_id="1",
            run_number="1",
            commit="abc",
            correlation_id=None,
            workflow_ref="workflow.yml",
            workdir=".",
            build_tool="maven",
            retention_days=30,
            project_type="Single module",
            docker_compose_file=None,
            docker_health_endpoint=None,
        )

    def test_builds_basic_report(self) -> None:
        report = build_java_report(
            config={"java": {"version": "21", "build_tool": "maven"}},
            tool_results={"build": {"success": True}},
            tools_configured={"jacoco": True, "checkstyle": True},
            tools_ran={"jacoco": True},
            tools_success={"jacoco": True},
            thresholds={"coverage_min": 80},
            context=self._make_context(),
        )

        assert report["schema_version"] == "2.0"
        assert report["java_version"] == "21"
        assert report["environment"]["build_tool"] == "maven"
        assert report["results"]["build"] == "success"

    def test_build_failure_status(self) -> None:
        report = build_java_report(
            config={"java": {}},
            tool_results={"build": {"success": False}},
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["build"] == "failure"

    def test_build_failure_on_test_failures(self) -> None:
        report = build_java_report(
            config={"java": {}},
            tool_results={"build": {"success": True, "metrics": {"tests_failed": 3}}},
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["build"] == "failure"

    def test_extracts_coverage_metrics(self) -> None:
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {"success": True},
                "jacoco": {"metrics": {"coverage": 85, "coverage_lines_covered": 850}},
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )

        assert report["results"]["coverage"] == 85
        assert report["results"]["coverage_lines_covered"] == 850

    def test_extracts_owasp_vulnerabilities(self) -> None:
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {"success": True},
                "owasp": {"metrics": {"owasp_critical": 2, "owasp_high": 5}},
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )

        assert report["tool_metrics"]["owasp_critical"] == 2
        assert report["tool_metrics"]["owasp_high"] == 5
