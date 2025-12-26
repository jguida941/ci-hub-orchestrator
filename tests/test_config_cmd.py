"""Tests for cihub.commands.config_cmd module.

These tests cover the config subcommand handlers:
- show: Display raw or effective config
- set: Set a config value by path
- enable/disable: Toggle tool enabled status
- edit: Interactive wizard editing (mocked)

All file operations use tmp_path fixture.
External dependencies (wizard, io, merge) are mocked as appropriate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.config_cmd import (  # noqa: E402
    ConfigError,
    _dump_config,
    _load_repo,
    _resolve_tool_path,
    _set_nested,
    cmd_config,
)
from cihub.config.paths import PathConfig  # noqa: E402

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def hub_paths(tmp_path: Path) -> PathConfig:
    """Create a PathConfig pointing to a temp hub directory."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text(
        yaml.safe_dump(
            {
                "java": {
                    "version": "21",
                    "tools": {
                        "jacoco": {"enabled": True},
                        "checkstyle": {"enabled": True},
                    },
                },
                "python": {
                    "version": "3.12",
                    "tools": {
                        "pytest": {"enabled": True},
                        "ruff": {"enabled": True},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return PathConfig(str(tmp_path))


@pytest.fixture
def sample_repo_config() -> dict[str, Any]:
    """Return a sample repo config."""
    return {
        "repo": {
            "owner": "testowner",
            "name": "testrepo",
            "language": "python",
            "default_branch": "main",
        },
        "language": "python",
        "python": {
            "version": "3.12",
            "tools": {
                "pytest": {"enabled": True},
                "ruff": {"enabled": True},
            },
        },
    }


@pytest.fixture
def java_repo_config() -> dict[str, Any]:
    """Return a sample Java repo config."""
    return {
        "repo": {
            "owner": "testowner",
            "name": "javarepo",
            "language": "java",
            "default_branch": "main",
        },
        "language": "java",
        "java": {
            "version": "21",
            "tools": {
                "jacoco": {"enabled": True},
                "checkstyle": {"enabled": True},
            },
        },
    }


def write_repo_config(paths: PathConfig, repo: str, config: dict[str, Any]) -> None:
    """Write a repo config to the paths."""
    repo_path = Path(paths.repo_file(repo))
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.write_text(yaml.safe_dump(config), encoding="utf-8")


# ==============================================================================
# Tests for _load_repo helper
# ==============================================================================


class TestLoadRepo:
    """Tests for the _load_repo helper function."""

    def test_load_repo_success(
        self, hub_paths: PathConfig, sample_repo_config: dict[str, Any]
    ) -> None:
        """Load an existing repo config."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        config = _load_repo(hub_paths, "testrepo")
        assert config["repo"]["owner"] == "testowner"
        assert config["language"] == "python"

    def test_load_repo_not_found(self, hub_paths: PathConfig) -> None:
        """Raise ConfigError when repo not found."""
        with pytest.raises(ConfigError, match="Repo config not found"):
            _load_repo(hub_paths, "nonexistent")

    def test_load_repo_empty_config(self, hub_paths: PathConfig) -> None:
        """Raise ConfigError when repo config is empty."""
        repo_path = Path(hub_paths.repo_file("emptyrepo"))
        repo_path.write_text("", encoding="utf-8")
        with pytest.raises(ConfigError, match="Repo config is empty"):
            _load_repo(hub_paths, "emptyrepo")


# ==============================================================================
# Tests for _set_nested helper
# ==============================================================================


class TestSetNested:
    """Tests for the _set_nested helper function."""

    def test_set_nested_simple(self) -> None:
        """Set a simple top-level key."""
        config: dict[str, Any] = {}
        _set_nested(config, "key", "value")
        assert config["key"] == "value"

    def test_set_nested_deep(self) -> None:
        """Set a nested key."""
        config: dict[str, Any] = {}
        _set_nested(config, "a.b.c", "value")
        assert config["a"]["b"]["c"] == "value"

    def test_set_nested_overwrite(self) -> None:
        """Overwrite an existing nested key."""
        config: dict[str, Any] = {"a": {"b": {"c": "old"}}}
        _set_nested(config, "a.b.c", "new")
        assert config["a"]["b"]["c"] == "new"

    def test_set_nested_creates_intermediate(self) -> None:
        """Create intermediate dicts when needed."""
        config: dict[str, Any] = {"a": "string"}
        _set_nested(config, "a.b.c", "value")
        assert config["a"]["b"]["c"] == "value"

    def test_set_nested_empty_path(self) -> None:
        """Raise ConfigError for empty path."""
        config: dict[str, Any] = {}
        with pytest.raises(ConfigError, match="Empty path"):
            _set_nested(config, "", "value")

    def test_set_nested_dots_only(self) -> None:
        """Raise ConfigError for path with only dots."""
        config: dict[str, Any] = {}
        with pytest.raises(ConfigError, match="Empty path"):
            _set_nested(config, "...", "value")


# ==============================================================================
# Tests for _resolve_tool_path helper
# ==============================================================================


class TestResolveToolPath:
    """Tests for the _resolve_tool_path helper function."""

    def test_resolve_java_language_in_repo(self) -> None:
        """Resolve tool path for Java language in repo block."""
        config = {"repo": {"language": "java"}}
        defaults = {"java": {"tools": {"jacoco": {}}}}
        path = _resolve_tool_path(config, defaults, "jacoco")
        assert path == "java.tools.jacoco.enabled"

    def test_resolve_python_language_in_repo(self) -> None:
        """Resolve tool path for Python language in repo block."""
        config = {"repo": {"language": "python"}}
        defaults = {"python": {"tools": {"pytest": {}}}}
        path = _resolve_tool_path(config, defaults, "pytest")
        assert path == "python.tools.pytest.enabled"

    def test_resolve_java_language_top_level(self) -> None:
        """Resolve tool path for Java language at top level."""
        config = {"language": "java"}
        defaults = {"java": {"tools": {"jacoco": {}}}}
        path = _resolve_tool_path(config, defaults, "jacoco")
        assert path == "java.tools.jacoco.enabled"

    def test_resolve_python_language_top_level(self) -> None:
        """Resolve tool path for Python language at top level."""
        config = {"language": "python"}
        defaults = {"python": {"tools": {"pytest": {}}}}
        path = _resolve_tool_path(config, defaults, "pytest")
        assert path == "python.tools.pytest.enabled"

    def test_resolve_infer_java_from_defaults(self) -> None:
        """Infer Java when tool only in Java defaults."""
        config: dict[str, Any] = {}
        defaults = {"java": {"tools": {"jacoco": {}}}, "python": {"tools": {}}}
        path = _resolve_tool_path(config, defaults, "jacoco")
        assert path == "java.tools.jacoco.enabled"

    def test_resolve_infer_python_from_defaults(self) -> None:
        """Infer Python when tool only in Python defaults."""
        config: dict[str, Any] = {}
        defaults = {"java": {"tools": {}}, "python": {"tools": {"pytest": {}}}}
        path = _resolve_tool_path(config, defaults, "pytest")
        assert path == "python.tools.pytest.enabled"

    def test_resolve_ambiguous_tool(self) -> None:
        """Raise ConfigError when tool exists in both languages."""
        config: dict[str, Any] = {}
        defaults = {
            "java": {"tools": {"semgrep": {}}},
            "python": {"tools": {"semgrep": {}}},
        }
        with pytest.raises(ConfigError, match="exists in both java and python"):
            _resolve_tool_path(config, defaults, "semgrep")

    def test_resolve_unknown_tool(self) -> None:
        """Raise ConfigError for unknown tool."""
        config: dict[str, Any] = {}
        defaults = {"java": {"tools": {}}, "python": {"tools": {}}}
        with pytest.raises(ConfigError, match="Unknown tool"):
            _resolve_tool_path(config, defaults, "unknowntool")


# ==============================================================================
# Tests for _dump_config helper
# ==============================================================================


class TestDumpConfig:
    """Tests for the _dump_config helper function."""

    def test_dump_config_outputs_yaml(self, capsys) -> None:
        """Dump config as YAML to stdout."""
        config = {"key": "value", "nested": {"inner": 123}}
        _dump_config(config)
        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert parsed["key"] == "value"
        assert parsed["nested"]["inner"] == 123


# ==============================================================================
# Tests for cmd_config - show subcommand
# ==============================================================================


class TestCmdConfigShow:
    """Tests for the config show subcommand."""

    def test_show_raw_config(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Show raw config without merging defaults."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="show",
            effective=False,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert parsed["repo"]["owner"] == "testowner"
        assert parsed["language"] == "python"

    def test_show_effective_config(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Show effective config merged with defaults."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="show",
            effective=True,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        # Should have both defaults and repo config merged
        assert "java" in parsed  # From defaults
        assert parsed["repo"]["owner"] == "testowner"  # From repo config

    def test_show_repo_not_found(
        self, hub_paths: PathConfig, capsys, monkeypatch
    ) -> None:
        """Return error when repo config not found."""
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="nonexistent",
            subcommand="show",
            effective=False,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Repo config not found" in captured.err


# ==============================================================================
# Tests for cmd_config - set subcommand
# ==============================================================================


class TestCmdConfigSet:
    """Tests for the config set subcommand."""

    def test_set_simple_value(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Set a simple string value."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="set",
            path="repo.owner",
            value="newowner",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        # Verify the file was updated
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert updated["repo"]["owner"] == "newowner"
        captured = capsys.readouterr()
        assert "[OK] Updated" in captured.err

    def test_set_nested_value(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Set a deeply nested value."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="set",
            path="python.tools.pytest.threshold",
            value="80",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert updated["python"]["tools"]["pytest"]["threshold"] == 80

    def test_set_boolean_value(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Set a boolean value from YAML string."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="set",
            path="python.tools.pytest.enabled",
            value="false",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert updated["python"]["tools"]["pytest"]["enabled"] is False

    def test_set_dry_run(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Dry run shows config without writing."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        original_content = Path(hub_paths.repo_file("testrepo")).read_text(
            encoding="utf-8"
        )
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="set",
            path="repo.owner",
            value="newowner",
            dry_run=True,
        )
        result = cmd_config(args)
        assert result == 0
        # File should NOT be changed
        assert (
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
            == original_content
        )
        captured = capsys.readouterr()
        # Should print the would-be config
        parsed = yaml.safe_load(captured.out)
        assert parsed["repo"]["owner"] == "newowner"


# ==============================================================================
# Tests for cmd_config - enable/disable subcommands
# ==============================================================================


class TestCmdConfigEnableDisable:
    """Tests for the config enable and disable subcommands."""

    def test_enable_tool_python(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Enable a Python tool."""
        # Set ruff to disabled first
        sample_repo_config["python"]["tools"]["ruff"]["enabled"] = False
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="enable",
            tool="ruff",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert updated["python"]["tools"]["ruff"]["enabled"] is True
        captured = capsys.readouterr()
        assert "[OK] Updated" in captured.err

    def test_disable_tool_python(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Disable a Python tool."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="disable",
            tool="pytest",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert updated["python"]["tools"]["pytest"]["enabled"] is False

    def test_enable_tool_java(
        self,
        hub_paths: PathConfig,
        java_repo_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Enable a Java tool."""
        java_repo_config["java"]["tools"]["jacoco"]["enabled"] = False
        write_repo_config(hub_paths, "javarepo", java_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="javarepo",
            subcommand="enable",
            tool="jacoco",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("javarepo")).read_text(encoding="utf-8")
        )
        assert updated["java"]["tools"]["jacoco"]["enabled"] is True

    def test_disable_tool_java(
        self,
        hub_paths: PathConfig,
        java_repo_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Disable a Java tool."""
        write_repo_config(hub_paths, "javarepo", java_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="javarepo",
            subcommand="disable",
            tool="checkstyle",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        updated = yaml.safe_load(
            Path(hub_paths.repo_file("javarepo")).read_text(encoding="utf-8")
        )
        assert updated["java"]["tools"]["checkstyle"]["enabled"] is False

    def test_enable_dry_run(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Dry run for enable shows config without writing."""
        sample_repo_config["python"]["tools"]["ruff"]["enabled"] = False
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        original_content = Path(hub_paths.repo_file("testrepo")).read_text(
            encoding="utf-8"
        )
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="enable",
            tool="ruff",
            dry_run=True,
        )
        result = cmd_config(args)
        assert result == 0
        # File should NOT be changed
        assert (
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
            == original_content
        )
        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert parsed["python"]["tools"]["ruff"]["enabled"] is True

    def test_enable_unknown_tool(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Return error for unknown tool."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="enable",
            tool="unknowntool",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown tool" in captured.err


# ==============================================================================
# Tests for cmd_config - edit subcommand (wizard)
# ==============================================================================


class TestCmdConfigEdit:
    """Tests for the config edit subcommand (wizard mode)."""

    def test_edit_no_wizard_deps(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Return error when wizard dependencies not installed."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        monkeypatch.setattr("cihub.commands.config_cmd.HAS_WIZARD", False)
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="edit",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Install wizard deps" in captured.err

    def test_edit_wizard_cancelled(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Return 130 when wizard is cancelled."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        monkeypatch.setattr("cihub.commands.config_cmd.HAS_WIZARD", True)

        from cihub.wizard import WizardCancelled

        def mock_apply_wizard(paths, existing):
            raise WizardCancelled("User cancelled")

        monkeypatch.setattr(
            "cihub.commands.config_cmd._apply_wizard", mock_apply_wizard
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="edit",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 130
        captured = capsys.readouterr()
        assert "Cancelled" in captured.err

    def test_edit_wizard_success(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Successfully update config via wizard."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        monkeypatch.setattr("cihub.commands.config_cmd.HAS_WIZARD", True)

        updated_config = sample_repo_config.copy()
        updated_config["repo"]["owner"] = "wizardowner"

        def mock_apply_wizard(paths, existing):
            return updated_config

        monkeypatch.setattr(
            "cihub.commands.config_cmd._apply_wizard", mock_apply_wizard
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="edit",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        saved = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert saved["repo"]["owner"] == "wizardowner"
        captured = capsys.readouterr()
        assert "[OK] Updated" in captured.err

    def test_edit_wizard_dry_run(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Dry run for wizard shows config without writing."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        original_content = Path(hub_paths.repo_file("testrepo")).read_text(
            encoding="utf-8"
        )
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        monkeypatch.setattr("cihub.commands.config_cmd.HAS_WIZARD", True)

        updated_config = sample_repo_config.copy()
        updated_config["repo"]["owner"] = "wizardowner"

        def mock_apply_wizard(paths, existing):
            return updated_config

        monkeypatch.setattr(
            "cihub.commands.config_cmd._apply_wizard", mock_apply_wizard
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="edit",
            dry_run=True,
        )
        result = cmd_config(args)
        assert result == 0
        # File should NOT be changed
        assert (
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
            == original_content
        )
        captured = capsys.readouterr()
        parsed = yaml.safe_load(captured.out)
        assert parsed["repo"]["owner"] == "wizardowner"


# ==============================================================================
# Tests for cmd_config - error handling
# ==============================================================================


class TestCmdConfigErrors:
    """Tests for error handling in cmd_config."""

    def test_missing_repo_arg(self, capsys, monkeypatch, tmp_path: Path) -> None:
        """Return error when --repo not provided."""
        monkeypatch.setattr("cihub.commands.config_cmd.hub_root", lambda: tmp_path)
        # Ensure dirs exist
        (tmp_path / "config" / "repos").mkdir(parents=True)
        (tmp_path / "config" / "defaults.yaml").write_text("{}", encoding="utf-8")
        args = argparse.Namespace(
            repo=None,
            subcommand="show",
            effective=False,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "--repo is required" in captured.err

    def test_unsupported_subcommand(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Return error for unsupported subcommand."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="invalid",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Unsupported config command" in captured.err


# ==============================================================================
# Tests for cmd_config - None/default subcommand (edit mode)
# ==============================================================================


class TestCmdConfigDefaultSubcommand:
    """Tests for default (None) subcommand behavior."""

    def test_none_subcommand_triggers_edit(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """None subcommand triggers edit/wizard mode."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )
        monkeypatch.setattr("cihub.commands.config_cmd.HAS_WIZARD", False)
        args = argparse.Namespace(
            repo="testrepo",
            subcommand=None,  # No subcommand defaults to edit
            dry_run=False,
        )
        result = cmd_config(args)
        # Should fail because wizard not installed
        assert result == 1
        captured = capsys.readouterr()
        assert "Install wizard deps" in captured.err


# ==============================================================================
# Integration-style tests
# ==============================================================================


class TestCmdConfigIntegration:
    """Integration-style tests for cmd_config."""

    def test_workflow_show_set_show(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        capsys,
        monkeypatch,
    ) -> None:
        """Test workflow: show -> set -> show."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )

        # 1. Show original
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="show",
            effective=False,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        captured = capsys.readouterr()
        original = yaml.safe_load(captured.out)
        assert original["repo"]["owner"] == "testowner"

        # 2. Set new value
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="set",
            path="repo.owner",
            value="modifiedowner",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0

        # 3. Show updated
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="show",
            effective=False,
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        captured = capsys.readouterr()
        updated = yaml.safe_load(captured.out)
        assert updated["repo"]["owner"] == "modifiedowner"

    def test_workflow_disable_enable(
        self,
        hub_paths: PathConfig,
        sample_repo_config: dict[str, Any],
        monkeypatch,
    ) -> None:
        """Test workflow: disable -> enable."""
        write_repo_config(hub_paths, "testrepo", sample_repo_config)
        monkeypatch.setattr(
            "cihub.commands.config_cmd.hub_root", lambda: Path(hub_paths.root)
        )

        # 1. Disable pytest
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="disable",
            tool="pytest",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        config = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert config["python"]["tools"]["pytest"]["enabled"] is False

        # 2. Enable pytest
        args = argparse.Namespace(
            repo="testrepo",
            subcommand="enable",
            tool="pytest",
            dry_run=False,
        )
        result = cmd_config(args)
        assert result == 0
        config = yaml.safe_load(
            Path(hub_paths.repo_file("testrepo")).read_text(encoding="utf-8")
        )
        assert config["python"]["tools"]["pytest"]["enabled"] is True
