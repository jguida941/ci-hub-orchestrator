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

    def test_python_trivy_cvss_fallback_from_owasp(self) -> None:
        """When trivy_cvss_fail not set, falls back to owasp_cvss_fail."""
        config = {
            "thresholds": {"owasp_cvss_fail": 7.5},
            "python": {"tools": {}},
        }
        result = resolve_thresholds(config, "python")
        assert result["trivy_cvss_fail"] == 7.5

    def test_python_trivy_cvss_no_fallback_when_set(self) -> None:
        """trivy_cvss_fail is not overwritten when already set."""
        config = {
            "thresholds": {"owasp_cvss_fail": 7.5, "trivy_cvss_fail": 8.0},
            "python": {"tools": {}},
        }
        result = resolve_thresholds(config, "python")
        assert result["trivy_cvss_fail"] == 8.0

    def test_python_trivy_cvss_from_tools(self) -> None:
        """trivy_cvss_fail can be set from python.tools.trivy."""
        config = {
            "python": {"tools": {"trivy": {"fail_on_cvss": 9.0}}},
        }
        result = resolve_thresholds(config, "python")
        assert result["trivy_cvss_fail"] == 9.0

    def test_python_pip_audit_not_set_without_max_high_vulns(self) -> None:
        """max_pip_audit_vulns not set if max_high_vulns missing."""
        config = {"python": {"tools": {}}}
        result = resolve_thresholds(config, "python")
        assert "max_pip_audit_vulns" not in result

    def test_python_all_tools(self) -> None:
        """Python with all tools configured."""
        config = {
            "python": {
                "tools": {
                    "pytest": {"min_coverage": 80},
                    "mutmut": {"min_mutation_score": 75},
                    "ruff": {"max_errors": 0},
                    "black": {"max_issues": 0},
                    "isort": {"max_issues": 0},
                    "semgrep": {"max_findings": 5},
                    "trivy": {"fail_on_cvss": 7.0},
                }
            },
        }
        result = resolve_thresholds(config, "python")
        assert result["coverage_min"] == 80
        assert result["mutation_score_min"] == 75
        assert result["max_ruff_errors"] == 0
        assert result["max_black_issues"] == 0
        assert result["max_isort_issues"] == 0
        assert result["max_semgrep_findings"] == 5
        assert result["trivy_cvss_fail"] == 7.0

    def test_java_all_tools(self) -> None:
        """Java with all tools configured."""
        config = {
            "java": {
                "tools": {
                    "jacoco": {"min_coverage": 85},
                    "pitest": {"min_mutation_score": 70},
                    "checkstyle": {"max_errors": 0},
                    "spotbugs": {"max_bugs": 0},
                    "pmd": {"max_violations": 10},
                    "owasp": {"fail_on_cvss": 7.0},
                    "semgrep": {"max_findings": 3},
                }
            },
        }
        result = resolve_thresholds(config, "java")
        assert result["coverage_min"] == 85
        assert result["mutation_score_min"] == 70
        assert result["max_checkstyle_errors"] == 0
        assert result["max_spotbugs_bugs"] == 0
        assert result["max_pmd_violations"] == 10
        assert result["owasp_cvss_fail"] == 7.0
        assert result["max_semgrep_findings"] == 3

    def test_language_is_case_sensitive(self) -> None:
        """Language comparison is exact match."""
        config = {"python": {"tools": {"pytest": {"min_coverage": 80}}}}
        # 'java' language should go to java branch, not find python config
        result = resolve_thresholds(config, "java")
        assert "coverage_min" not in result

    def test_handles_none_tools_dict(self) -> None:
        """Handles None as tools dict."""
        config = {"python": {"tools": None}}
        result = resolve_thresholds(config, "python")
        assert result == {}

    def test_handles_none_thresholds(self) -> None:
        """Handles None as thresholds."""
        config = {"thresholds": None, "python": {"tools": {}}}
        result = resolve_thresholds(config, "python")
        assert result == {}


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

    def test_returns_float_value_directly(self) -> None:
        """Float values are returned as-is."""
        tool_results = {"pytest": {"metrics": {"runtime": 3.14159}}}
        result = _get_metric(tool_results, "pytest", "runtime")
        assert result == 3.14159
        assert isinstance(result, float)

    def test_returns_default_for_non_numeric_type(self) -> None:
        """Non-numeric types (list, dict, None) return default."""
        tool_results = {"pytest": {"metrics": {"bad": ["a", "b"]}}}
        assert _get_metric(tool_results, "pytest", "bad", 42) == 42

        tool_results = {"pytest": {"metrics": {"bad": {"nested": True}}}}
        assert _get_metric(tool_results, "pytest", "bad", 99) == 99

        tool_results = {"pytest": {"metrics": {"bad": None}}}
        assert _get_metric(tool_results, "pytest", "bad", 7) == 7

    def test_returns_default_when_metrics_key_missing(self) -> None:
        """When metrics dict is missing entirely, return default."""
        tool_results = {"pytest": {}}
        assert _get_metric(tool_results, "pytest", "coverage", 50) == 50

    def test_string_without_dot_converts_to_int(self) -> None:
        """String '123' without dot converts to int, not float."""
        tool_results = {"pytest": {"metrics": {"count": "123"}}}
        result = _get_metric(tool_results, "pytest", "count")
        assert result == 123
        assert isinstance(result, int)

    def test_string_with_dot_converts_to_float(self) -> None:
        """String '1.0' with dot converts to float."""
        tool_results = {"pytest": {"metrics": {"rate": "1.0"}}}
        result = _get_metric(tool_results, "pytest", "rate")
        assert result == 1.0
        assert isinstance(result, float)


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

    def test_test_status_skipped_when_pytest_disabled(self) -> None:
        """Test status is 'skipped' when pytest not configured."""
        report = build_python_report(
            config={},
            tool_results={},
            tools_configured={"pytest": False},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["test"] == "skipped"

    def test_extracts_all_pytest_metrics(self) -> None:
        """All pytest metrics are extracted correctly."""
        report = build_python_report(
            config={},
            tool_results={
                "pytest": {
                    "metrics": {
                        "tests_failed": 2,
                        "tests_passed": 98,
                        "tests_skipped": 5,
                        "tests_runtime_seconds": 12.5,
                        "coverage": 85,
                        "coverage_lines_covered": 850,
                        "coverage_lines_total": 1000,
                    }
                }
            },
            tools_configured={"pytest": True},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        results = report["results"]
        assert results["tests_passed"] == 98
        assert results["tests_failed"] == 2
        assert results["tests_skipped"] == 5
        assert results["tests_runtime_seconds"] == 12.5
        assert results["coverage"] == 85
        assert results["coverage_lines_covered"] == 850
        assert results["coverage_lines_total"] == 1000

    def test_extracts_mutation_metrics(self) -> None:
        """Mutation testing metrics are extracted."""
        report = build_python_report(
            config={},
            tool_results={
                "mutmut": {
                    "metrics": {
                        "mutation_score": 75,
                        "mutation_killed": 150,
                        "mutation_survived": 50,
                    }
                }
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        results = report["results"]
        assert results["mutation_score"] == 75
        assert results["mutation_killed"] == 150
        assert results["mutation_survived"] == 50

    def test_extracts_all_tool_metrics(self) -> None:
        """All tool metrics are extracted to tool_metrics dict."""
        report = build_python_report(
            config={},
            tool_results={
                "ruff": {"metrics": {"ruff_errors": 5}},
                "mypy": {"metrics": {"mypy_errors": 10}},
                "bandit": {"metrics": {"bandit_high": 1, "bandit_medium": 2, "bandit_low": 3}},
                "black": {"metrics": {"black_issues": 4}},
                "isort": {"metrics": {"isort_issues": 2}},
                "pip_audit": {"metrics": {"pip_audit_vulns": 1}},
                "semgrep": {"metrics": {"semgrep_findings": 7}},
                "trivy": {
                    "metrics": {
                        "trivy_critical": 0,
                        "trivy_high": 1,
                        "trivy_medium": 2,
                        "trivy_low": 3,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        tm = report["tool_metrics"]
        assert tm["ruff_errors"] == 5
        assert tm["mypy_errors"] == 10
        assert tm["bandit_high"] == 1
        assert tm["bandit_medium"] == 2
        assert tm["bandit_low"] == 3
        assert tm["black_issues"] == 4
        assert tm["isort_issues"] == 2
        assert tm["pip_audit_vulns"] == 1
        assert tm["semgrep_findings"] == 7
        assert tm["trivy_critical"] == 0
        assert tm["trivy_high"] == 1
        assert tm["trivy_medium"] == 2
        assert tm["trivy_low"] == 3

    def test_aggregates_low_vulns(self) -> None:
        """Low vulns aggregate bandit_low + trivy_low."""
        report = build_python_report(
            config={},
            tool_results={
                "bandit": {"metrics": {"bandit_low": 5}},
                "trivy": {"metrics": {"trivy_low": 3}},
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["low_vulns"] == 8

    def test_aggregates_medium_vulns(self) -> None:
        """Medium vulns aggregate bandit_medium + trivy_medium."""
        report = build_python_report(
            config={},
            tool_results={
                "bandit": {"metrics": {"bandit_medium": 4}},
                "trivy": {"metrics": {"trivy_medium": 2}},
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["medium_vulns"] == 6

    def test_dependency_severity_matches_trivy(self) -> None:
        """dependency_severity comes from trivy only."""
        report = build_python_report(
            config={},
            tool_results={
                "trivy": {
                    "metrics": {
                        "trivy_critical": 1,
                        "trivy_high": 2,
                        "trivy_medium": 3,
                        "trivy_low": 4,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        ds = report["dependency_severity"]
        assert ds["critical"] == 1
        assert ds["high"] == 2
        assert ds["medium"] == 3
        assert ds["low"] == 4

    def test_context_values_in_report(self) -> None:
        """Context values are correctly placed in report."""
        ctx = RunContext(
            repository="org/repo",
            branch="feature",
            run_id="12345",
            run_number="42",
            commit="abc123def",
            correlation_id="corr-xyz",
            workflow_ref="ci.yml@main",
            workdir="/app",
            build_tool=None,
            retention_days=14,
            project_type=None,
            docker_compose_file=None,
            docker_health_endpoint=None,
        )
        report = build_python_report(
            config={},
            tool_results={},
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=ctx,
        )
        assert report["repository"] == "org/repo"
        assert report["branch"] == "feature"
        assert report["run_id"] == "12345"
        assert report["run_number"] == "42"
        assert report["commit"] == "abc123def"
        assert report["hub_correlation_id"] == "corr-xyz"
        assert report["metadata"]["workflow_ref"] == "ci.yml@main"
        assert report["environment"]["workdir"] == "/app"
        assert report["environment"]["retention_days"] == 14


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

    def test_extracts_all_java_metrics(self) -> None:
        """All Java build and test metrics are extracted."""
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {
                    "success": True,
                    "metrics": {
                        "tests_passed": 100,
                        "tests_failed": 0,
                        "tests_skipped": 5,
                        "tests_runtime_seconds": 30.5,
                    },
                },
                "jacoco": {
                    "metrics": {
                        "coverage": 90,
                        "coverage_lines_covered": 900,
                        "coverage_lines_total": 1000,
                    }
                },
                "pitest": {
                    "metrics": {
                        "mutation_score": 80,
                        "mutation_killed": 160,
                        "mutation_survived": 40,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        results = report["results"]
        assert results["tests_passed"] == 100
        assert results["tests_failed"] == 0
        assert results["tests_skipped"] == 5
        assert results["tests_runtime_seconds"] == 30.5
        assert results["coverage"] == 90
        assert results["coverage_lines_covered"] == 900
        assert results["coverage_lines_total"] == 1000
        assert results["mutation_score"] == 80
        assert results["mutation_killed"] == 160
        assert results["mutation_survived"] == 40

    def test_extracts_all_java_tool_metrics(self) -> None:
        """All Java tool metrics are extracted."""
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {"success": True},
                "checkstyle": {"metrics": {"checkstyle_issues": 10}},
                "spotbugs": {"metrics": {"spotbugs_issues": 5}},
                "pmd": {"metrics": {"pmd_violations": 15}},
                "owasp": {
                    "metrics": {
                        "owasp_critical": 1,
                        "owasp_high": 2,
                        "owasp_medium": 3,
                        "owasp_low": 4,
                    }
                },
                "semgrep": {"metrics": {"semgrep_findings": 7}},
                "trivy": {
                    "metrics": {
                        "trivy_critical": 0,
                        "trivy_high": 1,
                        "trivy_medium": 2,
                        "trivy_low": 3,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        tm = report["tool_metrics"]
        assert tm["checkstyle_issues"] == 10
        assert tm["spotbugs_issues"] == 5
        assert tm["pmd_violations"] == 15
        assert tm["owasp_critical"] == 1
        assert tm["owasp_high"] == 2
        assert tm["owasp_medium"] == 3
        assert tm["owasp_low"] == 4
        assert tm["semgrep_findings"] == 7
        assert tm["trivy_critical"] == 0
        assert tm["trivy_high"] == 1
        assert tm["trivy_medium"] == 2
        assert tm["trivy_low"] == 3

    def test_aggregates_vulns_from_owasp_and_trivy(self) -> None:
        """Java vulns aggregate owasp + trivy."""
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {"success": True},
                "owasp": {
                    "metrics": {
                        "owasp_critical": 1,
                        "owasp_high": 2,
                        "owasp_medium": 3,
                        "owasp_low": 4,
                    }
                },
                "trivy": {
                    "metrics": {
                        "trivy_critical": 5,
                        "trivy_high": 6,
                        "trivy_medium": 7,
                        "trivy_low": 8,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        results = report["results"]
        assert results["critical_vulns"] == 6  # 1 + 5
        assert results["high_vulns"] == 8  # 2 + 6
        assert results["medium_vulns"] == 10  # 3 + 7
        assert results["low_vulns"] == 12  # 4 + 8

    def test_dependency_severity_aggregates_owasp_and_trivy(self) -> None:
        """Java dependency_severity combines owasp + trivy."""
        report = build_java_report(
            config={"java": {}},
            tool_results={
                "build": {"success": True},
                "owasp": {
                    "metrics": {
                        "owasp_critical": 1,
                        "owasp_high": 2,
                        "owasp_medium": 3,
                        "owasp_low": 4,
                    }
                },
                "trivy": {
                    "metrics": {
                        "trivy_critical": 10,
                        "trivy_high": 20,
                        "trivy_medium": 30,
                        "trivy_low": 40,
                    }
                },
            },
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        ds = report["dependency_severity"]
        assert ds["critical"] == 11  # 1 + 10
        assert ds["high"] == 22  # 2 + 20
        assert ds["medium"] == 33  # 3 + 30
        assert ds["low"] == 44  # 4 + 40

    def test_java_context_includes_build_tool(self) -> None:
        """Java report includes build tool and project type in environment."""
        ctx = RunContext(
            repository="org/repo",
            branch="main",
            run_id="1",
            run_number="1",
            commit="abc",
            correlation_id=None,
            workflow_ref="ci.yml",
            workdir="/app",
            build_tool="gradle",
            retention_days=30,
            project_type="Multi module",
            docker_compose_file="docker-compose.yml",
            docker_health_endpoint="/health",
        )
        report = build_java_report(
            config={"java": {}},
            tool_results={"build": {"success": True}},
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=ctx,
        )
        env = report["environment"]
        assert env["build_tool"] == "gradle"
        assert env["project_type"] == "Multi module"
        assert env["docker_compose_file"] == "docker-compose.yml"
        assert env["docker_health_endpoint"] == "/health"

    def test_build_success_with_zero_test_failures(self) -> None:
        """Build succeeds when build.success=True and tests_failed=0."""
        report = build_java_report(
            config={"java": {}},
            tool_results={"build": {"success": True, "metrics": {"tests_failed": 0}}},
            tools_configured={},
            tools_ran={},
            tools_success={},
            thresholds={},
            context=self._make_context(),
        )
        assert report["results"]["build"] == "success"
