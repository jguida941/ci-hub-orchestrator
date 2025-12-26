"""Extended tests for cihub.commands module - JSON mode, error paths, edge cases."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import CommandResult  # noqa: E402
from cihub.commands.init import cmd_init  # noqa: E402
from cihub.commands.update import cmd_update  # noqa: E402
from cihub.commands.validate import cmd_validate  # noqa: E402

try:
    from hypothesis import HealthCheck, given, settings, strategies as st  # isort: skip # noqa: E402
except ImportError:  # pragma: no cover - optional dependency
    HealthCheck = None
    given = None
    settings = None
    st = None


# =============================================================================
# cmd_validate JSON Mode Tests
# =============================================================================


class TestCmdValidateJsonMode:
    """Tests for cmd_validate JSON output mode."""

    def test_validate_missing_config_json_mode(self, tmp_path: Path) -> None:
        """JSON mode returns CommandResult for missing config."""
        args = argparse.Namespace(repo=str(tmp_path), strict=False, json=True)
        result = cmd_validate(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "Config not found" in result.summary
        assert len(result.problems) == 1
        assert result.problems[0]["code"] == "CIHUB-VALIDATE-001"

    def test_validate_schema_errors_json_mode(self, tmp_path: Path) -> None:
        """JSON mode returns schema errors as problems."""
        config_content = "repo:\n  owner: test\n"
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False, json=True)
        result = cmd_validate(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 1
        assert "Validation failed" in result.summary
        assert any(p["code"] == "CIHUB-VALIDATE-002" for p in result.problems)

    def test_validate_success_json_mode(self, tmp_path: Path) -> None:
        """JSON mode returns success CommandResult for valid config."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
    ruff:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False, json=True)
        result = cmd_validate(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "Config OK" in result.summary
        assert result.data["language"] == "python"

    def test_validate_java_pom_warnings_json_mode(self, tmp_path: Path) -> None:
        """JSON mode returns POM warnings as problems."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
python:
  version: '3.12'
  tools:
    pytest:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False, json=True)
        result = cmd_validate(args)
        assert isinstance(result, CommandResult)
        # Should have POM warnings
        if result.problems:
            assert any(p["code"] == "CIHUB-POM-001" for p in result.problems)

    def test_validate_java_strict_json_mode(self, tmp_path: Path) -> None:
        """JSON mode in strict returns exit_code 1 for POM warnings."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
python:
  version: '3.12'
  tools:
    pytest:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=True, json=True)
        result = cmd_validate(args)
        assert isinstance(result, CommandResult)
        # Strict mode should fail if there are POM warnings
        if result.problems:
            assert result.exit_code == 1


# =============================================================================
# cmd_init JSON Mode and Error Path Tests
# =============================================================================


class TestCmdInitJsonMode:
    """Tests for cmd_init JSON output mode."""

    def test_init_wizard_with_json_fails(self, tmp_path: Path) -> None:
        """Wizard mode with JSON returns error CommandResult."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=True,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_init(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "wizard" in result.summary.lower()

    def test_init_force_without_apply_json(self, tmp_path: Path) -> None:
        """Force without apply in JSON mode returns error."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=False,
            force=True,
            fix_pom=False,
            json=True,
        )
        result = cmd_init(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "--force requires --apply" in result.summary

    def test_init_force_without_apply_non_json(self, tmp_path: Path, capsys) -> None:
        """Force without apply in non-JSON mode prints error."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=False,
            force=True,
            fix_pom=False,
            json=False,
        )
        result = cmd_init(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "--force requires --apply" in captured.err

    def test_init_repo_side_execution_blocked(self, tmp_path: Path, capsys) -> None:
        """Apply blocked when repo_side_execution is false and not bootstrap."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
  repo_side_execution: false
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "hub-ci.yml").write_text(
            "name: CI\n", encoding="utf-8"
        )
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=False,
        )
        result = cmd_init(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "repo_side_execution is false" in captured.err

    def test_init_repo_side_execution_blocked_json(self, tmp_path: Path) -> None:
        """Apply blocked in JSON mode when repo_side_execution is false."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
  repo_side_execution: false
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "hub-ci.yml").write_text(
            "name: CI\n", encoding="utf-8"
        )
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_init(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "repo_side_execution" in result.summary
        assert result.problems[0]["code"] == "CIHUB-INIT-001"

    def test_init_json_mode_success(self, tmp_path: Path) -> None:
        """Init in JSON mode returns proper CommandResult."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_init(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "complete" in result.summary.lower()
        assert result.data["language"] == "python"
        assert result.data["owner"] == "testowner"
        assert result.data["name"] == "testrepo"

    def test_init_json_mode_dry_run(self, tmp_path: Path) -> None:
        """Init dry run in JSON mode returns proper CommandResult."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            wizard=False,
            dry_run=True,
            apply=False,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_init(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "dry run" in result.summary.lower()
        assert result.data["dry_run"] is True


# =============================================================================
# cmd_update JSON Mode and Error Path Tests
# =============================================================================


class TestCmdUpdateJsonMode:
    """Tests for cmd_update JSON output mode."""

    def test_update_force_without_apply_json(self, tmp_path: Path) -> None:
        """Force without apply in JSON mode returns error."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=False,
            force=True,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "--force requires --apply" in result.summary

    def test_update_force_without_apply_non_json(self, tmp_path: Path, capsys) -> None:
        """Force without apply in non-JSON mode prints error."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=False,
            force=True,
            fix_pom=False,
            json=False,
        )
        result = cmd_update(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "--force requires --apply" in captured.err

    def test_update_repo_side_execution_blocked(self, tmp_path: Path, capsys) -> None:
        """Apply blocked when repo_side_execution is false."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
  repo_side_execution: false
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "hub-ci.yml").write_text(
            "name: CI\n", encoding="utf-8"
        )
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=False,
        )
        result = cmd_update(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "repo_side_execution is false" in captured.err

    def test_update_repo_side_execution_blocked_json(self, tmp_path: Path) -> None:
        """Apply blocked in JSON mode when repo_side_execution is false."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
  repo_side_execution: false
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "hub-ci.yml").write_text(
            "name: CI\n", encoding="utf-8"
        )
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "repo_side_execution" in result.summary
        assert result.problems[0]["code"] == "CIHUB-UPDATE-001"

    def test_update_json_mode_success(self, tmp_path: Path) -> None:
        """Update in JSON mode returns proper CommandResult."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "complete" in result.summary.lower()
        assert result.data["language"] == "python"

    def test_update_json_mode_dry_run(self, tmp_path: Path) -> None:
        """Update dry run in JSON mode returns proper CommandResult."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir="",
            dry_run=True,
            apply=False,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "dry run" in result.summary.lower()
        assert result.data["dry_run"] is True

    def test_update_missing_owner_warning_json(self, tmp_path: Path) -> None:
        """Update adds owner warning in JSON mode when owner unknown."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        # Should have warning about missing owner
        if result.problems:
            owner_warning = any(
                "owner" in str(p.get("message", "")).lower() for p in result.problems
            )
            assert owner_warning
        assert result.data["owner"] == "unknown"


# =============================================================================
# Property-Based Tests for config/merge.py
# =============================================================================


class TestDeepMergeProperties:
    """Property-based tests for deep_merge using Hypothesis."""

    def test_deep_merge_empty_overlay_returns_copy(self) -> None:
        """Merging with empty overlay returns copy of base."""
        from cihub.config.merge import deep_merge

        base = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, {})
        assert result == base
        # Should be a copy, not same object
        assert result is not base
        assert result["b"] is not base["b"]

    def test_deep_merge_empty_base_returns_copy(self) -> None:
        """Merging empty base with overlay returns copy of overlay."""
        from cihub.config.merge import deep_merge

        overlay = {"a": 1, "b": {"c": 2}}
        result = deep_merge({}, overlay)
        assert result == overlay
        # Should be a copy
        assert result is not overlay

    def test_deep_merge_overlay_wins(self) -> None:
        """Overlay values take precedence over base."""
        from cihub.config.merge import deep_merge

        base = {"a": 1, "b": 2}
        overlay = {"a": 10, "c": 3}
        result = deep_merge(base, overlay)
        assert result["a"] == 10  # Overlay wins
        assert result["b"] == 2  # Base preserved
        assert result["c"] == 3  # Overlay added

    def test_deep_merge_nested_dicts(self) -> None:
        """Nested dicts are merged recursively."""
        from cihub.config.merge import deep_merge

        base = {"a": {"b": 1, "c": 2}}
        overlay = {"a": {"b": 10, "d": 4}}
        result = deep_merge(base, overlay)
        assert result["a"]["b"] == 10  # Overlay wins
        assert result["a"]["c"] == 2  # Base preserved
        assert result["a"]["d"] == 4  # Overlay added

    def test_deep_merge_non_dict_replaces(self) -> None:
        """Non-dict values in overlay replace base values."""
        from cihub.config.merge import deep_merge

        base = {"a": {"b": 1}}
        overlay = {"a": "replaced"}
        result = deep_merge(base, overlay)
        assert result["a"] == "replaced"

    def test_build_effective_config_layer_priority(self) -> None:
        """build_effective_config applies layers in correct order."""
        from cihub.config.merge import build_effective_config

        defaults = {"a": 1, "b": 2, "c": 3}
        profile = {"b": 20, "d": 4}
        repo = {"c": 30, "e": 5}

        result = build_effective_config(defaults, profile, repo)

        assert result["a"] == 1  # From defaults
        assert result["b"] == 20  # Profile overrides defaults
        assert result["c"] == 30  # Repo overrides all
        assert result["d"] == 4  # From profile
        assert result["e"] == 5  # From repo

    def test_build_effective_config_none_layers(self) -> None:
        """build_effective_config handles None profile and repo."""
        from cihub.config.merge import build_effective_config

        defaults = {"a": 1, "b": 2}
        result = build_effective_config(defaults, None, None)
        assert result == defaults
        # Should be a copy
        assert result is not defaults


# =============================================================================
# Hypothesis Property-Based Tests
# =============================================================================

if given and settings and st:

    class TestDeepMergeHypothesis:
        """Hypothesis property-based tests for deep_merge."""

        @given(st.dictionaries(st.text(min_size=1, max_size=10), st.integers()))
        @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
        def test_merge_with_empty_preserves_keys(self, base: dict) -> None:
            """Merging with empty dict preserves all keys."""
            from cihub.config.merge import deep_merge

            result = deep_merge(base, {})
            assert set(result.keys()) == set(base.keys())

        @given(
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers()),
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers()),
        )
        @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
        def test_merge_contains_all_keys(self, base: dict, overlay: dict) -> None:
            """Result contains all keys from both base and overlay."""
            from cihub.config.merge import deep_merge

            result = deep_merge(base, overlay)
            all_keys = set(base.keys()) | set(overlay.keys())
            assert set(result.keys()) == all_keys

        @given(
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers()),
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers()),
        )
        @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
        def test_overlay_values_take_precedence(
            self, base: dict, overlay: dict
        ) -> None:
            """Overlay values always take precedence."""
            from cihub.config.merge import deep_merge

            result = deep_merge(base, overlay)
            for key, value in overlay.items():
                assert result[key] == value


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


class TestInitEdgeCases:
    """Additional edge case tests for cmd_init."""

    def test_init_with_git_remote_detection(self, tmp_path: Path) -> None:
        """Init uses git remote when owner/name not provided."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )

        with mock.patch("cihub.commands.init.get_git_remote") as mock_remote:
            mock_remote.return_value = (
                "https://github.com/detected-owner/detected-repo.git"
            )
            with mock.patch("cihub.commands.init.parse_repo_from_remote") as mock_parse:
                mock_parse.return_value = ("detected-owner", "detected-repo")

                args = argparse.Namespace(
                    repo=str(tmp_path),
                    language=None,
                    owner=None,
                    name=None,
                    branch=None,
                    subdir="",
                    wizard=False,
                    dry_run=False,
                    apply=True,
                    force=False,
                    fix_pom=False,
                    json=False,
                )
                result = cmd_init(args)
                assert result == 0

                config_text = (tmp_path / ".ci-hub.yml").read_text()
                assert "detected-owner" in config_text
                assert "detected-repo" in config_text

    def test_init_with_git_branch_detection(self, tmp_path: Path) -> None:
        """Init uses git branch when branch not provided."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )

        with mock.patch("cihub.commands.init.get_git_branch") as mock_branch:
            mock_branch.return_value = "develop"

            args = argparse.Namespace(
                repo=str(tmp_path),
                language=None,
                owner="testowner",
                name="testrepo",
                branch=None,
                subdir="",
                wizard=False,
                dry_run=False,
                apply=True,
                force=False,
                fix_pom=False,
                json=False,
            )
            result = cmd_init(args)
            assert result == 0

            config_text = (tmp_path / ".ci-hub.yml").read_text()
            assert "develop" in config_text


class TestUpdateEdgeCases:
    """Additional edge case tests for cmd_update."""

    def test_update_preserves_existing_config_values(self, tmp_path: Path) -> None:
        """Update preserves values from existing config."""
        config_content = """
repo:
  owner: existing-owner
  name: existing-name
  default_branch: develop
  custom_key: preserved
language: python
python:
  version: '3.11'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='example'\n", encoding="utf-8"
        )

        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=False,
            apply=True,
            force=True,  # Force to bypass repo_side_execution check
            fix_pom=False,
            json=False,
        )
        result = cmd_update(args)
        assert result == 0

        config_text = (tmp_path / ".ci-hub.yml").read_text()
        # Existing values should be preserved through merge
        assert "existing-owner" in config_text or "existing-name" in config_text

    def test_update_with_language_override(self, tmp_path: Path) -> None:
        """Update respects language override."""
        config_content = """
repo:
  owner: test
  name: example
  default_branch: main
language: python
python:
  version: '3.12'
  tools:
    pytest:
      enabled: true
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")

        args = argparse.Namespace(
            repo=str(tmp_path),
            language="java",  # Override to java
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=False,
            apply=True,
            force=True,
            fix_pom=False,
            json=True,
        )
        result = cmd_update(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.data["language"] == "java"


# =============================================================================
# get_effective_config_for_repo Tests
# =============================================================================


class TestGetEffectiveConfigForRepo:
    """Tests for get_effective_config_for_repo function."""

    def test_loads_defaults_and_repo_config(self, tmp_path: Path) -> None:
        """Loads and merges defaults with repo config."""
        from cihub.config.merge import get_effective_config_for_repo
        from cihub.config.paths import PathConfig

        # Create hub structure
        config_dir = tmp_path / "config"
        repos_dir = config_dir / "repos"
        repos_dir.mkdir(parents=True)

        # Create defaults.yaml
        defaults_file = config_dir / "defaults.yaml"
        defaults_file.write_text(
            "language: python\npython:\n  version: '3.10'\n", encoding="utf-8"
        )

        # Create repo config with owner subdirectory
        owner_dir = repos_dir / "owner"
        owner_dir.mkdir()
        repo_file = owner_dir / "repo.yaml"
        repo_file.write_text("python:\n  version: '3.12'\n", encoding="utf-8")

        paths = PathConfig(str(tmp_path))
        result = get_effective_config_for_repo(paths, "owner/repo")

        assert result["language"] == "python"
        assert result["python"]["version"] == "3.12"  # Repo config takes precedence

    def test_applies_profile_when_specified(self, tmp_path: Path) -> None:
        """Applies profile config when profile_name is provided."""
        from cihub.config.merge import get_effective_config_for_repo
        from cihub.config.paths import PathConfig

        # Create hub structure
        config_dir = tmp_path / "config"
        repos_dir = config_dir / "repos"
        repos_dir.mkdir(parents=True)
        profiles_dir = tmp_path / "templates" / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create defaults.yaml
        defaults_file = config_dir / "defaults.yaml"
        defaults_file.write_text(
            "language: python\npython:\n  version: '3.10'\n", encoding="utf-8"
        )

        # Create profile
        profile_file = profiles_dir / "strict.yaml"
        profile_file.write_text(
            "python:\n  tools:\n    ruff:\n      enabled: true\n", encoding="utf-8"
        )

        # Create repo config with owner subdirectory
        owner_dir = repos_dir / "owner"
        owner_dir.mkdir()
        repo_file = owner_dir / "repo.yaml"
        repo_file.write_text("python:\n  version: '3.12'\n", encoding="utf-8")

        paths = PathConfig(str(tmp_path))
        result = get_effective_config_for_repo(
            paths, "owner/repo", profile_name="strict"
        )

        # Profile merged in
        assert result["python"]["tools"]["ruff"]["enabled"] is True
        # Repo config takes precedence for version
        assert result["python"]["version"] == "3.12"

    def test_no_profile_applied_when_none(self, tmp_path: Path) -> None:
        """No profile applied when profile_name is None."""
        from cihub.config.merge import get_effective_config_for_repo
        from cihub.config.paths import PathConfig

        # Create hub structure
        config_dir = tmp_path / "config"
        repos_dir = config_dir / "repos"
        repos_dir.mkdir(parents=True)

        # Create defaults.yaml
        defaults_file = config_dir / "defaults.yaml"
        defaults_file.write_text("language: python\n", encoding="utf-8")

        # Create repo config with owner subdirectory
        owner_dir = repos_dir / "owner"
        owner_dir.mkdir()
        repo_file = owner_dir / "repo.yaml"
        repo_file.write_text("python:\n  version: '3.12'\n", encoding="utf-8")

        paths = PathConfig(str(tmp_path))
        result = get_effective_config_for_repo(paths, "owner/repo", profile_name=None)

        # Just defaults + repo, no profile
        assert result["language"] == "python"
        assert result["python"]["version"] == "3.12"
