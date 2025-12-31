"""Tests for hub_ci command handlers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from unittest import mock

import pytest


class TestWriteOutputs:
    """Tests for _write_outputs helper."""

    def test_writes_to_stdout_when_no_path(self, capsys) -> None:
        from cihub.commands.hub_ci import _write_outputs

        _write_outputs({"key1": "value1", "key2": "value2"}, None)
        captured = capsys.readouterr()
        assert "key1=value1" in captured.out
        assert "key2=value2" in captured.out

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _write_outputs

        output_path = tmp_path / "output.txt"
        _write_outputs({"issues": "5"}, output_path)
        content = output_path.read_text()
        assert "issues=5\n" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _write_outputs

        output_path = tmp_path / "output.txt"
        output_path.write_text("existing=value\n")
        _write_outputs({"new": "data"}, output_path)
        content = output_path.read_text()
        assert "existing=value" in content
        assert "new=data" in content


class TestAppendSummary:
    """Tests for _append_summary helper."""

    def test_prints_to_stdout_when_no_path(self, capsys) -> None:
        from cihub.commands.hub_ci import _append_summary

        _append_summary("Summary text", None)
        captured = capsys.readouterr()
        assert "Summary text" in captured.out

    def test_writes_to_file_when_path_provided(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _append_summary

        summary_path = tmp_path / "summary.md"
        _append_summary("## Test Summary", summary_path)
        content = summary_path.read_text()
        assert "## Test Summary" in content

    def test_adds_newline_if_missing(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _append_summary

        summary_path = tmp_path / "summary.md"
        _append_summary("No newline", summary_path)
        content = summary_path.read_text()
        assert content.endswith("\n")


class TestResolveOutputPath:
    """Tests for _resolve_output_path helper."""

    def test_returns_path_from_value(self) -> None:
        from cihub.commands.hub_ci import _resolve_output_path

        result = _resolve_output_path("/some/path.txt", False)
        assert result == Path("/some/path.txt")

    def test_returns_env_path_when_github_output_true(self) -> None:
        from cihub.commands.hub_ci import _resolve_output_path

        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": "/env/path.txt"}):
            result = _resolve_output_path(None, True)
            assert result == Path("/env/path.txt")

    def test_returns_none_when_no_path_and_no_flag(self) -> None:
        from cihub.commands.hub_ci import _resolve_output_path

        result = _resolve_output_path(None, False)
        assert result is None

    def test_returns_none_when_github_output_true_but_env_missing(self) -> None:
        from cihub.commands.hub_ci import _resolve_output_path

        with mock.patch.dict(os.environ, {}, clear=True):
            # Remove GITHUB_OUTPUT if present
            os.environ.pop("GITHUB_OUTPUT", None)
            result = _resolve_output_path(None, True)
            assert result is None


class TestResolveSummaryPath:
    """Tests for _resolve_summary_path helper."""

    def test_returns_path_from_value(self) -> None:
        from cihub.commands.hub_ci import _resolve_summary_path

        result = _resolve_summary_path("/some/summary.md", False)
        assert result == Path("/some/summary.md")

    def test_returns_env_path_when_github_summary_true(self) -> None:
        from cihub.commands.hub_ci import _resolve_summary_path

        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/env/summary.md"}):
            result = _resolve_summary_path(None, True)
            assert result == Path("/env/summary.md")


class TestExtractCount:
    """Tests for _extract_count helper."""

    def test_extracts_count_from_emoji_line(self) -> None:
        from cihub.commands.hub_ci import _extract_count

        line = "🎉 42 🙁 5"
        assert _extract_count(line, "🎉") == 42
        assert _extract_count(line, "🙁") == 5

    def test_returns_zero_when_emoji_not_found(self) -> None:
        from cihub.commands.hub_ci import _extract_count

        line = "🎉 42"
        assert _extract_count(line, "⏰") == 0

    def test_returns_zero_for_empty_line(self) -> None:
        from cihub.commands.hub_ci import _extract_count

        assert _extract_count("", "🎉") == 0


class TestCountPipAuditVulns:
    """Tests for _count_pip_audit_vulns helper."""

    def test_counts_vulns_in_list_format(self) -> None:
        from cihub.commands.hub_ci import _count_pip_audit_vulns

        data = [
            {"name": "package1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
            {"name": "package2", "vulns": [{"id": "CVE-3"}]},
        ]
        assert _count_pip_audit_vulns(data) == 3

    def test_handles_vulnerabilities_key(self) -> None:
        from cihub.commands.hub_ci import _count_pip_audit_vulns

        data = [{"name": "pkg", "vulnerabilities": [{"id": "CVE-1"}]}]
        assert _count_pip_audit_vulns(data) == 1

    def test_returns_zero_for_non_list(self) -> None:
        from cihub.commands.hub_ci import _count_pip_audit_vulns

        assert _count_pip_audit_vulns({}) == 0
        assert _count_pip_audit_vulns(None) == 0

    def test_returns_zero_for_empty_vulns(self) -> None:
        from cihub.commands.hub_ci import _count_pip_audit_vulns

        data = [{"name": "pkg", "vulns": []}]
        assert _count_pip_audit_vulns(data) == 0


class TestCmdRuff:
    """Tests for cmd_ruff command."""

    @mock.patch("cihub.commands.hub_ci._run_command")
    @mock.patch("subprocess.run")
    def test_returns_success_when_no_issues(
        self, mock_subprocess: mock.Mock, mock_run: mock.Mock
    ) -> None:
        from cihub.commands.hub_ci import cmd_ruff
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(stdout="[]", returncode=0)
        mock_subprocess.return_value = mock.Mock(returncode=0)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
        )
        result = cmd_ruff(args)
        assert result == EXIT_SUCCESS

    @mock.patch("cihub.commands.hub_ci._run_command")
    @mock.patch("subprocess.run")
    def test_returns_failure_when_issues_found(
        self, mock_subprocess: mock.Mock, mock_run: mock.Mock
    ) -> None:
        from cihub.commands.hub_ci import cmd_ruff
        from cihub.exit_codes import EXIT_FAILURE

        mock_run.return_value = mock.Mock(
            stdout='[{"code": "E501"}]',
            returncode=0,
        )
        mock_subprocess.return_value = mock.Mock(returncode=1)

        args = argparse.Namespace(
            path=".",
            force_exclude=False,
            output=None,
            github_output=False,
        )
        result = cmd_ruff(args)
        assert result == EXIT_FAILURE


class TestCmdBlack:
    """Tests for cmd_black command."""

    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_returns_success_no_issues(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_black
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(stdout="", stderr="", returncode=0)

        args = argparse.Namespace(
            path=".",
            output=None,
            github_output=False,
        )
        result = cmd_black(args)
        assert result == EXIT_SUCCESS

    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_counts_would_reformat(self, mock_run: mock.Mock, capsys) -> None:
        from cihub.commands.hub_ci import cmd_black

        mock_run.return_value = mock.Mock(
            stdout="would reformat file1.py\nwould reformat file2.py",
            stderr="",
            returncode=1,
        )

        args = argparse.Namespace(
            path=".",
            output=None,
            github_output=False,
        )
        cmd_black(args)
        captured = capsys.readouterr()
        assert "issues=2" in captured.out


class TestCmdBandit:
    """Tests for cmd_bandit command."""

    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_returns_success_no_high_issues(
        self, mock_run: mock.Mock, tmp_path: Path
    ) -> None:
        from cihub.commands.hub_ci import cmd_bandit
        from cihub.exit_codes import EXIT_SUCCESS

        output_file = tmp_path / "bandit.json"
        output_file.write_text(json.dumps({"results": []}))
        mock_run.return_value = mock.Mock(returncode=0)

        args = argparse.Namespace(
            paths=["cihub"],
            output=str(output_file),
            severity="low",
            confidence="low",
            summary=None,
            github_summary=False,
        )
        result = cmd_bandit(args)
        assert result == EXIT_SUCCESS

    @mock.patch("subprocess.run")
    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_returns_failure_with_high_issues(
        self, mock_run: mock.Mock, mock_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        from cihub.commands.hub_ci import cmd_bandit
        from cihub.exit_codes import EXIT_FAILURE

        output_file = tmp_path / "bandit.json"
        output_file.write_text(
            json.dumps({"results": [{"issue_severity": "HIGH"}]})
        )
        mock_run.return_value = mock.Mock(returncode=0)
        mock_subprocess.return_value = mock.Mock(returncode=0)

        args = argparse.Namespace(
            paths=["cihub"],
            output=str(output_file),
            severity="low",
            confidence="low",
            summary=None,
            github_summary=False,
        )
        result = cmd_bandit(args)
        assert result == EXIT_FAILURE


class TestCmdZizmorCheck:
    """Tests for cmd_zizmor_check command."""

    def test_returns_failure_when_sarif_missing(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_zizmor_check
        from cihub.exit_codes import EXIT_FAILURE

        args = argparse.Namespace(
            sarif=str(tmp_path / "missing.sarif"),
            summary=None,
            github_summary=False,
        )
        result = cmd_zizmor_check(args)
        assert result == EXIT_FAILURE

    def test_returns_success_no_findings(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_zizmor_check
        from cihub.exit_codes import EXIT_SUCCESS

        sarif_path = tmp_path / "zizmor.sarif"
        sarif_path.write_text(json.dumps({"runs": [{"results": []}]}))

        args = argparse.Namespace(
            sarif=str(sarif_path),
            summary=None,
            github_summary=False,
        )
        result = cmd_zizmor_check(args)
        assert result == EXIT_SUCCESS

    def test_returns_failure_with_findings(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_zizmor_check
        from cihub.exit_codes import EXIT_FAILURE

        sarif_path = tmp_path / "zizmor.sarif"
        sarif_path.write_text(
            json.dumps(
                {"runs": [{"results": [{"level": "error"}]}]}
            )
        )

        args = argparse.Namespace(
            sarif=str(sarif_path),
            summary=None,
            github_summary=False,
        )
        result = cmd_zizmor_check(args)
        assert result == EXIT_FAILURE


class TestCmdValidateProfiles:
    """Tests for cmd_validate_profiles command."""

    def test_validates_yaml_files(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_validate_profiles
        from cihub.exit_codes import EXIT_SUCCESS

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "test.yaml").write_text("key: value\n")

        args = argparse.Namespace(profiles_dir=str(profiles_dir))
        result = cmd_validate_profiles(args)
        assert result == EXIT_SUCCESS

    def test_fails_on_non_dict_yaml(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_validate_profiles
        from cihub.exit_codes import EXIT_FAILURE

        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "bad.yaml").write_text("- list\n- item\n")

        args = argparse.Namespace(profiles_dir=str(profiles_dir))
        result = cmd_validate_profiles(args)
        assert result == EXIT_FAILURE


class TestCmdLicenseCheck:
    """Tests for cmd_license_check command."""

    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_returns_success_no_copyleft(self, mock_run: mock.Mock) -> None:
        from cihub.commands.hub_ci import cmd_license_check
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            stdout="Name,Version,License\npytest,7.0,MIT\n",
            returncode=0,
        )

        args = argparse.Namespace(summary=None, github_summary=False)
        result = cmd_license_check(args)
        assert result == EXIT_SUCCESS

    @mock.patch("cihub.commands.hub_ci._run_command")
    def test_warns_on_copyleft(self, mock_run: mock.Mock, capsys) -> None:
        from cihub.commands.hub_ci import cmd_license_check
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            stdout="Name,Version,License\nsome-pkg,1.0,GPL-3.0\n",
            returncode=0,
        )

        args = argparse.Namespace(summary=None, github_summary=False)
        result = cmd_license_check(args)
        # Still returns success but warns
        assert result == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "copyleft" in captured.out.lower() or "GPL" in captured.out


class TestCmdEnforce:
    """Tests for cmd_enforce command."""

    def test_returns_success_when_all_pass(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_SUCCESS

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result == EXIT_SUCCESS

    def test_returns_failure_when_check_fails(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_FAILURE

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "failure",  # This one fails
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "success",
            "RESULT_MUTATION": "success",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "success",
            "RESULT_SCORECARD": "success",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result == EXIT_FAILURE

    def test_ignores_skipped_results(self) -> None:
        from cihub.commands.hub_ci import cmd_enforce
        from cihub.exit_codes import EXIT_SUCCESS

        env = {
            "RESULT_ACTIONLINT": "success",
            "RESULT_ZIZMOR": "success",
            "RESULT_LINT": "success",
            "RESULT_TYPECHECK": "success",
            "RESULT_YAMLLINT": "success",
            "RESULT_SYNTAX": "success",
            "RESULT_UNIT_TESTS": "skipped",  # Skipped, not failure
            "RESULT_MUTATION": "skipped",
            "RESULT_BANDIT": "success",
            "RESULT_PIP_AUDIT": "success",
            "RESULT_SECRET_SCAN": "success",
            "RESULT_TRIVY": "success",
            "RESULT_TEMPLATES": "success",
            "RESULT_CONFIGS": "success",
            "RESULT_MATRIX_KEYS": "success",
            "RESULT_LICENSE": "success",
            "RESULT_DEP_REVIEW": "skipped",
            "RESULT_SCORECARD": "skipped",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            args = argparse.Namespace()
            result = cmd_enforce(args)
            assert result == EXIT_SUCCESS


class TestCmdHubCi:
    """Tests for cmd_hub_ci main router."""

    def test_routes_to_correct_handler(self) -> None:
        from cihub.commands.hub_ci import cmd_hub_ci

        with mock.patch("cihub.commands.hub_ci.cmd_validate_profiles") as mock_handler:
            mock_handler.return_value = 0
            args = argparse.Namespace(subcommand="validate-profiles", profiles_dir=None)
            cmd_hub_ci(args)
            mock_handler.assert_called_once_with(args)

    def test_returns_usage_error_for_unknown_subcommand(self) -> None:
        from cihub.commands.hub_ci import cmd_hub_ci
        from cihub.exit_codes import EXIT_USAGE

        args = argparse.Namespace(subcommand="unknown-command")
        result = cmd_hub_ci(args)
        assert result == EXIT_USAGE
