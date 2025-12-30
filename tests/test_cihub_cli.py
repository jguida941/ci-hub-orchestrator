import json
import sys
import urllib.request
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import (  # noqa: E402
    build_repo_config,
    detect_language,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
    render_caller_workflow,
    render_dispatch_workflow,
    safe_urlopen,
    validate_repo_path,
    validate_subdir,
)


def test_parse_repo_from_remote_https():
    owner, name = parse_repo_from_remote("https://github.com/acme/example.git")
    assert owner == "acme"
    assert name == "example"


def test_parse_repo_from_remote_ssh():
    owner, name = parse_repo_from_remote("git@github.com:acme/example.git")
    assert owner == "acme"
    assert name == "example"


def test_detect_language_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    language, reasons = detect_language(tmp_path)
    assert language == "python"
    assert "pyproject.toml" in reasons


def test_detect_language_java(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    language, reasons = detect_language(tmp_path)
    assert language == "java"
    assert "pom.xml" in reasons


def test_build_repo_config_prunes_other_language():
    config = build_repo_config("python", "acme", "repo", "main")
    assert config["language"] == "python"
    assert "python" in config
    assert "java" not in config
    assert config["repo"]["dispatch_workflow"] == "hub-ci.yml"


def test_build_repo_config_sets_subdir():
    config = build_repo_config("java", "acme", "repo", "main", subdir="services/app")
    assert config["repo"]["subdir"] == "services/app"


def test_render_caller_workflow_renames_target():
    content = render_caller_workflow("python")
    assert "hub-ci.yml" in content
    assert "hub-python-ci.yml" not in content


def test_render_dispatch_workflow_hub_ci_requires_language():
    try:
        render_dispatch_workflow("", "hub-ci.yml")
    except ValueError as exc:
        assert "language is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing language")


def test_render_dispatch_workflow_java_template():
    content = render_dispatch_workflow("java", "hub-java-ci.yml")
    assert "uses: jguida941/ci-cd-hub/.github/workflows/hub-ci.yml@main" in content
    assert "secrets: inherit" in content


def test_render_dispatch_workflow_hub_ci_renders_caller():
    content = render_dispatch_workflow("python", "hub-ci.yml")
    assert "hub-ci.yml" in content
    assert "hub-python-ci.yml" not in content


def test_render_dispatch_workflow_rejects_unknown():
    try:
        render_dispatch_workflow("python", "hub-ruby-ci.yml")
    except ValueError as exc:
        assert "Unsupported dispatch_workflow" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported workflow")


# =============================================================================
# Security Function Tests
# =============================================================================


class TestValidateRepoPath:
    """Tests for validate_repo_path security function."""

    def test_valid_directory_returns_resolved_path(self, tmp_path: Path) -> None:
        """Valid directory path returns the resolved path."""
        result = validate_repo_path(tmp_path)
        assert result == tmp_path.resolve()
        assert result.is_absolute()

    def test_nonexistent_path_raises_value_error(self) -> None:
        """Non-existent path raises ValueError."""
        fake_path = Path("/nonexistent/path/that/does/not/exist")
        with pytest.raises(ValueError, match="not a valid directory"):
            validate_repo_path(fake_path)

    def test_file_instead_of_directory_raises_value_error(self, tmp_path: Path) -> None:
        """File path (not directory) raises ValueError."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test content")
        with pytest.raises(ValueError, match="not a valid directory"):
            validate_repo_path(file_path)

    def test_resolves_symlinks(self, tmp_path: Path) -> None:
        """Symlinks are resolved to their target."""
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()
        symlink_path = tmp_path / "symlink"
        symlink_path.symlink_to(real_dir)

        result = validate_repo_path(symlink_path)
        assert result == real_dir.resolve()

    def test_relative_path_becomes_absolute(self, tmp_path: Path, monkeypatch) -> None:
        """Relative paths are resolved to absolute."""
        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = validate_repo_path(Path("subdir"))
        assert result.is_absolute()
        assert result == subdir.resolve()


class TestValidateSubdir:
    """Tests for validate_subdir security function."""

    @pytest.mark.parametrize(
        "subdir",
        [
            "src",
            "services/app",
            "path/to/module",
            "a/b/c/d",
            "my-service",
            "my_service",
        ],
    )
    def test_valid_subdirs_return_unchanged(self, subdir: str) -> None:
        """Valid subdirectory paths return unchanged."""
        result = validate_subdir(subdir)
        assert result == subdir

    def test_empty_string_returns_empty(self) -> None:
        """Empty string returns empty string."""
        result = validate_subdir("")
        assert result == ""

    def test_none_like_empty_returns_unchanged(self) -> None:
        """Falsy values return unchanged."""
        result = validate_subdir("")
        assert result == ""

    @pytest.mark.parametrize(
        "subdir",
        [
            "..",
            "../escape",
            "foo/../bar",
            "foo/bar/../../../escape",
            "path/to/../../etc/passwd",
        ],
    )
    def test_path_traversal_raises_value_error(self, subdir: str) -> None:
        """Path traversal attempts raise ValueError."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_subdir(subdir)

    @pytest.mark.parametrize(
        "subdir",
        [
            "/absolute/path",
            "/etc/passwd",
            "/",
        ],
    )
    def test_absolute_path_raises_value_error(self, subdir: str) -> None:
        """Absolute paths raise ValueError."""
        with pytest.raises(ValueError, match="relative path"):
            validate_subdir(subdir)

    def test_dot_in_name_is_allowed(self) -> None:
        """Single dots in directory names are allowed."""
        result = validate_subdir("my.service/app")
        assert result == "my.service/app"

    def test_dotdot_in_component_blocked(self) -> None:
        """Double dots as path component blocked."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_subdir("foo/..bar/../baz")


class TestSafeUrlopen:
    """Tests for safe_urlopen security function."""

    def test_https_url_allowed(self) -> None:
        """HTTPS URLs are allowed."""
        req = urllib.request.Request("https://api.github.com/user")
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = mock.Mock()
            safe_urlopen(req, timeout=10)
            mock_urlopen.assert_called_once()

    def test_http_url_blocked(self) -> None:
        """HTTP URLs are blocked."""
        req = urllib.request.Request("http://api.github.com/user")
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            safe_urlopen(req, timeout=10)

    def test_ftp_url_blocked(self) -> None:
        """FTP URLs are blocked."""
        req = urllib.request.Request("ftp://files.example.com/file.txt")  # noqa: S310
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            safe_urlopen(req, timeout=10)

    def test_file_url_blocked(self) -> None:
        """File URLs are blocked."""
        req = urllib.request.Request("file:///etc/passwd")  # noqa: S310
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            safe_urlopen(req, timeout=10)


# =============================================================================
# Git Function Tests
# =============================================================================


class TestGetGitRemote:
    """Tests for get_git_remote function."""

    def test_returns_remote_url(self, tmp_path: Path) -> None:
        """Returns git remote URL on success."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    stdout="https://github.com/owner/repo.git\n",
                    returncode=0,
                )
                result = get_git_remote(tmp_path)
                assert result == "https://github.com/owner/repo.git"

    def test_returns_none_on_subprocess_error(self, tmp_path: Path) -> None:
        """Returns None when subprocess fails."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError()
                result = get_git_remote(tmp_path)
                assert result is None

    def test_returns_none_on_value_error(self, tmp_path: Path) -> None:
        """Returns None when validation fails."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.side_effect = ValueError("invalid path")
            result = get_git_remote(tmp_path)
            assert result is None

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """Strips trailing whitespace from output."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    stdout="  https://github.com/owner/repo.git  \n",
                    returncode=0,
                )
                result = get_git_remote(tmp_path)
                assert result == "https://github.com/owner/repo.git"

    def test_returns_none_for_empty_output(self, tmp_path: Path) -> None:
        """Returns None when git returns empty output."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    stdout="   \n",
                    returncode=0,
                )
                result = get_git_remote(tmp_path)
                assert result is None


class TestGetGitBranch:
    """Tests for get_git_branch function."""

    def test_returns_branch_name(self, tmp_path: Path) -> None:
        """Returns current branch name on success."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    stdout="main\n",
                    returncode=0,
                )
                result = get_git_branch(tmp_path)
                assert result == "main"

    def test_returns_none_on_error(self, tmp_path: Path) -> None:
        """Returns None when subprocess fails."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError()
                result = get_git_branch(tmp_path)
                assert result is None

    def test_feature_branch_name(self, tmp_path: Path) -> None:
        """Returns feature branch names correctly."""
        with mock.patch("cihub.cli.validate_repo_path") as mock_validate:
            mock_validate.return_value = tmp_path
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    stdout="feature/add-new-feature\n",
                    returncode=0,
                )
                result = get_git_branch(tmp_path)
                assert result == "feature/add-new-feature"


# =============================================================================
# Main Function Tests (cli.py lines 1335-1389)
# =============================================================================

from cihub.cli import CommandResult, main  # noqa: E402


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = CommandResult()
        assert result.exit_code == 0
        assert result.summary == ""
        assert result.problems == []
        assert result.suggestions == []
        assert result.files_generated == []
        assert result.files_modified == []
        assert result.artifacts == {}
        assert result.data == {}

    def test_custom_values(self):
        """Custom values are preserved."""
        result = CommandResult(
            exit_code=1,
            summary="Test failed",
            problems=[{"message": "error"}],
        )
        assert result.exit_code == 1
        assert result.summary == "Test failed"
        assert result.problems == [{"message": "error"}]

    def test_to_payload_structure(self):
        """to_payload returns correct structure."""
        result = CommandResult(
            exit_code=0,
            summary="Success",
            problems=[],
            artifacts={"file": "test.txt"},
        )
        payload = result.to_payload("test-cmd", "success", 100)

        assert payload["command"] == "test-cmd"
        assert payload["status"] == "success"
        assert payload["exit_code"] == 0
        assert payload["duration_ms"] == 100
        assert payload["summary"] == "Success"
        assert payload["artifacts"] == {"file": "test.txt"}


class TestMainFunction:
    """Tests for main() function (lines 1335-1389)."""

    def test_main_with_help_flag(self):
        """Main exits with help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_main_with_version_flag(self):
        """Main exits with version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_main_no_command_shows_help(self, capsys):
        """Main with no command shows help."""
        with pytest.raises(SystemExit):
            main([])

    def test_main_json_output_on_success(self, capsys):
        """Main outputs JSON when --json flag is used with successful command."""
        # Mock cmd_config which handles all config subcommands
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = CommandResult(
                exit_code=0,
                summary="Config shown",
            )
            result = main(["config", "--repo", "test", "show", "--json"])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "success"
        assert output["exit_code"] == 0

    def test_main_json_output_on_failure(self, capsys):
        """Main outputs JSON when --json flag is used with failed command."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = CommandResult(
                exit_code=1,
                summary="Config not found",
                problems=[{"message": "File not found", "severity": "error"}],
            )
            result = main(["config", "--repo", "nonexistent", "show", "--json"])

        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "failure"
        assert output["exit_code"] == 1
        assert len(output["problems"]) == 1

    def test_main_json_output_on_exception(self, capsys):
        """Main outputs JSON error on unhandled exception."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.side_effect = RuntimeError("Unexpected error")
            result = main(["config", "--repo", "test", "show", "--json"])

        assert result != 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "Unexpected error" in output["summary"]

    def test_main_exception_without_json_raises(self):
        """Main re-raises exception when not in JSON mode."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.side_effect = RuntimeError("Test error")
            with pytest.raises(RuntimeError, match="Test error"):
                main(["config", "--repo", "test", "show"])

    def test_main_sets_default_summary_on_success(self, capsys):
        """Main sets 'OK' summary when command returns success without summary."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = CommandResult(exit_code=0)
            main(["config", "--repo", "test", "show", "--json"])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"] == "OK"

    def test_main_sets_default_summary_on_failure(self, capsys):
        """Main sets failure summary when command returns failure without summary."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = CommandResult(exit_code=1)
            main(["config", "--repo", "test", "show", "--json"])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"] == "Command failed"

    def test_main_handles_int_return(self, capsys):
        """Main handles commands that return int instead of CommandResult."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = 0  # Return int instead of CommandResult
            result = main(["config", "--repo", "test", "show", "--json"])

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["exit_code"] == 0

    def test_main_includes_duration(self, capsys):
        """Main includes duration_ms in JSON output."""
        with mock.patch("cihub.cli.cmd_config") as mock_cmd:
            mock_cmd.return_value = CommandResult(exit_code=0)
            main(["config", "--repo", "test", "show", "--json"])

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "duration_ms" in output
        assert isinstance(output["duration_ms"], int)
        assert output["duration_ms"] >= 0
