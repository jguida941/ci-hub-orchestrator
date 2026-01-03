"""Tests for cihub.services.ci_engine module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cihub.services.ci_engine import (
    JAVA_TOOLS,
    PYTHON_TOOLS,
    _apply_force_all_tools,
    _build_context,
    _collect_codecov_files,
    _detect_java_project_type,
    _evaluate_java_gates,
    _evaluate_python_gates,
    _get_env_name,
    _get_env_value,
    _get_repo_name,
    _install_python_dependencies,
    _notify,
    _resolve_workdir,
    _run_codecov_upload,
    _run_dep_command,
    _run_java_tools,
    _run_python_tools,
    _send_email,
    _send_slack,
    _set_tool_enabled,
    _tool_enabled,
    _tool_gate_enabled,
    _warn_reserved_features,
)


class TestGetRepoName:
    """Tests for _get_repo_name function."""

    def test_from_github_repository_env(self, tmp_path: Path) -> None:
        config: dict = {}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            result = _get_repo_name(config, tmp_path)
        assert result == "owner/repo"

    def test_from_config_repo_section(self, tmp_path: Path) -> None:
        config = {"repo": {"owner": "myowner", "name": "myrepo"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.services.ci_engine.get_git_remote", return_value=None):
                result = _get_repo_name(config, tmp_path)
        assert result == "myowner/myrepo"

    def test_from_git_remote(self, tmp_path: Path) -> None:
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "cihub.services.ci_engine.get_git_remote",
                return_value="git@github.com:gitowner/gitrepo.git",
            ):
                with patch(
                    "cihub.services.ci_engine.parse_repo_from_remote",
                    return_value=("gitowner", "gitrepo"),
                ):
                    result = _get_repo_name(config, tmp_path)
        assert result == "gitowner/gitrepo"

    def test_returns_empty_when_no_source(self, tmp_path: Path) -> None:
        config: dict = {}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.services.ci_engine.get_git_remote", return_value=None):
                result = _get_repo_name(config, tmp_path)
        assert result == ""


class TestResolveWorkdir:
    """Tests for _resolve_workdir function."""

    def test_override_takes_precedence(self, tmp_path: Path) -> None:
        config = {"repo": {"subdir": "src"}}
        with patch("cihub.services.ci_engine.validate_subdir"):
            result = _resolve_workdir(tmp_path, config, "override")
        assert result == "override"

    def test_uses_config_subdir(self, tmp_path: Path) -> None:
        config = {"repo": {"subdir": "mysubdir"}}
        with patch("cihub.services.ci_engine.validate_subdir"):
            result = _resolve_workdir(tmp_path, config, None)
        assert result == "mysubdir"

    def test_returns_dot_when_no_subdir(self, tmp_path: Path) -> None:
        config: dict = {}
        result = _resolve_workdir(tmp_path, config, None)
        assert result == "."


class TestDetectJavaProjectType:
    """Tests for _detect_java_project_type function."""

    def test_maven_multi_module(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text("<modules><module>a</module><module>b</module></modules>")
        result = _detect_java_project_type(tmp_path)
        assert "Multi-module" in result
        assert "2 modules" in result

    def test_maven_single_module(self, tmp_path: Path) -> None:
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><name>single</name></project>")
        result = _detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_gradle_multi_module(self, tmp_path: Path) -> None:
        (tmp_path / "settings.gradle").write_text("include 'a', 'b'")
        result = _detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_gradle_kts_multi_module(self, tmp_path: Path) -> None:
        (tmp_path / "settings.gradle.kts").write_text('include(":a")')
        result = _detect_java_project_type(tmp_path)
        assert result == "Multi-module"

    def test_gradle_single_module(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'")
        result = _detect_java_project_type(tmp_path)
        assert result == "Single module"

    def test_unknown_project(self, tmp_path: Path) -> None:
        result = _detect_java_project_type(tmp_path)
        assert result == "Unknown"


class TestToolEnabled:
    """Tests for _tool_enabled function."""

    def test_enabled_with_bool_true(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_disabled_with_bool_false(self) -> None:
        config = {"python": {"tools": {"pytest": False}}}
        assert _tool_enabled(config, "pytest", "python") is False

    def test_enabled_with_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_enabled(config, "pytest", "python") is True

    def test_disabled_with_dict(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": False}}}}
        assert _tool_enabled(config, "pytest", "python") is False

    def test_missing_tool(self) -> None:
        config = {"python": {"tools": {}}}
        assert _tool_enabled(config, "pytest", "python") is False


class TestToolGateEnabled:
    """Tests for _tool_gate_enabled function - gate configuration."""

    def test_python_ruff_gate(self) -> None:
        config = {"python": {"tools": {"ruff": {"fail_on_error": False}}}}
        assert _tool_gate_enabled(config, "ruff", "python") is False

    def test_python_black_gate(self) -> None:
        config = {"python": {"tools": {"black": {"fail_on_format_issues": False}}}}
        assert _tool_gate_enabled(config, "black", "python") is False

    def test_python_isort_gate(self) -> None:
        config = {"python": {"tools": {"isort": {"fail_on_issues": False}}}}
        assert _tool_gate_enabled(config, "isort", "python") is False

    def test_python_bandit_gate(self) -> None:
        config = {"python": {"tools": {"bandit": {"fail_on_high": False}}}}
        assert _tool_gate_enabled(config, "bandit", "python") is False

    def test_python_pip_audit_gate(self) -> None:
        config = {"python": {"tools": {"pip_audit": {"fail_on_vuln": False}}}}
        assert _tool_gate_enabled(config, "pip_audit", "python") is False

    def test_python_semgrep_gate(self) -> None:
        config = {"python": {"tools": {"semgrep": {"fail_on_findings": False}}}}
        assert _tool_gate_enabled(config, "semgrep", "python") is False

    def test_python_trivy_gate_critical(self) -> None:
        config = {"python": {"tools": {"trivy": {"fail_on_critical": False, "fail_on_high": False}}}}
        assert _tool_gate_enabled(config, "trivy", "python") is False

    def test_java_checkstyle_gate(self) -> None:
        config = {"java": {"tools": {"checkstyle": {"fail_on_violation": False}}}}
        assert _tool_gate_enabled(config, "checkstyle", "java") is False

    def test_java_spotbugs_gate(self) -> None:
        config = {"java": {"tools": {"spotbugs": {"fail_on_error": False}}}}
        assert _tool_gate_enabled(config, "spotbugs", "java") is False

    def test_java_pmd_gate(self) -> None:
        config = {"java": {"tools": {"pmd": {"fail_on_violation": False}}}}
        assert _tool_gate_enabled(config, "pmd", "java") is False

    def test_defaults_to_true(self) -> None:
        config = {"python": {"tools": {"pytest": {"enabled": True}}}}
        assert _tool_gate_enabled(config, "pytest", "python") is True

    def test_non_dict_entry_returns_true(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        assert _tool_gate_enabled(config, "pytest", "python") is True


class TestGetEnvName:
    """Tests for _get_env_name function."""

    def test_returns_config_value(self) -> None:
        config = {"mykey": "MY_ENV_VAR"}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "MY_ENV_VAR"

    def test_returns_default_when_missing(self) -> None:
        config: dict = {}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "DEFAULT"

    def test_strips_whitespace(self) -> None:
        config = {"mykey": "  MY_VAR  "}
        result = _get_env_name(config, "mykey", "DEFAULT")
        assert result == "MY_VAR"


class TestGetEnvValue:
    """Tests for _get_env_value function."""

    def test_returns_primary_value(self) -> None:
        env = {"PRIMARY": "value1", "FALLBACK": "value2"}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result == "value1"

    def test_returns_fallback_when_primary_missing(self) -> None:
        env = {"FALLBACK": "value2"}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result == "value2"

    def test_returns_none_when_no_match(self) -> None:
        env: dict = {}
        result = _get_env_value(env, "PRIMARY", ["FALLBACK"])
        assert result is None


class TestWarnReservedFeatures:
    """Tests for _warn_reserved_features function."""

    def test_warns_for_enabled_dict(self) -> None:
        config = {"chaos": {"enabled": True}}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 1
        assert "CIHUB-CI-RESERVED-FEATURE" in problems[0]["code"]

    def test_warns_for_enabled_bool(self) -> None:
        config = {"dr_drill": True}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 1

    def test_no_warning_for_disabled(self) -> None:
        config = {"chaos": {"enabled": False}}
        problems: list = []
        _warn_reserved_features(config, problems)
        assert len(problems) == 0


class TestSetToolEnabled:
    """Tests for _set_tool_enabled function."""

    def test_sets_enabled_on_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": {"min_coverage": 80}}}}
        _set_tool_enabled(config, "python", "pytest", False)
        assert config["python"]["tools"]["pytest"]["enabled"] is False

    def test_creates_dict_for_non_dict_entry(self) -> None:
        config = {"python": {"tools": {"pytest": True}}}
        _set_tool_enabled(config, "python", "pytest", False)
        assert config["python"]["tools"]["pytest"]["enabled"] is False

    def test_creates_structure_from_scratch(self) -> None:
        config: dict = {}
        _set_tool_enabled(config, "python", "pytest", True)
        assert config["python"]["tools"]["pytest"]["enabled"] is True


class TestApplyForceAllTools:
    """Tests for _apply_force_all_tools function."""

    def test_enables_all_python_tools(self) -> None:
        config = {"repo": {"force_all_tools": True}, "python": {"tools": {}}}
        _apply_force_all_tools(config, "python")
        for tool in PYTHON_TOOLS:
            assert config["python"]["tools"][tool]["enabled"] is True

    def test_enables_all_java_tools(self) -> None:
        config = {"repo": {"force_all_tools": True}, "java": {"tools": {}}}
        _apply_force_all_tools(config, "java")
        for tool in JAVA_TOOLS:
            assert config["java"]["tools"][tool]["enabled"] is True

    def test_does_nothing_when_disabled(self) -> None:
        config = {"repo": {"force_all_tools": False}, "python": {"tools": {}}}
        _apply_force_all_tools(config, "python")
        assert config["python"]["tools"] == {}


class TestCollectCodecovFiles:
    """Tests for _collect_codecov_files function."""

    def test_collects_python_coverage(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        tool_outputs = {"pytest": {"artifacts": {"coverage": str(coverage)}}}
        files = _collect_codecov_files("python", tmp_path, tool_outputs)
        assert len(files) == 1
        assert files[0] == coverage

    def test_fallback_coverage_path(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        tool_outputs: dict = {}
        files = _collect_codecov_files("python", tmp_path, tool_outputs)
        assert len(files) == 1

    def test_collects_java_jacoco(self, tmp_path: Path) -> None:
        jacoco = tmp_path / "jacoco.xml"
        jacoco.write_text("<report/>")
        tool_outputs = {"jacoco": {"artifacts": {"report": str(jacoco)}}}
        files = _collect_codecov_files("java", tmp_path, tool_outputs)
        assert len(files) == 1


class TestRunCodecovUpload:
    """Tests for _run_codecov_upload function."""

    def test_warns_when_no_files(self) -> None:
        problems: list = []
        _run_codecov_upload([], False, problems)
        assert len(problems) == 1
        assert "no coverage files" in problems[0]["message"].lower()

    def test_warns_when_codecov_missing(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        with patch("shutil.which", return_value=None):
            _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 1
        assert "uploader not found" in problems[0]["message"].lower()

    def test_runs_codecov_successfully(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("shutil.which", return_value="/usr/bin/codecov"):
            with patch("subprocess.run", return_value=mock_proc):
                _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 0

    def test_reports_codecov_failure(self, tmp_path: Path) -> None:
        coverage = tmp_path / "coverage.xml"
        coverage.write_text("<coverage/>")
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "upload failed"
        mock_proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/codecov"):
            with patch("subprocess.run", return_value=mock_proc):
                _run_codecov_upload([coverage], False, problems)
        assert len(problems) == 1
        assert "upload failed" in problems[0]["message"]


class TestSendSlack:
    """Tests for _send_slack function."""

    def test_sends_notification(self) -> None:
        problems: list = []
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            _send_slack("https://hooks.slack.com/test", "Test message", problems)
        assert len(problems) == 0

    def test_reports_failure_status(self) -> None:
        problems: list = []
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            _send_slack("https://hooks.slack.com/test", "Test message", problems)
        assert len(problems) == 1
        assert problems[0]["code"] == "CIHUB-CI-SLACK-FAILED"


class TestSendEmail:
    """Tests for _send_email function."""

    def test_warns_when_host_missing(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env: dict = {}
        _send_email("Subject", "Body", problems, email_cfg, env)
        assert len(problems) == 1
        assert "SMTP_HOST" in problems[0]["message"]

    def test_warns_when_recipients_missing(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env = {"SMTP_HOST": "mail.example.com"}
        _send_email("Subject", "Body", problems, email_cfg, env)
        assert len(problems) == 1
        assert "recipients" in problems[0]["message"].lower()

    def test_warns_on_invalid_port(self) -> None:
        problems: list = []
        email_cfg: dict = {}
        env = {
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "invalid",
            "SMTP_TO": "test@example.com",
        }
        # Should still attempt send with default port 25
        with patch("smtplib.SMTP") as mock_smtp:
            mock_client = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            _send_email("Subject", "Body", problems, email_cfg, env)
        # Should have warned about invalid port
        port_warning = [p for p in problems if "port" in p["message"].lower()]
        assert len(port_warning) == 1


class TestNotify:
    """Tests for _notify function."""

    def test_does_nothing_when_disabled(self) -> None:
        config = {"notifications": {"slack": {"enabled": False}}}
        report = {"repository": "owner/repo", "branch": "main"}
        problems: list = []
        with patch("cihub.services.ci_engine._send_slack") as mock_slack:
            _notify(True, config, report, problems, {})
        mock_slack.assert_not_called()

    def test_sends_slack_on_failure(self) -> None:
        config = {"notifications": {"slack": {"enabled": True, "on_failure": True, "on_success": False}}}
        report = {"repository": "owner/repo", "branch": "main"}
        env = {"CIHUB_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}
        problems: list = []
        with patch("cihub.services.ci_engine._send_slack") as mock_slack:
            _notify(False, config, report, problems, env)
        mock_slack.assert_called_once()

    def test_warns_when_webhook_missing(self) -> None:
        config = {"notifications": {"slack": {"enabled": True, "on_failure": True}}}
        report = {"repository": "owner/repo", "branch": "main"}
        problems: list = []
        _notify(False, config, report, problems, {})
        assert len(problems) == 1
        assert "CIHUB_SLACK_WEBHOOK_URL" in problems[0]["message"]

    def test_sends_email_on_failure(self) -> None:
        config = {"notifications": {"email": {"enabled": True, "on_failure": True}}}
        report = {"repository": "owner/repo", "branch": "main"}
        env = {"SMTP_HOST": "mail.example.com", "SMTP_TO": "test@example.com"}
        problems: list = []
        with patch("smtplib.SMTP") as mock_smtp:
            mock_client = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            _notify(False, config, report, problems, env)
        # Email was sent via SMTP
        mock_smtp.assert_called_once()


class TestRunDepCommand:
    """Tests for _run_dep_command function."""

    def test_success_returns_true(self, tmp_path: Path) -> None:
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc):
            result = _run_dep_command(["echo", "hello"], tmp_path, "test", problems)
        assert result is True
        assert len(problems) == 0

    def test_failure_returns_false_and_adds_problem(self, tmp_path: Path) -> None:
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "error occurred"
        mock_proc.stdout = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = _run_dep_command(["false"], tmp_path, "test cmd", problems)
        assert result is False
        assert len(problems) == 1
        assert "test cmd failed" in problems[0]["message"]


class TestInstallPythonDependencies:
    """Tests for _install_python_dependencies function."""

    def test_skips_when_install_disabled(self, tmp_path: Path) -> None:
        config = {"python": {"dependencies": {"install": False}}}
        problems: list = []
        _install_python_dependencies(config, tmp_path, problems)
        assert len(problems) == 0

    def test_runs_custom_commands(self, tmp_path: Path) -> None:
        config = {"python": {"dependencies": {"commands": ["pip install pytest"]}}}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc):
            _install_python_dependencies(config, tmp_path, problems)
        assert len(problems) == 0

    def test_installs_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("pytest\n")
        config: dict = {}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            _install_python_dependencies(config, tmp_path, problems)
        # Should have called pip install -r requirements.txt
        assert mock_run.called

    def test_installs_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        config: dict = {}
        problems: list = []
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            _install_python_dependencies(config, tmp_path, problems)
        assert mock_run.called


class TestRunPythonTools:
    """Tests for _run_python_tools function."""

    def test_runs_enabled_tools(self, tmp_path: Path) -> None:
        from cihub.ci_runner import ToolResult

        workdir = tmp_path / "repo"
        workdir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {"python": {"tools": {"ruff": {"enabled": True}}}}
        problems: list = []

        mock_result = ToolResult(tool="ruff", ran=True, success=True, metrics={"ruff_errors": 0})
        with patch("cihub.services.ci_engine.run_ruff", return_value=mock_result):
            outputs, ran, success = _run_python_tools(config, tmp_path, "repo", output_dir, problems)

        assert ran.get("ruff") is True
        assert success.get("ruff") is True

    def test_warns_for_unsupported_tool(self, tmp_path: Path) -> None:
        workdir = tmp_path / "repo"
        workdir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {
            "python": {
                "tools": {"codeql": {"enabled": True}}  # codeql has no runner
            }
        }
        problems: list = []

        _run_python_tools(config, tmp_path, "repo", output_dir, problems)

        # Should have warned about unsupported tool
        unsupported_warnings = [p for p in problems if "not supported" in p["message"]]
        assert len(unsupported_warnings) == 1

    def test_raises_for_missing_workdir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config: dict = {}
        problems: list = []

        with pytest.raises(FileNotFoundError):
            _run_python_tools(config, tmp_path, "nonexistent", output_dir, problems)


class TestRunJavaTools:
    """Tests for _run_java_tools function."""

    def test_runs_java_build(self, tmp_path: Path) -> None:
        from cihub.ci_runner import ToolResult

        workdir = tmp_path / "repo"
        workdir.mkdir()
        (workdir / "pom.xml").write_text("<project/>")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = {"java": {"tools": {"jacoco": {"enabled": False}}}}
        problems: list = []

        mock_build = ToolResult(tool="build", ran=True, success=True, metrics={})
        with patch("cihub.services.ci_engine.run_java_build", return_value=mock_build):
            outputs, ran, success = _run_java_tools(config, tmp_path, "repo", output_dir, "maven", problems)

        assert "build" in outputs

    def test_raises_for_missing_workdir(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config: dict = {}
        problems: list = []

        with pytest.raises(FileNotFoundError):
            _run_java_tools(config, tmp_path, "nonexistent", output_dir, "maven", problems)


class TestBuildContext:
    """Tests for _build_context function."""

    def test_builds_context_from_config(self, tmp_path: Path) -> None:
        # default_branch from config is used when GITHUB_REF_NAME is not set
        config = {"repo": {"owner": "myorg", "name": "myrepo", "default_branch": "main"}}
        with patch.dict(os.environ, {}, clear=True):
            with patch("cihub.services.ci_engine.get_git_branch", return_value="develop"):
                ctx = _build_context(tmp_path, config, ".", None)

        # Config default_branch takes precedence over git_branch when no env var
        assert ctx.branch == "main"
        assert ctx.workdir == "."

    def test_uses_github_env_vars(self, tmp_path: Path) -> None:
        config: dict = {}
        env = {
            "GITHUB_REPOSITORY": "org/repo",
            "GITHUB_REF_NAME": "feature-branch",
            "GITHUB_RUN_ID": "12345",
            "GITHUB_SHA": "abc123",
        }
        with patch.dict(os.environ, env, clear=True):
            ctx = _build_context(tmp_path, config, "src", "corr-123")

        assert ctx.branch == "feature-branch"
        assert ctx.run_id == "12345"
        assert ctx.commit == "abc123"
        assert ctx.correlation_id == "corr-123"


class TestEvaluatePythonGates:
    """Tests for _evaluate_python_gates function."""

    def test_detects_test_failures(self) -> None:
        report = {"results": {"tests_failed": 5}}
        thresholds: dict = {}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert "pytest failures detected" in failures

    def test_detects_coverage_below_threshold(self) -> None:
        report = {"results": {"coverage": 60}}
        thresholds = {"coverage_min": 80}
        tools_configured = {"pytest": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("coverage 60%" in f for f in failures)

    def test_detects_mutation_score_below_threshold(self) -> None:
        report = {"results": {"mutation_score": 50}}
        thresholds = {"mutation_score_min": 70}
        tools_configured = {"mutmut": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("mutation score 50%" in f for f in failures)

    def test_detects_ruff_errors(self) -> None:
        report = {"tool_metrics": {"ruff_errors": 10}}
        thresholds = {"max_ruff_errors": 0}
        tools_configured = {"ruff": True}
        config = {"python": {"tools": {"ruff": {"fail_on_error": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("ruff errors" in f for f in failures)

    def test_detects_bandit_high_vulns(self) -> None:
        report = {"tool_metrics": {"bandit_high": 3}}
        thresholds = {"max_high_vulns": 0}
        tools_configured = {"bandit": True}
        config = {"python": {"tools": {"bandit": {"fail_on_high": True}}}}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert any("bandit high" in f for f in failures)

    def test_no_failures_when_all_pass(self) -> None:
        report = {"results": {"coverage": 90, "tests_failed": 0}, "tool_metrics": {"ruff_errors": 0}}
        thresholds = {"coverage_min": 80}
        tools_configured = {"pytest": True, "ruff": True}
        config: dict = {}

        failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

        assert len(failures) == 0


class TestEvaluateJavaGates:
    """Tests for _evaluate_java_gates function."""

    def test_detects_test_failures(self) -> None:
        report = {"results": {"tests_failed": 2}}
        thresholds: dict = {}
        tools_configured: dict = {}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert "test failures detected" in failures

    def test_detects_coverage_below_threshold(self) -> None:
        report = {"results": {"coverage": 50}}
        thresholds = {"coverage_min": 70}
        tools_configured = {"jacoco": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("coverage 50%" in f for f in failures)

    def test_detects_checkstyle_issues(self) -> None:
        report = {"tool_metrics": {"checkstyle_issues": 15}}
        thresholds = {"max_checkstyle_errors": 0}
        tools_configured = {"checkstyle": True}
        config = {"java": {"tools": {"checkstyle": {"fail_on_violation": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("checkstyle issues" in f for f in failures)

    def test_detects_spotbugs_issues(self) -> None:
        report = {"tool_metrics": {"spotbugs_issues": 5}}
        thresholds = {"max_spotbugs_bugs": 0}
        tools_configured = {"spotbugs": True}
        config = {"java": {"tools": {"spotbugs": {"fail_on_error": True}}}}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("spotbugs issues" in f for f in failures)

    def test_detects_owasp_vulns(self) -> None:
        report = {"tool_metrics": {"owasp_critical": 1, "owasp_high": 2}}
        thresholds = {"max_critical_vulns": 0, "max_high_vulns": 0}
        tools_configured = {"owasp": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert any("owasp critical/high" in f for f in failures)

    def test_no_failures_when_all_pass(self) -> None:
        report = {"results": {"coverage": 85, "tests_failed": 0}, "tool_metrics": {}}
        thresholds = {"coverage_min": 70}
        tools_configured = {"jacoco": True}
        config: dict = {}

        failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

        assert len(failures) == 0
