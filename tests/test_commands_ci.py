"""Tests for CI engine helpers and CLI adapter behavior."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from cihub.commands import ci as ci_cmd
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services import ci_engine


def test_get_repo_name_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    assert ci_engine._get_repo_name({}, tmp_path) == "owner/repo"


def test_get_repo_name_from_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    config = {"repo": {"owner": "org", "name": "project"}}
    assert ci_engine._get_repo_name(config, tmp_path) == "org/project"


def test_get_repo_name_from_remote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with mock.patch.object(ci_engine, "get_git_remote", return_value="git@github.com:org/project.git"):
        with mock.patch.object(ci_engine, "parse_repo_from_remote", return_value=("org", "project")):
            assert ci_engine._get_repo_name({}, tmp_path) == "org/project"


def test_get_env_value_with_fallback() -> None:
    env = {"PRIMARY": "one", "FALLBACK": "two"}
    assert ci_engine._get_env_value(env, "PRIMARY") == "one"
    assert ci_engine._get_env_value(env, "MISSING", ["FALLBACK"]) == "two"
    assert ci_engine._get_env_value(env, None, ["MISSING"]) is None


def test_get_git_commit_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_engine, "resolve_executable", return_value="git"):
        with mock.patch.object(subprocess, "check_output", return_value="abc123\n"):
            assert ci_engine._get_git_commit(tmp_path) == "abc123"


def test_get_git_commit_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with mock.patch.object(ci_engine, "resolve_executable", return_value="git"):
        with mock.patch.object(subprocess, "check_output", side_effect=subprocess.CalledProcessError(1, ["git"])):
            assert ci_engine._get_git_commit(tmp_path) == ""


def test_resolve_workdir(tmp_path: Path) -> None:
    config = {"repo": {"subdir": "src"}}
    assert ci_engine._resolve_workdir(tmp_path, config, "override") == "override"
    assert ci_engine._resolve_workdir(tmp_path, config, None) == "src"
    assert ci_engine._resolve_workdir(tmp_path, {}, None) == "."


def test_detect_java_project_type(tmp_path: Path) -> None:
    pom = tmp_path / "pom.xml"
    pom.write_text("<modules><module>a</module><module>b</module></modules>", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module (2 modules)"


def test_detect_java_project_type_gradle(tmp_path: Path) -> None:
    (tmp_path / "build.gradle").write_text("// gradle", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Single module"


def test_tool_enabled_and_gate() -> None:
    config = {
        "python": {"tools": {"ruff": {"enabled": True, "fail_on_error": False}, "black": True}},
        "java": {"tools": {"spotbugs": {"enabled": True}}},
    }
    assert ci_engine._tool_enabled(config, "ruff", "python") is True
    assert ci_engine._tool_enabled(config, "bandit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "ruff", "python") is False
    assert ci_engine._tool_gate_enabled(config, "black", "python") is True
    assert ci_engine._tool_gate_enabled(config, "spotbugs", "java") is True


def test_tool_gate_enabled_python_tools() -> None:
    """Test all Python tool gate options."""
    # Test each Python tool gate option
    config = {
        "python": {
            "tools": {
                "black": {"enabled": True, "fail_on_format_issues": False},
                "isort": {"enabled": True, "fail_on_issues": False},
                "bandit": {"enabled": True, "fail_on_high": False},
                "pip_audit": {"enabled": True, "fail_on_vuln": False},
                "semgrep": {"enabled": True, "fail_on_findings": False},
                "trivy": {"enabled": True, "fail_on_critical": False, "fail_on_high": False},
            }
        }
    }
    assert ci_engine._tool_gate_enabled(config, "black", "python") is False
    assert ci_engine._tool_gate_enabled(config, "isort", "python") is False
    assert ci_engine._tool_gate_enabled(config, "bandit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "pip_audit", "python") is False
    assert ci_engine._tool_gate_enabled(config, "semgrep", "python") is False
    assert ci_engine._tool_gate_enabled(config, "trivy", "python") is False


def test_tool_gate_enabled_java_tools() -> None:
    """Test all Java tool gate options."""
    config = {
        "java": {
            "tools": {
                "checkstyle": {"enabled": True, "fail_on_violation": False},
                "pmd": {"enabled": True, "fail_on_violation": False},
                "semgrep": {"enabled": True, "fail_on_findings": False},
                "trivy": {"enabled": True, "fail_on_critical": False, "fail_on_high": False},
            }
        }
    }
    assert ci_engine._tool_gate_enabled(config, "checkstyle", "java") is False
    assert ci_engine._tool_gate_enabled(config, "pmd", "java") is False
    assert ci_engine._tool_gate_enabled(config, "semgrep", "java") is False
    assert ci_engine._tool_gate_enabled(config, "trivy", "java") is False


def test_warn_reserved_features_adds_problem() -> None:
    problems: list[dict[str, object]] = []
    config = {"chaos": {"enabled": True}}
    ci_engine._warn_reserved_features(config, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-RESERVED-FEATURE"


def test_warn_reserved_features_kyverno() -> None:
    """Test that kyverno also triggers reserved feature warning."""
    problems: list[dict[str, object]] = []
    config = {"kyverno": {"enabled": True}}
    ci_engine._warn_reserved_features(config, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-RESERVED-FEATURE"
    assert "Kyverno" in problems[0]["message"]


def test_get_env_name_returns_config_value() -> None:
    config = {"codecov_env_name": "CODECOV_CUSTOM"}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_CUSTOM"


def test_get_env_name_returns_default() -> None:
    config = {}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_TOKEN"


def test_get_env_name_ignores_whitespace_only() -> None:
    config = {"codecov_env_name": "   "}
    assert ci_engine._get_env_name(config, "codecov_env_name", "CODECOV_TOKEN") == "CODECOV_TOKEN"


def test_split_problems() -> None:
    problems = [
        {"severity": "error", "message": "Error 1"},
        {"severity": "warning", "message": "Warning 1"},
        {"severity": "error", "message": "Error 2"},
        {"severity": "info", "message": "Info 1"},
    ]
    errors, warnings = ci_engine._split_problems(problems)
    assert errors == ["Error 1", "Error 2"]
    assert warnings == ["Warning 1"]


def test_split_problems_empty_messages_filtered() -> None:
    problems = [
        {"severity": "error", "message": ""},
        {"severity": "warning", "message": "Valid warning"},
    ]
    errors, warnings = ci_engine._split_problems(problems)
    assert errors == []
    assert warnings == ["Valid warning"]


def test_detect_java_project_type_settings_gradle(tmp_path: Path) -> None:
    """Test detection of multi-module Gradle project via settings.gradle."""
    (tmp_path / "settings.gradle").write_text("include 'sub1', 'sub2'", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module"


def test_detect_java_project_type_settings_gradle_kts(tmp_path: Path) -> None:
    """Test detection of multi-module Gradle project via settings.gradle.kts."""
    (tmp_path / "settings.gradle.kts").write_text('include("sub1")', encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Multi-module"


def test_detect_java_project_type_unknown(tmp_path: Path) -> None:
    """Test unknown project type when no build files present."""
    assert ci_engine._detect_java_project_type(tmp_path) == "Unknown"


def test_detect_java_project_type_pom_single_module(tmp_path: Path) -> None:
    """Test single module Maven project (pom without modules)."""
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    assert ci_engine._detect_java_project_type(tmp_path) == "Single module"


def test_apply_env_overrides_sets_tools_and_summary() -> None:
    config: dict[str, object] = {"python": {"tools": {}}, "reports": {"github_summary": {"enabled": True}}}
    env = {"CIHUB_RUN_PYTEST": "true", "CIHUB_WRITE_GITHUB_SUMMARY": "false"}
    problems: list[dict[str, object]] = []

    ci_engine._apply_env_overrides(config, "python", env, problems)

    tools = config["python"]["tools"]
    assert tools["pytest"]["enabled"] is True
    assert config["reports"]["github_summary"]["enabled"] is False
    assert problems == []


def test_apply_env_overrides_invalid_value_adds_warning() -> None:
    config: dict[str, object] = {"python": {"tools": {}}}
    env = {"CIHUB_RUN_RUFF": "maybe"}
    problems: list[dict[str, object]] = []

    ci_engine._apply_env_overrides(config, "python", env, problems)

    assert problems
    assert problems[0]["code"] == "CIHUB-CI-ENV-BOOL"


def test_collect_codecov_files(tmp_path: Path) -> None:
    coverage_file = tmp_path / "coverage.xml"
    coverage_file.write_text("data", encoding="utf-8")
    tool_outputs = {"pytest": {"artifacts": {"coverage": str(coverage_file)}}}

    files = ci_engine._collect_codecov_files("python", tmp_path, tool_outputs)

    assert files == [coverage_file]


def test_run_codecov_upload_with_no_files() -> None:
    problems: list[dict[str, object]] = []
    ci_engine._run_codecov_upload([], False, problems)
    assert problems
    assert problems[0]["code"] == "CIHUB-CI-CODECOV-NO-FILES"


def test_cmd_ci_python_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"
    summary_path = repo / "summary.md"
    report_path = repo / "report.json"

    args = argparse.Namespace(
        repo=str(repo),
        json=True,
        output_dir=str(output_dir),
        summary=str(summary_path),
        report=str(report_path),
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )

    service_result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report_path,
        summary_path=summary_path,
        artifacts={"report": str(report_path), "summary": str(summary_path)},
        data={"report_path": str(report_path), "summary_path": str(summary_path)},
    )

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_SUCCESS
    assert result.data["report_path"] == str(report_path)
    assert result.data["summary_path"] == str(summary_path)


def test_cmd_ci_java_non_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = repo / ".cihub"

    args = argparse.Namespace(
        repo=str(repo),
        json=False,
        output_dir=str(output_dir),
        summary=None,
        report=None,
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )

    service_result = ci_engine.CiRunResult(success=True, exit_code=EXIT_SUCCESS)

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result == EXIT_SUCCESS


def test_cmd_ci_unknown_language(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    args = argparse.Namespace(
        repo=str(repo),
        json=True,
        output_dir=str(repo / ".cihub"),
        summary=None,
        report=None,
        workdir=None,
        install_deps=False,
        correlation_id=None,
        no_summary=False,
        write_github_summary=None,
        config_from_hub=None,
    )
    service_result = ci_engine.CiRunResult(success=False, exit_code=EXIT_FAILURE, errors=["bad language"])

    with mock.patch.object(ci_cmd, "run_ci", return_value=service_result):
        result = ci_cmd.cmd_ci(args)

    assert result.exit_code == EXIT_FAILURE


def test_print_result_with_paths(tmp_path: Path, capsys) -> None:
    """Test _print_result outputs report and summary paths."""
    report = tmp_path / "report.json"
    summary = tmp_path / "summary.md"
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        report_path=report,
        summary_path=summary,
    )

    ci_cmd._print_result(result)

    out = capsys.readouterr().out
    assert f"Wrote report: {report}" in out
    assert f"Wrote summary: {summary}" in out


def test_print_result_with_problems(capsys) -> None:
    """Test _print_result outputs problems list."""
    result = ci_engine.CiRunResult(
        success=False,
        exit_code=EXIT_FAILURE,
        problems=[
            {"severity": "error", "message": "Test failed"},
            {"severity": "warning", "message": "Coverage low"},
        ],
    )

    ci_cmd._print_result(result)

    out = capsys.readouterr().out
    assert "CI findings:" in out
    assert "[error] Test failed" in out
    assert "[warning] Coverage low" in out


def test_summary_for_result_with_errors_no_report() -> None:
    """Test _summary_for_result returns first error when no report."""
    result = ci_engine.CiRunResult(
        success=False,
        exit_code=EXIT_FAILURE,
        errors=["First error", "Second error"],
        report={},
    )
    assert ci_cmd._summary_for_result(result) == "First error"


def test_summary_for_result_with_problems() -> None:
    """Test _summary_for_result returns issues message when problems exist."""
    result = ci_engine.CiRunResult(
        success=True,
        exit_code=EXIT_SUCCESS,
        problems=[{"severity": "warning", "message": "Low coverage"}],
    )
    assert ci_cmd._summary_for_result(result) == "CI completed with issues"


def test_summary_for_result_success() -> None:
    """Test _summary_for_result returns success message."""
    result = ci_engine.CiRunResult(success=True, exit_code=EXIT_SUCCESS)
    assert ci_cmd._summary_for_result(result) == "CI completed"
