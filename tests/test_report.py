"""Tests for cihub.commands.report module."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cihub.commands.report import (
    _build_context,
    _detect_java_project_type,
    _get_repo_name,
    _load_tool_outputs,
    _tool_enabled,
    cmd_report,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE


class TestToolEnabled:
    """Tests for _tool_enabled helper."""

    def test_returns_true_for_bool_true(self) -> None:
        config = {"python": {"tools": {"ruff": True}}}
        assert _tool_enabled(config, "ruff", "python") is True

    def test_returns_false_for_bool_false(self) -> None:
        config = {"python": {"tools": {"ruff": False}}}
        assert _tool_enabled(config, "ruff", "python") is False

    def test_returns_enabled_from_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_returns_false_for_missing_tool(self) -> None:
        config = {"python": {"tools": {}}}
        assert _tool_enabled(config, "missing", "python") is False

    def test_handles_java_language(self) -> None:
        config = {"java": {"tools": {"jacoco": True}}}
        assert _tool_enabled(config, "jacoco", "java") is True


class TestGetRepoName:
    """Tests for _get_repo_name helper."""

    def test_returns_github_repository_env(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            result = _get_repo_name({}, tmp_path)
        assert result == "owner/repo"

    def test_returns_config_owner_and_name(self, tmp_path: Path) -> None:
        config = {"repo": {"owner": "myorg", "name": "myrepo"}}
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_REPOSITORY", None)
            result = _get_repo_name(config, tmp_path)
        assert result == "myorg/myrepo"

    def test_parses_from_git_remote(self, tmp_path: Path) -> None:
        # Patch at helpers module where functions are looked up
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("cihub.commands.report.helpers.get_git_remote") as mock_remote,
            patch("cihub.commands.report.helpers.parse_repo_from_remote") as mock_parse,
        ):
            os.environ.pop("GITHUB_REPOSITORY", None)
            mock_remote.return_value = "git@github.com:parsed/repo.git"
            mock_parse.return_value = ("parsed", "repo")
            result = _get_repo_name({}, tmp_path)
        assert result == "parsed/repo"

    def test_returns_empty_when_no_info(self, tmp_path: Path) -> None:
        # Patch at helpers module where function is looked up
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("cihub.commands.report.helpers.get_git_remote") as mock_remote,
        ):
            os.environ.pop("GITHUB_REPOSITORY", None)
            mock_remote.return_value = None
            result = _get_repo_name({}, tmp_path)
        assert result == ""


class TestBuildContext:
    """Tests for _build_context helper."""

    def test_builds_context_with_env_vars(self, tmp_path: Path) -> None:
        env = {
            "GITHUB_REF_NAME": "feature-branch",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_NUMBER": "42",
            "GITHUB_SHA": "abc123",
            "GITHUB_WORKFLOW_REF": "workflow.yml",
        }
        with patch.dict(os.environ, env):
            context = _build_context(tmp_path, {}, ".", "correlation-id")
        assert context.branch == "feature-branch"
        assert context.run_id == "123"
        assert context.run_number == "42"
        assert context.commit == "abc123"
        assert context.correlation_id == "correlation-id"

    def test_falls_back_to_config_branch(self, tmp_path: Path) -> None:
        config = {"repo": {"default_branch": "main"}}
        with patch.dict(os.environ, {}, clear=True):
            for key in ["GITHUB_REF_NAME", "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER", "GITHUB_SHA", "GITHUB_WORKFLOW_REF"]:
                os.environ.pop(key, None)
            context = _build_context(tmp_path, config, ".", None)
        assert context.branch == "main"

    def test_includes_java_specific_fields(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {}, clear=True):
            context = _build_context(
                tmp_path,
                {},
                ".",
                correlation_id=None,
                build_tool="gradle",
                project_type="Multi-module",
                docker_compose_file="docker-compose.yml",
                docker_health_endpoint="/health",
            )
        assert context.build_tool == "gradle"
        assert context.project_type == "Multi-module"
        assert context.docker_compose_file == "docker-compose.yml"
        assert context.docker_health_endpoint == "/health"

    def test_includes_retention_days(self, tmp_path: Path) -> None:
        config = {"reports": {"retention_days": 14}}
        with patch.dict(os.environ, {}, clear=True):
            context = _build_context(tmp_path, config, ".", None)
        assert context.retention_days == 14


class TestDetectJavaProjectType:
    """Tests for _detect_java_project_type helper."""

    def test_detects_maven_multimodule(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text("""
            <project>
                <modules>
                    <module>core</module>
                    <module>web</module>
                </modules>
            </project>
        """)
        result = _detect_java_project_type(tmp_path)
        assert "Multi-module" in result
        assert "2 modules" in result

    def test_detects_maven_single_module(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><artifactId>app</artifactId></project>")
        result = _detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_detects_gradle_multimodule(self, tmp_path: Path) -> None:
        (tmp_path / "settings.gradle").write_text("include 'core', 'web'")
        result = _detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_detects_gradle_kts_multimodule(self, tmp_path: Path) -> None:
        (tmp_path / "settings.gradle.kts").write_text('include(":core")')
        result = _detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_detects_gradle_single_module(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        result = _detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_detects_gradle_kts_single_module(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle.kts").write_text("plugins { java }")
        result = _detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_returns_unknown_for_no_build_files(self, tmp_path: Path) -> None:
        result = _detect_java_project_type(tmp_path)
        assert result == "Unknown"

    def test_handles_pom_read_error(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text("")  # Create file
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            # The function catches OSError, so this should not raise
            result = _detect_java_project_type(tmp_path)
        # Will fall through to single module check since content is empty
        assert result == "Single module"


class TestLoadToolOutputs:
    """Tests for _load_tool_outputs helper."""

    def test_loads_json_files(self, tmp_path: Path) -> None:
        (tmp_path / "ruff.json").write_text(json.dumps({"tool": "ruff", "ran": True}))
        (tmp_path / "pytest.json").write_text(json.dumps({"tool": "pytest", "ran": True}))
        result = _load_tool_outputs(tmp_path)
        assert "ruff" in result
        assert "pytest" in result
        assert result["ruff"]["ran"] is True

    def test_uses_filename_as_tool_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "mytest.json").write_text(json.dumps({"ran": True}))
        result = _load_tool_outputs(tmp_path)
        assert "mytest" in result

    def test_skips_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "good.json").write_text(json.dumps({"tool": "good"}))
        (tmp_path / "bad.json").write_text("not valid json")
        result = _load_tool_outputs(tmp_path)
        assert "good" in result
        assert "bad" not in result

    def test_returns_empty_for_no_files(self, tmp_path: Path) -> None:
        result = _load_tool_outputs(tmp_path)
        assert result == {}


class TestCmdReportOutputs:
    """Tests for cmd_report outputs subcommand."""

    def test_extracts_outputs_from_report(self, tmp_path: Path) -> None:
        report = {
            "results": {
                "build": "success",
                "coverage": 85,
                "mutation_score": 75,
            }
        }
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            subcommand="outputs",
            report=str(report_path),
            output=str(output_path),
            json=True,
        )
        result = cmd_report(args)

        assert result.exit_code == EXIT_SUCCESS
        content = output_path.read_text()
        assert "build_status=success" in content
        assert "coverage=85" in content
        assert "mutation_score=75" in content

    def test_infers_status_from_tests_failed(self, tmp_path: Path) -> None:
        report = {"results": {"tests_failed": 5, "coverage": 50}}
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            subcommand="outputs",
            report=str(report_path),
            output=str(output_path),
            json=True,
        )
        cmd_report(args)

        content = output_path.read_text()
        assert "build_status=failure" in content

    def test_uses_github_output_env(self, tmp_path: Path) -> None:
        report = {"results": {"build": "success", "coverage": 80}}
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))
        output_path = tmp_path / "github_output.txt"

        args = argparse.Namespace(
            subcommand="outputs",
            report=str(report_path),
            output=None,
            json=True,
        )

        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path)}):
            result = cmd_report(args)

        assert result.exit_code == EXIT_SUCCESS
        assert output_path.exists()

    def test_fails_when_no_output_target(self, tmp_path: Path) -> None:
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({"results": {}}))

        args = argparse.Namespace(
            subcommand="outputs",
            report=str(report_path),
            output=None,
            json=True,
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GITHUB_OUTPUT", None)
            result = cmd_report(args)

        assert result.exit_code == EXIT_USAGE
        assert "No output target" in result.summary

    def test_fails_when_report_not_found(self, tmp_path: Path) -> None:
        args = argparse.Namespace(
            subcommand="outputs",
            report=str(tmp_path / "missing.json"),
            output=None,
            json=True,
        )
        result = cmd_report(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Failed to read report" in result.summary

    def test_text_mode_prints_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({"results": {"build": "success"}}))
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            subcommand="outputs",
            report=str(report_path),
            output=str(output_path),
            json=False,
        )
        result = cmd_report(args)

        captured = capsys.readouterr()
        assert "Wrote outputs" in captured.out
        assert result == EXIT_SUCCESS


class TestCmdReportSummary:
    """Tests for cmd_report summary subcommand."""

    def test_renders_summary_to_file(self, tmp_path: Path) -> None:
        report = {"summary": {"status": "passed"}}
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report))
        output_path = tmp_path / "summary.md"

        args = argparse.Namespace(
            subcommand="summary",
            report=str(report_path),
            output=str(output_path),
            write_github_summary=False,
            json=True,
        )

        with patch("cihub.commands.report.render_summary_from_path") as mock_render:
            mock_render.return_value = "# Summary\nAll passed!"
            result = cmd_report(args)

        assert result.exit_code == EXIT_SUCCESS
        assert output_path.read_text() == "# Summary\nAll passed!"

    def test_prints_summary_when_no_output(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({}))

        args = argparse.Namespace(
            subcommand="summary",
            report=str(report_path),
            output=None,
            write_github_summary=True,
            json=False,
        )

        with patch("cihub.commands.report.render_summary_from_path") as mock_render:
            mock_render.return_value = "Summary text"
            result = cmd_report(args)

        captured = capsys.readouterr()
        assert "Summary text" in captured.out
        assert result == EXIT_SUCCESS

    def test_writes_to_github_step_summary(self, tmp_path: Path) -> None:
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps({}))
        summary_file = tmp_path / "step_summary.md"

        args = argparse.Namespace(
            subcommand="summary",
            report=str(report_path),
            output=None,
            write_github_summary=True,
            json=False,
        )

        with (
            patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}),
            patch("cihub.commands.report.render_summary_from_path") as mock_render,
        ):
            mock_render.return_value = "# Step Summary"
            cmd_report(args)

        assert summary_file.read_text() == "# Step Summary"


class TestCmdReportBuild:
    """Tests for cmd_report build subcommand."""

    def test_builds_python_report(self, tmp_path: Path) -> None:
        tool_dir = tmp_path / "tool-outputs"
        tool_dir.mkdir()
        (tool_dir / "pytest.json").write_text(
            json.dumps(
                {"tool": "pytest", "ran": True, "success": True, "metrics": {"coverage": 80, "tests_passed": 10}}
            )
        )

        args = argparse.Namespace(
            subcommand="build",
            repo=str(tmp_path),
            output_dir=str(tmp_path),
            tool_dir=str(tool_dir),
            report=str(tmp_path / "report.json"),
            summary=str(tmp_path / "summary.md"),
            workdir=None,
            correlation_id=None,
            json=True,
        )

        # Patch at build module where functions are looked up
        with (
            patch("cihub.commands.report.build.load_ci_config") as mock_load,
            patch("cihub.commands.report.build.build_python_report") as mock_build,
            patch("cihub.commands.report.build.render_summary_from_path") as mock_render,
        ):
            mock_load.return_value = {"language": "python"}
            mock_build.return_value = {"summary": {"status": "passed"}}
            mock_render.return_value = "# Summary"
            result = cmd_report(args)

        assert result.exit_code == EXIT_SUCCESS
        assert (tmp_path / "report.json").exists()

    def test_builds_java_report(self, tmp_path: Path) -> None:
        tool_dir = tmp_path / "tool-outputs"
        tool_dir.mkdir()
        (tool_dir / "build.json").write_text(json.dumps({"tool": "build", "ran": True, "success": True}))

        args = argparse.Namespace(
            subcommand="build",
            repo=str(tmp_path),
            output_dir=str(tmp_path),
            tool_dir=str(tool_dir),
            report=str(tmp_path / "report.json"),
            summary=str(tmp_path / "summary.md"),
            workdir=None,
            correlation_id=None,
            json=True,
        )

        # Patch at build module where functions are looked up
        with (
            patch("cihub.commands.report.build.load_ci_config") as mock_load,
            patch("cihub.commands.report.build.build_java_report") as mock_build,
            patch("cihub.commands.report.build.render_summary_from_path") as mock_render,
        ):
            mock_load.return_value = {"language": "java", "java": {"build_tool": "maven"}}
            mock_build.return_value = {"summary": {"status": "passed"}}
            mock_render.return_value = "# Summary"
            result = cmd_report(args)

        assert result.exit_code == EXIT_SUCCESS
        mock_build.assert_called_once()

    def test_fails_for_unsupported_language(self, tmp_path: Path) -> None:
        tool_dir = tmp_path / "tool-outputs"
        tool_dir.mkdir()

        args = argparse.Namespace(
            subcommand="build",
            repo=str(tmp_path),
            output_dir=str(tmp_path),
            tool_dir=str(tool_dir),
            report=str(tmp_path / "report.json"),
            summary=str(tmp_path / "summary.md"),
            workdir=None,
            correlation_id=None,
            json=True,
        )

        # Patch at build module where function is looked up
        with patch("cihub.commands.report.build.load_ci_config") as mock_load:
            mock_load.return_value = {"language": "ruby"}
            result = cmd_report(args)

        assert result.exit_code == EXIT_FAILURE
        assert "python or java" in result.summary

    def test_fails_on_config_error(self, tmp_path: Path) -> None:
        args = argparse.Namespace(
            subcommand="build",
            repo=str(tmp_path),
            output_dir=str(tmp_path),
            tool_dir=None,
            report=None,
            summary=None,
            workdir=None,
            correlation_id=None,
            json=True,
        )

        # Patch at build module where function is looked up
        with patch("cihub.commands.report.build.load_ci_config") as mock_load:
            mock_load.side_effect = Exception("Config missing")
            result = cmd_report(args)

        assert result.exit_code == EXIT_FAILURE
        assert "Failed to load config" in result.summary

    def test_unknown_subcommand(self, tmp_path: Path) -> None:
        args = argparse.Namespace(
            subcommand="invalid",
            json=True,
        )
        result = cmd_report(args)

        assert result.exit_code == EXIT_USAGE
        assert "Unknown report subcommand" in result.summary

    def test_text_mode_prints_paths(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        tool_dir = tmp_path / "tool-outputs"
        tool_dir.mkdir()

        args = argparse.Namespace(
            subcommand="build",
            repo=str(tmp_path),
            output_dir=str(tmp_path),
            tool_dir=str(tool_dir),
            report=str(tmp_path / "report.json"),
            summary=str(tmp_path / "summary.md"),
            workdir=None,
            correlation_id=None,
            json=False,
        )

        # Patch at build module where functions are looked up
        with (
            patch("cihub.commands.report.build.load_ci_config") as mock_load,
            patch("cihub.commands.report.build.build_python_report") as mock_build,
            patch("cihub.commands.report.build.render_summary_from_path") as mock_render,
        ):
            mock_load.return_value = {"language": "python"}
            mock_build.return_value = {}
            mock_render.return_value = ""
            result = cmd_report(args)

        captured = capsys.readouterr()
        assert "Wrote report" in captured.out
        assert "Wrote summary" in captured.out
        assert result == EXIT_SUCCESS
