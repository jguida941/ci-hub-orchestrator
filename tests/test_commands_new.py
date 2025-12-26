"""Tests for commands/new.py."""

from __future__ import annotations

# isort: skip_file

import argparse
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.new import (  # isort: skip # noqa: E402
    _apply_repo_defaults,
    _validate_profile_language,
    cmd_new,
)
from cihub.config.paths import PathConfig  # noqa: E402


# =============================================================================
# Helper Functions
# =============================================================================


@pytest.fixture
def hub_paths(tmp_path: Path) -> PathConfig:
    """Create a PathConfig pointing to a temp hub directory."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    # Profiles are under templates/profiles
    profiles_dir = tmp_path / "templates" / "profiles"
    profiles_dir.mkdir(parents=True)

    # Create defaults.yaml
    defaults_file = config_dir / "defaults.yaml"
    defaults_file.write_text(
        "repo:\n  use_central_runner: true\n  dispatch_workflow: hub-ci.yml\n"
    )

    return PathConfig(str(tmp_path))


@pytest.fixture
def base_args() -> argparse.Namespace:
    """Create base arguments for cmd_new."""
    return argparse.Namespace(
        name="owner/repo",
        owner="owner",
        language="python",
        branch="main",
        subdir=None,
        profile=None,
        interactive=False,
        dry_run=False,
        yes=True,
        json=False,
    )


# =============================================================================
# _apply_repo_defaults Tests
# =============================================================================


class TestApplyRepoDefaults:
    """Tests for _apply_repo_defaults helper function."""

    def test_applies_use_central_runner(self) -> None:
        """Applies use_central_runner from defaults."""
        config = {"language": "python", "repo": {"owner": "test"}}
        defaults = {"repo": {"use_central_runner": True}}
        result = _apply_repo_defaults(config, defaults)
        assert result["repo"]["use_central_runner"] is True
        assert result["repo"]["owner"] == "test"

    def test_applies_repo_side_execution(self) -> None:
        """Applies repo_side_execution from defaults."""
        config = {"language": "python", "repo": {}}
        defaults = {"repo": {"repo_side_execution": False}}
        result = _apply_repo_defaults(config, defaults)
        assert result["repo"]["repo_side_execution"] is False

    def test_does_not_override_existing_values(self) -> None:
        """Does not override values already in config."""
        config = {"repo": {"use_central_runner": False}}
        defaults = {"repo": {"use_central_runner": True}}
        result = _apply_repo_defaults(config, defaults)
        assert result["repo"]["use_central_runner"] is False

    def test_handles_missing_repo_block(self) -> None:
        """Handles config with no repo block."""
        config = {"language": "python"}
        defaults = {"repo": {"use_central_runner": True}}
        result = _apply_repo_defaults(config, defaults)
        assert result["repo"]["use_central_runner"] is True

    def test_handles_empty_defaults(self) -> None:
        """Handles empty defaults dict."""
        config = {"language": "python", "repo": {"owner": "test"}}
        result = _apply_repo_defaults(config, {})
        assert result["repo"]["owner"] == "test"

    def test_handles_non_dict_defaults(self) -> None:
        """Handles non-dict defaults gracefully."""
        config = {"language": "python", "repo": {}}
        result = _apply_repo_defaults(config, None)
        assert "repo" in result


# =============================================================================
# _validate_profile_language Tests
# =============================================================================


class TestValidateProfileLanguage:
    """Tests for _validate_profile_language helper function."""

    def test_empty_profile_passes(self) -> None:
        """Empty profile passes validation."""
        _validate_profile_language({}, "python")  # should not raise
        _validate_profile_language(None, "python")  # should not raise

    def test_java_profile_with_java_language(self) -> None:
        """Java profile with java language passes."""
        profile = {"java": {"tools": {"jacoco": {"enabled": True}}}}
        _validate_profile_language(profile, "java")  # should not raise

    def test_python_profile_with_python_language(self) -> None:
        """Python profile with python language passes."""
        profile = {"python": {"tools": {"ruff": {"enabled": True}}}}
        _validate_profile_language(profile, "python")  # should not raise

    def test_java_profile_with_python_language_raises(self) -> None:
        """Java profile with python language raises ValueError."""
        profile = {"java": {"tools": {"jacoco": {"enabled": True}}}}
        with pytest.raises(ValueError, match="Java-only"):
            _validate_profile_language(profile, "python")

    def test_python_profile_with_java_language_raises(self) -> None:
        """Python profile with java language raises ValueError."""
        profile = {"python": {"tools": {"ruff": {"enabled": True}}}}
        with pytest.raises(ValueError, match="Python-only"):
            _validate_profile_language(profile, "java")

    def test_profile_with_no_language_keys(self) -> None:
        """Profile without java/python keys passes for any language."""
        profile = {"thresholds": {"coverage_min": 80}}
        _validate_profile_language(profile, "java")  # should not raise
        _validate_profile_language(profile, "python")  # should not raise


# =============================================================================
# cmd_new Tests
# =============================================================================


class TestCmdNew:
    """Tests for cmd_new command handler."""

    def test_creates_repo_config_file(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Creates repo config file successfully."""
        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 0
            repo_file = Path(hub_paths.repo_file("owner/repo"))
            assert repo_file.exists()
            content = repo_file.read_text()
            assert "language: python" in content

    def test_existing_config_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Fails when config already exists."""
        # Create existing config (need to create parent directory first)
        repo_file = Path(hub_paths.repo_file("owner/repo"))
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_text("language: python\n")

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 2

    def test_dry_run_does_not_create_file(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Dry run does not create the config file."""
        base_args.dry_run = True

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 0
            repo_file = Path(hub_paths.repo_file("owner/repo"))
            assert not repo_file.exists()

    def test_missing_owner_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Fails when owner is missing in non-interactive mode."""
        base_args.owner = None

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 2

    def test_missing_language_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Fails when language is missing in non-interactive mode."""
        base_args.language = None

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 2

    def test_json_mode_with_interactive_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """JSON mode with interactive flag fails."""
        base_args.json = True
        base_args.interactive = True

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            # Returns CommandResult object with exit_code=2
            assert result.exit_code == 2
            assert "interactive" in result.summary.lower()

    def test_json_mode_dry_run_returns_command_result(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """JSON mode dry run returns CommandResult."""
        base_args.json = True
        base_args.dry_run = True

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result.exit_code == 0
            assert "config" in result.data
            assert result.files_generated

    def test_sets_subdir_when_provided(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Sets subdir in config when provided."""
        base_args.subdir = "services/api"

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 0
            repo_file = Path(hub_paths.repo_file("owner/repo"))
            content = repo_file.read_text()
            assert "subdir: services/api" in content

    def test_applies_profile_when_provided(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Applies profile settings when profile is provided."""
        # Create a profile file in templates/profiles (where PathConfig expects it)
        profile_file = Path(hub_paths.root) / "templates" / "profiles" / "strict.yaml"
        profile_file.write_text("python:\n  tools:\n    ruff:\n      enabled: true\n")
        base_args.profile = "strict"

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 0
            repo_file = Path(hub_paths.repo_file("owner/repo"))
            content = repo_file.read_text()
            assert "ruff" in content

    def test_missing_profile_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Fails when specified profile does not exist."""
        base_args.profile = "nonexistent"

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 2

    def test_profile_language_mismatch_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Fails when profile language doesn't match specified language."""
        # Create a Java-only profile in templates/profiles
        profile_file = (
            Path(hub_paths.root) / "templates" / "profiles" / "java-only.yaml"
        )
        profile_file.write_text("java:\n  tools:\n    jacoco:\n      enabled: true\n")
        base_args.profile = "java-only"
        base_args.language = "python"  # Mismatch!

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            with pytest.raises(ValueError, match="Java-only"):
                cmd_new(base_args)

    def test_confirmation_required_in_json_mode(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """JSON mode without --yes returns error about confirmation."""
        base_args.json = True
        base_args.yes = False

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result.exit_code == 2
            assert "confirmation" in result.summary.lower() or "--yes" in result.summary

    def test_creates_java_config(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Creates Java language config successfully."""
        base_args.language = "java"

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert result == 0
            repo_file = Path(hub_paths.repo_file("owner/repo"))
            content = repo_file.read_text()
            assert "language: java" in content

    def test_existing_config_json_mode_fails(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """JSON mode fails when config already exists."""
        from cihub.cli import CommandResult

        # Create existing config
        repo_file = Path(hub_paths.repo_file("owner/repo"))
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_text("language: python\n")

        base_args.json = True

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert isinstance(result, CommandResult)
            assert result.exit_code == 2
            assert "already exists" in result.summary

    def test_json_mode_success_after_write(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """JSON mode returns CommandResult after successful write."""
        from cihub.cli import CommandResult

        base_args.json = True
        base_args.yes = True
        base_args.dry_run = False

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            result = cmd_new(base_args)

            assert isinstance(result, CommandResult)
            assert result.exit_code == 0
            assert "created" in result.summary.lower()
            assert "config" in result.data
            assert result.files_generated

    def test_interactive_without_wizard_deps(
        self, hub_paths: PathConfig, base_args: argparse.Namespace
    ) -> None:
        """Interactive mode without wizard deps fails."""
        base_args.interactive = True

        with mock.patch("cihub.commands.new.hub_root") as mock_hub_root:
            mock_hub_root.return_value = Path(hub_paths.root)

            with mock.patch("cihub.commands.new.HAS_WIZARD", False):
                result = cmd_new(base_args)

                assert result == 1
