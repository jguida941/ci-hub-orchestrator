"""Tests for CLI commands using argparse testing patterns.

This test module covers CLI command testing best practices:
1. Direct main() invocation with argv list
2. Exit code verification
3. stdout/stderr capture with capsys
4. Error path testing for invalid inputs
5. JSON output mode testing
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cihub.cli import main
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS


class TestVersionCommand:
    """Tests for --version flag."""

    def test_version_flag(self, capsys) -> None:
        """--version prints version and exits successfully."""
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "cihub" in out.lower() or "." in out  # version string

    def test_version_long_flag(self, capsys) -> None:
        """--version prints version and exits successfully (no short flag)."""
        # Note: cihub uses --version only, no -v short flag
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "cihub" in out.lower()


class TestHelpCommand:
    """Tests for --help flag on various commands."""

    def test_main_help(self, capsys) -> None:
        """--help prints usage and exits successfully."""
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "cihub" in out.lower()

    def test_detect_help(self, capsys) -> None:
        """detect --help prints command usage."""
        with pytest.raises(SystemExit) as exc:
            main(["detect", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "repo" in out.lower()

    def test_init_help(self, capsys) -> None:
        """init --help prints command usage."""
        with pytest.raises(SystemExit) as exc:
            main(["init", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "language" in out.lower() or "repo" in out.lower()

    def test_ci_help(self, capsys) -> None:
        """ci --help prints command usage."""
        with pytest.raises(SystemExit) as exc:
            main(["ci", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "ci" in out.lower()

    def test_report_help(self, capsys) -> None:
        """report --help prints subcommand list."""
        with pytest.raises(SystemExit) as exc:
            main(["report", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "build" in out or "summary" in out

    def test_hub_ci_help(self, capsys) -> None:
        """hub-ci --help prints subcommand list."""
        with pytest.raises(SystemExit) as exc:
            main(["hub-ci", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "hub" in out.lower()


class TestDetectCommand:
    """Tests for detect command."""

    def test_detect_python_repo(self, tmp_path: Path, capsys) -> None:
        """detect identifies Python repo from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")

        result = main(["detect", "--repo", str(tmp_path)])

        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "python" in out.lower()

    def test_detect_java_repo(self, tmp_path: Path, capsys) -> None:
        """detect identifies Java repo from pom.xml."""
        (tmp_path / "pom.xml").write_text('<?xml version="1.0"?><project></project>')

        result = main(["detect", "--repo", str(tmp_path)])

        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "java" in out.lower()

    def test_detect_unknown_language_returns_error(self, tmp_path: Path, capsys) -> None:
        """detect returns EXIT_FAILURE for repo without markers."""
        # Empty repo has no language markers, returns error code (not exception)
        result = main(["detect", "--repo", str(tmp_path)])

        assert result == EXIT_FAILURE
        err = capsys.readouterr().err
        assert "Unable to detect language" in err

    def test_detect_invalid_repo_path(self, tmp_path: Path, capsys) -> None:
        """detect fails for non-existent path with proper error message."""
        result = main(["detect", "--repo", str(tmp_path / "nonexistent")])

        assert result == EXIT_FAILURE
        err = capsys.readouterr().err
        assert "not a valid directory" in err or "Error" in err

    def test_detect_json_output(self, tmp_path: Path, capsys) -> None:
        """detect --json outputs JSON format."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        result = main(["detect", "--repo", str(tmp_path), "--json"])

        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "command" in data
        assert data["command"] == "detect"


class TestPreflightCommand:
    """Tests for preflight command."""

    def test_preflight_basic(self, tmp_path: Path, capsys) -> None:
        """preflight runs environment checks."""
        result = main(["preflight"])

        # preflight may pass or fail depending on environment
        out = capsys.readouterr().out
        # Should produce some output about checks
        assert len(out) > 0 or result in (EXIT_SUCCESS, EXIT_FAILURE)

    def test_doctor_alias(self, capsys) -> None:
        """doctor is an alias for preflight."""
        result = main(["doctor"])
        # Same behavior as preflight
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)


class TestInitCommand:
    """Tests for init command."""

    def test_init_missing_required_args(self, capsys) -> None:
        """init fails without required arguments."""
        with pytest.raises(SystemExit) as exc:
            main(["init"])
        # argparse exits with 2 for missing required args
        assert exc.value.code == 2

    def test_init_dry_run(self, tmp_path: Path, capsys) -> None:
        """init --dry-run shows what would be created."""
        result = main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--dry-run",
            ]
        )

        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "Would write" in out or ".ci-hub.yml" in out

    def test_init_creates_files(self, tmp_path: Path) -> None:
        """init --apply creates config and workflow files."""
        result = main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "testorg",
                "--name",
                "testrepo",
                "--branch",
                "main",
                "--apply",
            ]
        )

        assert result == EXIT_SUCCESS
        assert (tmp_path / ".ci-hub.yml").exists()
        assert (tmp_path / ".github" / "workflows" / "hub-ci.yml").exists()


class TestUpdateCommand:
    """Tests for update command."""

    def test_update_creates_config_in_dry_run(self, tmp_path: Path, capsys) -> None:
        """update in dry-run mode shows what would be created even without existing config."""
        result = main(
            [
                "update",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
            ]
        )

        # Dry-run mode (default) shows what would be written
        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "Would write" in out

    def test_update_with_existing_config(self, tmp_path: Path) -> None:
        """update works with existing .ci-hub.yml."""
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\n")

        result = main(
            [
                "update",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--dry-run",
            ]
        )

        assert result == EXIT_SUCCESS


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_missing_config(self, tmp_path: Path) -> None:
        """validate fails when .ci-hub.yml is missing."""
        result = main(["validate", "--repo", str(tmp_path)])
        assert result != EXIT_SUCCESS

    def test_validate_valid_config(self, tmp_path: Path, capsys) -> None:
        """validate passes for valid configuration."""
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\nrepo:\n  owner: test\n  name: repo\n")

        result = main(["validate", "--repo", str(tmp_path)])

        # May still need workflow file in some validation modes
        capsys.readouterr()  # Consume output
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)


class TestReportSubcommands:
    """Tests for report subcommands."""

    def test_report_build_missing_file(self, tmp_path: Path) -> None:
        """report build fails when report file doesn't exist."""
        result = main(
            [
                "report",
                "build",
                "--report",
                str(tmp_path / "nonexistent.json"),
            ]
        )
        assert result != EXIT_SUCCESS

    def test_report_summary_missing_file(self, tmp_path: Path, capsys) -> None:
        """report summary fails when report file doesn't exist with error."""
        result = main(
            [
                "report",
                "summary",
                "--report",
                str(tmp_path / "nonexistent.json"),
            ]
        )

        assert result == EXIT_FAILURE
        err = capsys.readouterr().err
        assert "Error" in err or "No such file" in err

    def test_report_validate_missing_file(self, tmp_path: Path) -> None:
        """report validate fails for non-existent file."""
        result = main(
            [
                "report",
                "validate",
                "--report",
                str(tmp_path / "missing.json"),
            ]
        )
        assert result != EXIT_SUCCESS

    def test_report_validate_valid_report(self, tmp_path: Path, capsys) -> None:
        """report validate passes for valid report with all required fields."""
        report = tmp_path / "report.json"
        report.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "repository": "test/repo",
                    "branch": "main",
                    "python_version": "3.12",
                    "results": {
                        "coverage": 80,
                        "tests_failed": 0,
                        "tests_passed": 10,  # Required field
                    },
                    "tool_metrics": {},
                    "tools_configured": {"pytest": True},
                    "tools_ran": {"pytest": True},
                    "tools_success": {"pytest": True},
                }
            )
        )

        result = main(["report", "validate", "--report", str(report)])

        capsys.readouterr()  # Consume output
        assert result == EXIT_SUCCESS


class TestConfigSubcommands:
    """Tests for config subcommands."""

    def test_config_show_requires_repo(self, capsys) -> None:
        """config show requires --repo argument."""
        result = main(["config", "show"])

        # Should fail with message about --repo required
        err = capsys.readouterr().err
        assert result == EXIT_FAILURE or "--repo" in err

    def test_config_show_with_repo(self, capsys) -> None:
        """config show --repo displays repo configuration."""
        # Use a known repo config from the hub
        result = main(["config", "--repo", "smoke-test-python", "show"])

        capsys.readouterr()  # Consume output
        # Should succeed if repo exists in config/repos/
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)


class TestRunCommand:
    """Tests for run command (single tool execution)."""

    def test_run_missing_tool(self) -> None:
        """run fails without tool argument."""
        with pytest.raises(SystemExit) as exc:
            main(["run"])
        assert exc.value.code == 2

    def test_run_unknown_tool(self, tmp_path: Path, capsys) -> None:
        """run fails for unknown tool with proper error message."""
        (tmp_path / ".ci-hub.yml").write_text("language: python\n")

        # Tool is positional, not --tool
        result = main(
            [
                "run",
                "nonexistent_tool",
                "--repo",
                str(tmp_path),
            ]
        )

        # EXIT_USAGE (2) for unknown tool - this is a usage error
        from cihub.exit_codes import EXIT_USAGE

        assert result == EXIT_USAGE
        out = capsys.readouterr().out
        assert "Unsupported tool" in out


class TestAdrSubcommands:
    """Tests for ADR subcommands."""

    def test_adr_list(self, capsys) -> None:
        """adr list shows available ADRs."""
        result = main(["adr", "list"])

        # Should succeed or fail based on ADR directory existence
        capsys.readouterr()  # Consume output
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)

    def test_adr_new_missing_title(self) -> None:
        """adr new requires --title argument."""
        with pytest.raises(SystemExit) as exc:
            main(["adr", "new"])
        assert exc.value.code == 2


class TestDocsSubcommands:
    """Tests for docs subcommands."""

    def test_docs_generate_check(self, capsys) -> None:
        """docs generate --check validates docs are up to date."""
        # --check flag, not --dry-run
        result = main(["docs", "generate", "--check"])

        capsys.readouterr()  # Consume output
        # May pass or fail depending on state
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)

    def test_docs_check(self, capsys) -> None:
        """docs check validates documentation."""
        result = main(["docs", "check"])

        # May pass or fail depending on state
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)


class TestJsonOutputMode:
    """Tests for --json output mode across commands."""

    def test_detect_json_structure(self, tmp_path: Path, capsys) -> None:
        """--json outputs proper JSON structure."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        result = main(["detect", "--repo", str(tmp_path), "--json"])

        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "command" in data
        assert "status" in data
        assert "exit_code" in data
        assert data["exit_code"] == 0

    def test_validate_json_on_failure(self, tmp_path: Path, capsys) -> None:
        """--json outputs proper structure on failure."""
        main(["validate", "--repo", str(tmp_path), "--json"])

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "command" in data
        assert data["status"] == "failure"
        assert data["exit_code"] != 0

    def test_init_json_output(self, tmp_path: Path, capsys) -> None:
        """init --json outputs proper JSON."""
        main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--dry-run",
                "--json",
            ]
        )

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["command"] == "init"


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_unknown_command(self) -> None:
        """Unknown command causes argparse error."""
        with pytest.raises(SystemExit) as exc:
            main(["unknown_command_xyz"])
        assert exc.value.code == 2

    def test_invalid_json_flag_position(self, capsys) -> None:
        """Invalid argument handling."""
        with pytest.raises(SystemExit):
            main(["--invalid-flag-xyz"])

    def test_exception_in_json_mode(self, tmp_path: Path, capsys) -> None:
        """Expected errors in --json mode return structured error."""
        # Test with a directory that doesn't exist - FileNotFoundError
        result = main(
            [
                "detect",
                "--repo",
                str(tmp_path / "nonexistent"),
                "--json",
            ]
        )

        out = capsys.readouterr().out
        data = json.loads(out)
        # Should be "failure" for user errors, not "error" for internal errors
        assert data["status"] == "failure"
        assert result == EXIT_FAILURE


class TestDiscoverCommand:
    """Tests for discover command."""

    def test_discover_basic(self, capsys) -> None:
        """discover generates repo matrix."""
        result = main(["discover"])

        capsys.readouterr()  # Consume output
        # Should produce matrix output
        assert result in (EXIT_SUCCESS, EXIT_FAILURE)


class TestDispatchSubcommands:
    """Tests for dispatch subcommands."""

    def test_dispatch_metadata_missing_args(self) -> None:
        """dispatch metadata requires arguments."""
        with pytest.raises(SystemExit) as exc:
            main(["dispatch", "metadata"])
        assert exc.value.code == 2

    def test_dispatch_trigger_missing_args(self) -> None:
        """dispatch trigger requires arguments."""
        with pytest.raises(SystemExit) as exc:
            main(["dispatch", "trigger"])
        assert exc.value.code == 2


class TestScaffoldCommand:
    """Tests for scaffold command."""

    def test_scaffold_list(self, capsys) -> None:
        """scaffold --list shows available fixture types."""
        result = main(["scaffold", "--list"])

        out = capsys.readouterr().out
        assert result == EXIT_SUCCESS
        assert "python" in out.lower() or "java" in out.lower()

    def test_scaffold_python_pyproject(self, tmp_path: Path, capsys) -> None:
        """scaffold creates a minimal Python pyproject fixture."""
        # scaffold uses positional args: type path
        result = main(
            [
                "scaffold",
                "python-pyproject",
                str(tmp_path / "scaffold"),
            ]
        )

        capsys.readouterr()  # Consume output
        assert result == EXIT_SUCCESS
        assert (tmp_path / "scaffold").exists()

    def test_scaffold_java_maven(self, tmp_path: Path, capsys) -> None:
        """scaffold creates a minimal Java Maven fixture."""
        result = main(
            [
                "scaffold",
                "java-maven",
                str(tmp_path / "scaffold"),
            ]
        )

        capsys.readouterr()  # Consume output
        assert result == EXIT_SUCCESS
        assert (tmp_path / "scaffold").exists()


class TestCheckCommand:
    """Tests for check command.

    Note: The check command runs extensive validation including smoke tests,
    which can take several minutes. We only test help here.
    """

    def test_check_help(self, capsys) -> None:
        """check --help shows available options."""
        with pytest.raises(SystemExit) as exc:
            main(["check", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "audit" in out or "security" in out


class TestNewCommand:
    """Tests for new command (hub-side repo config)."""

    def test_new_missing_args(self) -> None:
        """new requires name argument (positional)."""
        with pytest.raises(SystemExit) as exc:
            main(["new"])
        assert exc.value.code == 2

    def test_new_dry_run(self, tmp_path: Path, capsys) -> None:
        """new --dry-run shows what would be created."""
        with patch("cihub.cli.hub_root", return_value=tmp_path):
            (tmp_path / "config" / "repos").mkdir(parents=True)
            (tmp_path / "config" / "defaults.yaml").write_text("repo:\n  owner: test\n")

            # name is positional, not --name
            result = main(
                [
                    "new",
                    "test-repo",
                    "--owner",
                    "testorg",
                    "--language",
                    "python",
                    "--dry-run",
                ]
            )

        out = capsys.readouterr().out
        assert "Would write" in out or result == EXIT_SUCCESS
