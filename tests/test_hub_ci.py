"""Tests for hub_ci command handlers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from unittest import mock


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


class TestCompareBadges:
    """Tests for _compare_badges helper."""

    def test_reports_missing_badges_dir(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _compare_badges

        issues = _compare_badges(tmp_path / "missing", tmp_path)
        assert "missing badges directory" in issues[0]

    def test_detects_missing_extra_and_diff(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import _compare_badges

        expected = tmp_path / "expected"
        actual = tmp_path / "actual"
        expected.mkdir()
        actual.mkdir()

        (expected / "same.json").write_text('{"value": 1}')
        (actual / "same.json").write_text('{"value": 2}')
        (expected / "missing.json").write_text('{"value": 3}')
        (actual / "extra.json").write_text('{"value": 4}')

        issues = _compare_badges(expected, actual)
        assert "diff: same.json" in issues
        assert "missing: missing.json" in issues
        assert "extra: extra.json" in issues


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

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    @mock.patch("subprocess.run")
    def test_returns_success_when_no_issues(self, mock_subprocess: mock.Mock, mock_run: mock.Mock) -> None:
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

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
    @mock.patch("subprocess.run")
    def test_returns_failure_when_issues_found(self, mock_subprocess: mock.Mock, mock_run: mock.Mock) -> None:
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

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
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


class TestCmdBadges:
    """Tests for cmd_badges command."""

    @mock.patch("cihub.commands.hub_ci.badges._compare_badges")
    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_check_mode_success(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        mock_compare: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        (tmp_path / "badges").mkdir()
        mock_main.return_value = 0
        mock_compare.return_value = []

        args = argparse.Namespace(
            check=True,
            config=None,
            output_dir=None,
            artifacts_dir=None,
            ruff_issues=None,
            mutation_score=None,
            mypy_errors=None,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result == EXIT_SUCCESS
        assert mock_main.call_count == 1
        env = mock_main.call_args.kwargs["env"]
        assert env["UPDATE_BADGES"] == "true"
        assert "BADGE_OUTPUT_DIR" in env

    @mock.patch("cihub.commands.hub_ci.badges._compare_badges")
    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_check_mode_detects_drift(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        mock_compare: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_FAILURE

        mock_root.return_value = tmp_path
        (tmp_path / "badges").mkdir()
        mock_main.return_value = 0
        mock_compare.return_value = ["diff: ruff.json"]

        args = argparse.Namespace(
            check=True,
            config=None,
            output_dir=None,
            artifacts_dir=None,
            ruff_issues=None,
            mutation_score=None,
            mypy_errors=None,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result == EXIT_FAILURE

    @mock.patch("cihub.commands.hub_ci.badges.badge_tools.main")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_updates_badges_with_output_dir(
        self,
        mock_root: mock.Mock,
        mock_main: mock.Mock,
        tmp_path: Path,
    ) -> None:
        from cihub.commands.hub_ci import cmd_badges
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_main.return_value = 0

        output_dir = tmp_path / "badges-out"
        args = argparse.Namespace(
            check=False,
            config=None,
            output_dir=str(output_dir),
            artifacts_dir=None,
            ruff_issues=0,
            mutation_score=88.5,
            mypy_errors=2,
            black_issues=None,
            black_status=None,
            zizmor_sarif=None,
        )
        result = cmd_badges(args)

        assert result == EXIT_SUCCESS
        env = mock_main.call_args.kwargs["env"]
        assert env["BADGE_OUTPUT_DIR"] == str(output_dir.resolve())
        assert env["RUFF_ISSUES"] == "0"
        assert env["MUTATION_SCORE"] == "88.5"
        assert env["MYPY_ERRORS"] == "2"

    @mock.patch("cihub.commands.hub_ci.python_tools._run_command")
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


class TestCmdBadgesCommit:
    """Tests for cmd_badges_commit command."""

    @mock.patch("cihub.commands.hub_ci.badges._run_command")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_no_changes(self, mock_root: mock.Mock, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_badges_commit
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_run.side_effect = [
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
        ]

        result = cmd_badges_commit(argparse.Namespace())
        assert result == EXIT_SUCCESS
        assert mock_run.call_count == 4

    @mock.patch("cihub.commands.hub_ci.badges._run_command")
    @mock.patch("cihub.commands.hub_ci.badges.hub_root")
    def test_commits_and_pushes(self, mock_root: mock.Mock, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_badges_commit
        from cihub.exit_codes import EXIT_SUCCESS

        mock_root.return_value = tmp_path
        mock_run.side_effect = [
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
            mock.Mock(returncode=1),
            mock.Mock(returncode=0),
            mock.Mock(returncode=0),
        ]

        result = cmd_badges_commit(argparse.Namespace())
        assert result == EXIT_SUCCESS
        assert mock_run.call_count == 6


class TestCmdBandit:
    """Tests for cmd_bandit command."""

    @mock.patch("cihub.commands.hub_ci.security._run_command")
    def test_returns_success_no_high_issues(self, mock_run: mock.Mock, tmp_path: Path) -> None:
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
    @mock.patch("cihub.commands.hub_ci.security._run_command")
    def test_returns_failure_with_high_issues(
        self, mock_run: mock.Mock, mock_subprocess: mock.Mock, tmp_path: Path
    ) -> None:
        from cihub.commands.hub_ci import cmd_bandit
        from cihub.exit_codes import EXIT_FAILURE

        output_file = tmp_path / "bandit.json"
        output_file.write_text(json.dumps({"results": [{"issue_severity": "HIGH"}]}))
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


class TestCmdZizmorRun:
    """Tests for cmd_zizmor_run command."""

    @mock.patch("subprocess.run")
    def test_writes_sarif_on_success(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout='{"runs": [{"results": []}]}',
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result == EXIT_SUCCESS
        assert output_path.exists()
        assert "runs" in output_path.read_text()

    @mock.patch("subprocess.run")
    def test_writes_sarif_on_findings(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        """Non-zero exit preserves SARIF when stdout is valid."""
        from cihub.commands.hub_ci import cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        # Even if zizmor outputs findings, we keep valid SARIF on non-zero exit
        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout='{"runs": [{"results": [{"level": "error"}]}]}',
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == '{"runs": [{"results": [{"level": "error"}]}]}'

    @mock.patch("subprocess.run")
    def test_writes_empty_sarif_on_failure(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import EMPTY_SARIF, cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        mock_run.return_value = mock.Mock(
            returncode=1,
            stdout="",
        )
        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == EMPTY_SARIF

    @mock.patch("subprocess.run", side_effect=FileNotFoundError)
    def test_writes_empty_sarif_when_zizmor_missing(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import EMPTY_SARIF, cmd_zizmor_run
        from cihub.exit_codes import EXIT_SUCCESS

        output_path = tmp_path / "zizmor.sarif"
        args = argparse.Namespace(
            output=str(output_path),
            workflows=".github/workflows/",
        )
        result = cmd_zizmor_run(args)
        assert result == EXIT_SUCCESS
        assert output_path.exists()
        assert output_path.read_text() == EMPTY_SARIF


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
        sarif_path.write_text(json.dumps({"runs": [{"results": [{"level": "error"}]}]}))

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

    @mock.patch("cihub.commands.hub_ci.release._run_command")
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

    @mock.patch("cihub.commands.hub_ci.release._run_command")
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


class TestVerifyMatrixKeys:
    """Tests for verify-matrix-keys helper."""

    def test_verify_matrix_keys_passes(self, tmp_path: Path, monkeypatch) -> None:
        from cihub.commands import hub_ci
        from cihub.commands.hub_ci import validation
        from cihub.exit_codes import EXIT_SUCCESS

        hub = tmp_path
        (hub / ".github" / "workflows").mkdir(parents=True)
        (hub / ".github" / "workflows" / "hub-run-all.yml").write_text(
            "matrix.owner\n",
            encoding="utf-8",
        )

        # Patch hub_root in the validation module where it's used
        monkeypatch.setattr(validation, "hub_root", lambda: hub)
        result = hub_ci.cmd_verify_matrix_keys(argparse.Namespace())
        assert result == EXIT_SUCCESS

    def test_verify_matrix_keys_fails_on_missing(self, tmp_path: Path, monkeypatch) -> None:
        from cihub.commands import hub_ci
        from cihub.commands.hub_ci import validation
        from cihub.exit_codes import EXIT_FAILURE

        hub = tmp_path
        (hub / ".github" / "workflows").mkdir(parents=True)
        (hub / ".github" / "workflows" / "hub-run-all.yml").write_text(
            "matrix.missing_key\n",
            encoding="utf-8",
        )

        # Patch hub_root in the validation module where it's used
        monkeypatch.setattr(validation, "hub_root", lambda: hub)
        result = hub_ci.cmd_verify_matrix_keys(argparse.Namespace())
        assert result == EXIT_FAILURE


class TestQuarantineCheck:
    """Tests for quarantine-check helper."""

    def test_quarantine_check_passes(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_quarantine_check
        from cihub.exit_codes import EXIT_SUCCESS

        args = argparse.Namespace(path=str(tmp_path))
        result = cmd_quarantine_check(args)
        assert result == EXIT_SUCCESS

    def test_quarantine_check_fails(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_quarantine_check
        from cihub.exit_codes import EXIT_FAILURE

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from _quarantine import thing\n", encoding="utf-8")

        args = argparse.Namespace(path=str(tmp_path))
        result = cmd_quarantine_check(args)
        assert result == EXIT_FAILURE


class TestCmdRepoCheck:
    """Tests for cmd_repo_check command."""

    def test_repo_present_outputs_true(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_repo_check
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        (repo_path / ".git").mkdir(parents=True)
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            owner="owner",
            name="repo",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_repo_check(args)
        assert result == EXIT_SUCCESS
        assert "present=true" in output_path.read_text(encoding="utf-8")

    def test_repo_missing_outputs_false(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_repo_check
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            owner="owner",
            name="repo",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_repo_check(args)
        assert result == EXIT_SUCCESS
        assert "present=false" in output_path.read_text(encoding="utf-8")


class TestCmdSourceCheck:
    """Tests for cmd_source_check command."""

    def test_detects_python_source(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_source_check
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            language="python",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_source_check(args)
        assert result == EXIT_SUCCESS
        assert "has_source=true" in output_path.read_text(encoding="utf-8")

    def test_detects_java_source(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_source_check
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "App.java").write_text("class App {}", encoding="utf-8")
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            language="java",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_source_check(args)
        assert result == EXIT_SUCCESS
        assert "has_source=true" in output_path.read_text(encoding="utf-8")


class TestCmdSmokeJava:
    """Tests for smoke Java commands."""

    def test_smoke_java_tests_parses_junit(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_java_tests
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        report_dir = repo_path / "target" / "surefire-reports"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "TEST.xml"
        report_path.write_text(
            '<testsuite tests="10" failures="2" errors="1" skipped="3" time="12.5"></testsuite>',
            encoding="utf-8",
        )
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_java_tests(args)
        assert result == EXIT_SUCCESS
        content = output_path.read_text(encoding="utf-8")
        # total = passed + failed + skipped = 4 + 3 + 3 = 10
        assert "total=10" in content
        assert "passed=4" in content
        assert "failed=3" in content
        assert "skipped=3" in content

    def test_smoke_java_coverage_parses_jacoco(self, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_java_coverage
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        report_dir = repo_path / "target" / "site"
        report_dir.mkdir(parents=True)
        report_path = report_dir / "jacoco.xml"
        report_path.write_text(
            '<report><counter type="INSTRUCTION" missed="20" covered="80"/></report>',
            encoding="utf-8",
        )
        output_path = tmp_path / "outputs.txt"

        args = argparse.Namespace(
            path=str(repo_path),
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_java_coverage(args)
        assert result == EXIT_SUCCESS
        content = output_path.read_text(encoding="utf-8")
        assert "percent=80" in content
        assert "covered=80" in content
        assert "missed=20" in content


class TestCmdSmokePython:
    """Tests for smoke Python commands."""

    @mock.patch("cihub.commands.hub_ci.smoke._run_command")
    def test_smoke_python_tests_parses_output(self, mock_run: mock.Mock, tmp_path: Path) -> None:
        from cihub.commands.hub_ci import cmd_smoke_python_tests
        from cihub.exit_codes import EXIT_SUCCESS

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        coverage_file = repo_path / "coverage.xml"
        coverage_file.write_text('<coverage line-rate="0.85"></coverage>', encoding="utf-8")

        mock_run.return_value = mock.Mock(
            stdout="10 passed, 2 failed, 1 skipped",
            stderr="",
            returncode=1,
        )

        output_path = tmp_path / "outputs.txt"
        args = argparse.Namespace(
            path=str(repo_path),
            output_file="test-output.txt",
            output=str(output_path),
            github_output=False,
        )
        result = cmd_smoke_python_tests(args)
        assert result == EXIT_SUCCESS
        content = output_path.read_text(encoding="utf-8")
        # total = passed + failed + skipped = 10 + 2 + 1 = 13
        assert "total=13" in content
        assert "passed=10" in content
        assert "failed=2" in content
        assert "skipped=1" in content
        assert "coverage=85" in content


class TestCmdHubCi:
    """Tests for cmd_hub_ci main router."""

    def test_routes_to_correct_handler(self) -> None:
        from cihub.commands.hub_ci import cmd_hub_ci

        # Patch at the router module where cmd_validate_profiles is looked up
        with mock.patch("cihub.commands.hub_ci.router.cmd_validate_profiles") as mock_handler:
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
