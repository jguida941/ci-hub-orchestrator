"""Comprehensive tests for cihub.config module.

These tests are designed to be mutation-testing ready with specific
assertions that would fail if the logic were changed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cihub.config import (
    PathConfig,
    build_effective_config,
    deep_merge,
    ensure_dirs,
    list_profiles,
    list_repos,
    load_defaults,
    load_profile,
    load_repo_config,
    load_yaml_file,
    save_repo_config,
    save_yaml_file,
)

# =============================================================================
# PathConfig Tests
# =============================================================================


class TestPathConfig:
    """Tests for PathConfig dataclass."""

    def test_config_dir_path(self):
        """config_dir is root/config."""
        paths = PathConfig(root="/hub")
        assert paths.config_dir == "/hub/config"

    def test_repos_dir_path(self):
        """repos_dir is root/config/repos."""
        paths = PathConfig(root="/hub")
        assert paths.repos_dir == "/hub/config/repos"

    def test_defaults_file_path(self):
        """defaults_file is root/config/defaults.yaml."""
        paths = PathConfig(root="/hub")
        assert paths.defaults_file == "/hub/config/defaults.yaml"

    def test_profiles_dir_path(self):
        """profiles_dir is root/templates/profiles."""
        paths = PathConfig(root="/hub")
        assert paths.profiles_dir == "/hub/templates/profiles"

    def test_schema_dir_path(self):
        """schema_dir is root/schema."""
        paths = PathConfig(root="/hub")
        assert paths.schema_dir == "/hub/schema"

    def test_repo_file_path(self):
        """repo_file returns correct path for repo name."""
        paths = PathConfig(root="/hub")
        assert paths.repo_file("my-repo") == "/hub/config/repos/my-repo.yaml"

    def test_repo_file_with_special_chars(self):
        """repo_file handles repo names with special characters."""
        paths = PathConfig(root="/hub")
        assert (
            paths.repo_file("org-name_repo") == "/hub/config/repos/org-name_repo.yaml"
        )

    def test_profile_file_path(self):
        """profile_file returns correct path for profile name."""
        paths = PathConfig(root="/hub")
        assert (
            paths.profile_file("java-security")
            == "/hub/templates/profiles/java-security.yaml"
        )

    def test_frozen_dataclass(self):
        """PathConfig is immutable."""
        paths = PathConfig(root="/hub")
        with pytest.raises(AttributeError):
            paths.root = "/other"


# =============================================================================
# load_yaml_file Tests
# =============================================================================


class TestLoadYamlFile:
    """Tests for load_yaml_file function."""

    def test_load_nonexistent_file(self, tmp_path: Path):
        """Loading nonexistent file returns empty dict."""
        result = load_yaml_file(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_load_valid_yaml(self, tmp_path: Path):
        """Loading valid YAML returns parsed dict."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nnested:\n  inner: data")

        result = load_yaml_file(yaml_file)
        assert result == {"key": "value", "nested": {"inner": "data"}}

    def test_load_empty_file(self, tmp_path: Path):
        """Loading empty file returns empty dict."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_yaml_file(yaml_file)
        assert result == {}

    def test_load_null_content(self, tmp_path: Path):
        """Loading file with null content returns empty dict."""
        yaml_file = tmp_path / "null.yaml"
        yaml_file.write_text("null")

        result = load_yaml_file(yaml_file)
        assert result == {}

    def test_load_whitespace_only(self, tmp_path: Path):
        """Loading file with only whitespace returns empty dict."""
        yaml_file = tmp_path / "whitespace.yaml"
        yaml_file.write_text("   \n\n     ")  # spaces and newlines only (no tabs)

        result = load_yaml_file(yaml_file)
        assert result == {}

    def test_load_list_raises_valueerror(self, tmp_path: Path):
        """Loading YAML with list root raises ValueError."""
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(ValueError, match="mapping.*dict"):
            load_yaml_file(yaml_file)

    def test_load_string_raises_valueerror(self, tmp_path: Path):
        """Loading YAML with string root raises ValueError."""
        yaml_file = tmp_path / "string.yaml"
        yaml_file.write_text("just a string")

        with pytest.raises(ValueError, match="mapping.*dict"):
            load_yaml_file(yaml_file)

    def test_load_number_raises_valueerror(self, tmp_path: Path):
        """Loading YAML with number root raises ValueError."""
        yaml_file = tmp_path / "number.yaml"
        yaml_file.write_text("42")

        with pytest.raises(ValueError, match="mapping.*dict"):
            load_yaml_file(yaml_file)

    def test_load_boolean_raises_valueerror(self, tmp_path: Path):
        """Loading YAML with boolean root raises ValueError."""
        yaml_file = tmp_path / "boolean.yaml"
        yaml_file.write_text("true")

        with pytest.raises(ValueError, match="mapping.*dict"):
            load_yaml_file(yaml_file)

    def test_load_accepts_string_path(self, tmp_path: Path):
        """Function accepts string path argument."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")

        result = load_yaml_file(str(yaml_file))
        assert result == {"key": "value"}

    def test_load_complex_yaml(self, tmp_path: Path):
        """Loading complex YAML with various types works correctly."""
        yaml_file = tmp_path / "complex.yaml"
        content = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"a": {"b": {"c": "deep"}}},
        }
        yaml_file.write_text(yaml.dump(content))

        result = load_yaml_file(yaml_file)
        assert result == content


# =============================================================================
# save_yaml_file Tests
# =============================================================================


class TestSaveYamlFile:
    """Tests for save_yaml_file function."""

    def test_save_creates_file(self, tmp_path: Path):
        """Saving creates a new file."""
        yaml_file = tmp_path / "new.yaml"
        data = {"key": "value"}

        result = save_yaml_file(yaml_file, data)

        assert result is True
        assert yaml_file.exists()

    def test_save_writes_correct_content(self, tmp_path: Path):
        """Saved content can be loaded back correctly."""
        yaml_file = tmp_path / "test.yaml"
        data = {"key": "value", "nested": {"inner": 42}}

        save_yaml_file(yaml_file, data)
        loaded = load_yaml_file(yaml_file)

        assert loaded == data

    def test_save_overwrites_existing(self, tmp_path: Path):
        """Saving overwrites existing file."""
        yaml_file = tmp_path / "existing.yaml"
        yaml_file.write_text("old: data")

        save_yaml_file(yaml_file, {"new": "data"})
        loaded = load_yaml_file(yaml_file)

        assert loaded == {"new": "data"}

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        """Saving creates parent directories if needed."""
        yaml_file = tmp_path / "a" / "b" / "c" / "test.yaml"
        data = {"key": "value"}

        save_yaml_file(yaml_file, data)

        assert yaml_file.exists()
        assert load_yaml_file(yaml_file) == data

    def test_dry_run_does_not_write(self, tmp_path: Path):
        """Dry run returns True but does not write file."""
        yaml_file = tmp_path / "dryrun.yaml"
        data = {"key": "value"}

        result = save_yaml_file(yaml_file, data, dry_run=True)

        assert result is True
        assert not yaml_file.exists()

    def test_dry_run_does_not_overwrite(self, tmp_path: Path):
        """Dry run does not overwrite existing file."""
        yaml_file = tmp_path / "existing.yaml"
        yaml_file.write_text("original: content")

        save_yaml_file(yaml_file, {"new": "data"}, dry_run=True)
        loaded = load_yaml_file(yaml_file)

        assert loaded == {"original": "content"}

    def test_save_accepts_string_path(self, tmp_path: Path):
        """Function accepts string path argument."""
        yaml_file = tmp_path / "test.yaml"
        data = {"key": "value"}

        save_yaml_file(str(yaml_file), data)

        assert load_yaml_file(yaml_file) == data

    def test_save_empty_dict(self, tmp_path: Path):
        """Saving empty dict creates valid YAML."""
        yaml_file = tmp_path / "empty.yaml"

        save_yaml_file(yaml_file, {})
        loaded = load_yaml_file(yaml_file)

        assert loaded == {}


# =============================================================================
# ensure_dirs Tests
# =============================================================================


class TestEnsureDirs:
    """Tests for ensure_dirs function."""

    def test_creates_config_dir(self, tmp_path: Path):
        """ensure_dirs creates config directory."""
        paths = PathConfig(root=str(tmp_path))
        ensure_dirs(paths)

        assert Path(paths.config_dir).exists()

    def test_creates_repos_dir(self, tmp_path: Path):
        """ensure_dirs creates repos directory."""
        paths = PathConfig(root=str(tmp_path))
        ensure_dirs(paths)

        assert Path(paths.repos_dir).exists()

    def test_creates_profiles_dir(self, tmp_path: Path):
        """ensure_dirs creates profiles directory."""
        paths = PathConfig(root=str(tmp_path))
        ensure_dirs(paths)

        assert Path(paths.profiles_dir).exists()

    def test_idempotent(self, tmp_path: Path):
        """ensure_dirs is idempotent - can be called multiple times."""
        paths = PathConfig(root=str(tmp_path))

        ensure_dirs(paths)
        ensure_dirs(paths)  # Should not raise

        assert Path(paths.config_dir).exists()


# =============================================================================
# load_defaults Tests
# =============================================================================


class TestLoadDefaults:
    """Tests for load_defaults function."""

    def test_load_existing_defaults(self, tmp_path: Path):
        """load_defaults loads from defaults.yaml."""
        paths = PathConfig(root=str(tmp_path))
        defaults_file = Path(paths.defaults_file)
        defaults_file.parent.mkdir(parents=True, exist_ok=True)
        defaults_file.write_text("key: value")

        result = load_defaults(paths)
        assert result == {"key": "value"}

    def test_load_missing_defaults(self, tmp_path: Path):
        """load_defaults returns empty dict if file missing."""
        paths = PathConfig(root=str(tmp_path))

        result = load_defaults(paths)
        assert result == {}


# =============================================================================
# load_profile Tests
# =============================================================================


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_existing_profile(self, tmp_path: Path):
        """load_profile loads named profile."""
        paths = PathConfig(root=str(tmp_path))
        profiles_dir = Path(paths.profiles_dir)
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "java-security.yaml").write_text(
            "java:\n  tools:\n    semgrep: true"
        )

        result = load_profile(paths, "java-security")
        assert result == {"java": {"tools": {"semgrep": True}}}

    def test_load_missing_profile(self, tmp_path: Path):
        """load_profile returns empty dict if profile missing."""
        paths = PathConfig(root=str(tmp_path))

        result = load_profile(paths, "nonexistent")
        assert result == {}


# =============================================================================
# load_repo_config Tests
# =============================================================================


class TestLoadRepoConfig:
    """Tests for load_repo_config function."""

    def test_load_existing_repo_config(self, tmp_path: Path):
        """load_repo_config loads named repo config."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True, exist_ok=True)
        (repos_dir / "my-repo.yaml").write_text("repo:\n  owner: jguida941")

        result = load_repo_config(paths, "my-repo")
        assert result == {"repo": {"owner": "jguida941"}}

    def test_load_missing_repo_config(self, tmp_path: Path):
        """load_repo_config returns empty dict if config missing."""
        paths = PathConfig(root=str(tmp_path))

        result = load_repo_config(paths, "nonexistent")
        assert result == {}


# =============================================================================
# save_repo_config Tests
# =============================================================================


class TestSaveRepoConfig:
    """Tests for save_repo_config function."""

    def test_save_creates_repo_config(self, tmp_path: Path):
        """save_repo_config creates repo config file."""
        paths = PathConfig(root=str(tmp_path))
        data = {"repo": {"name": "test"}}

        save_repo_config(paths, "test-repo", data)

        assert Path(paths.repo_file("test-repo")).exists()
        assert load_repo_config(paths, "test-repo") == data

    def test_save_dry_run(self, tmp_path: Path):
        """save_repo_config with dry_run does not write."""
        paths = PathConfig(root=str(tmp_path))
        data = {"repo": {"name": "test"}}

        result = save_repo_config(paths, "test-repo", data, dry_run=True)

        assert result is True
        assert not Path(paths.repo_file("test-repo")).exists()


# =============================================================================
# list_repos Tests
# =============================================================================


class TestListRepos:
    """Tests for list_repos function."""

    def test_list_empty_when_no_dir(self, tmp_path: Path):
        """list_repos returns empty list when repos dir doesn't exist."""
        paths = PathConfig(root=str(tmp_path))

        result = list_repos(paths)
        assert result == []

    def test_list_empty_when_dir_empty(self, tmp_path: Path):
        """list_repos returns empty list when repos dir is empty."""
        paths = PathConfig(root=str(tmp_path))
        Path(paths.repos_dir).mkdir(parents=True)

        result = list_repos(paths)
        assert result == []

    def test_list_returns_repo_names(self, tmp_path: Path):
        """list_repos returns repo names without .yaml extension."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True)
        (repos_dir / "repo-a.yaml").write_text("a: 1")
        (repos_dir / "repo-b.yaml").write_text("b: 2")

        result = list_repos(paths)
        assert result == ["repo-a", "repo-b"]

    def test_list_sorted_alphabetically(self, tmp_path: Path):
        """list_repos returns repos sorted alphabetically."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True)
        (repos_dir / "zebra.yaml").write_text("z: 1")
        (repos_dir / "alpha.yaml").write_text("a: 1")
        (repos_dir / "middle.yaml").write_text("m: 1")

        result = list_repos(paths)
        assert result == ["alpha", "middle", "zebra"]

    def test_list_ignores_non_yaml(self, tmp_path: Path):
        """list_repos ignores non-.yaml files."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True)
        (repos_dir / "repo.yaml").write_text("a: 1")
        (repos_dir / "readme.md").write_text("# Readme")
        (repos_dir / ".gitkeep").write_text("")

        result = list_repos(paths)
        assert result == ["repo"]

    def test_list_ignores_directories(self, tmp_path: Path):
        """list_repos ignores directories even with .yaml in name."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True)
        (repos_dir / "repo.yaml").write_text("a: 1")
        (repos_dir / "subdir.yaml").mkdir()

        result = list_repos(paths)
        assert result == ["repo"]


# =============================================================================
# list_profiles Tests
# =============================================================================


class TestListProfiles:
    """Tests for list_profiles function."""

    def test_list_empty_when_no_dir(self, tmp_path: Path):
        """list_profiles returns empty list when profiles dir doesn't exist."""
        paths = PathConfig(root=str(tmp_path))

        result = list_profiles(paths)
        assert result == []

    def test_list_returns_profile_names(self, tmp_path: Path):
        """list_profiles returns profile names without .yaml extension."""
        paths = PathConfig(root=str(tmp_path))
        profiles_dir = Path(paths.profiles_dir)
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "java-security.yaml").write_text("a: 1")
        (profiles_dir / "python-fast.yaml").write_text("b: 2")

        result = list_profiles(paths)
        assert result == ["java-security", "python-fast"]

    def test_list_sorted_alphabetically(self, tmp_path: Path):
        """list_profiles returns profiles sorted alphabetically."""
        paths = PathConfig(root=str(tmp_path))
        profiles_dir = Path(paths.profiles_dir)
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "z-profile.yaml").write_text("z: 1")
        (profiles_dir / "a-profile.yaml").write_text("a: 1")

        result = list_profiles(paths)
        assert result == ["a-profile", "z-profile"]


# =============================================================================
# deep_merge Tests
# =============================================================================


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_empty_base_and_overlay(self):
        """Merging two empty dicts returns empty dict."""
        result = deep_merge({}, {})
        assert result == {}

    def test_empty_base(self):
        """Merging empty base with overlay returns overlay copy."""
        overlay = {"key": "value"}
        result = deep_merge({}, overlay)
        assert result == {"key": "value"}

    def test_empty_overlay(self):
        """Merging base with empty overlay returns base copy."""
        base = {"key": "value"}
        result = deep_merge(base, {})
        assert result == {"key": "value"}

    def test_overlay_wins_simple(self):
        """Overlay values override base values."""
        base = {"key": "base"}
        overlay = {"key": "overlay"}
        result = deep_merge(base, overlay)
        assert result["key"] == "overlay"

    def test_adds_new_keys(self):
        """Overlay adds keys not in base."""
        base = {"a": 1}
        overlay = {"b": 2}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 2}

    def test_nested_merge(self):
        """Nested dicts are merged recursively."""
        base = {"outer": {"inner": "base", "preserved": "yes"}}
        overlay = {"outer": {"inner": "overlay", "added": "new"}}
        result = deep_merge(base, overlay)

        assert result["outer"]["inner"] == "overlay"
        assert result["outer"]["preserved"] == "yes"
        assert result["outer"]["added"] == "new"

    def test_deeply_nested_merge(self):
        """Deeply nested structures merge correctly."""
        base = {"a": {"b": {"c": {"d": "base"}}}}
        overlay = {"a": {"b": {"c": {"e": "overlay"}}}}
        result = deep_merge(base, overlay)

        assert result["a"]["b"]["c"]["d"] == "base"
        assert result["a"]["b"]["c"]["e"] == "overlay"

    def test_list_replacement(self):
        """Lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        overlay = {"items": [4, 5]}
        result = deep_merge(base, overlay)
        assert result["items"] == [4, 5]

    def test_type_mismatch_dict_to_scalar(self):
        """When overlay has scalar where base has dict, overlay wins."""
        base = {"key": {"nested": "value"}}
        overlay = {"key": "string"}
        result = deep_merge(base, overlay)
        assert result["key"] == "string"

    def test_type_mismatch_scalar_to_dict(self):
        """When overlay has dict where base has scalar, overlay wins."""
        base = {"key": "string"}
        overlay = {"key": {"nested": "value"}}
        result = deep_merge(base, overlay)
        assert result["key"] == {"nested": "value"}

    def test_none_in_overlay(self):
        """None in overlay replaces base value."""
        base = {"key": "value"}
        overlay = {"key": None}
        result = deep_merge(base, overlay)
        assert result["key"] is None

    def test_preserves_key_order(self):
        """Base key order is preserved."""
        base = {"z": 1, "a": 2, "m": 3}
        overlay = {"a": 20, "x": 40}
        result = deep_merge(base, overlay)
        keys = list(result.keys())
        assert keys == ["z", "a", "m", "x"]

    def test_original_dicts_unchanged(self):
        """Original dicts are not modified (immutability)."""
        base = {"key": "base", "nested": {"inner": "original"}}
        overlay = {"key": "overlay"}

        result = deep_merge(base, overlay)

        assert base["key"] == "base"
        assert base["nested"]["inner"] == "original"
        assert result["key"] == "overlay"

    def test_nested_dicts_copied(self):
        """Nested dicts are copied, not shared references."""
        base = {"nested": {"value": 1}}
        overlay = {}

        result = deep_merge(base, overlay)
        result["nested"]["value"] = 999

        assert base["nested"]["value"] == 1

    def test_overlay_nested_dicts_deeply_copied(self):
        """Overlay nested dicts are deeply copied, not shallow copied."""
        base = {}
        overlay = {"nested": {"deep": {"value": 1}}}

        result = deep_merge(base, overlay)
        # Modify deeply nested value in result
        result["nested"]["deep"]["value"] = 999

        # Original overlay must be unchanged (requires deepcopy, not copy)
        assert overlay["nested"]["deep"]["value"] == 1


# =============================================================================
# build_effective_config Tests
# =============================================================================


class TestBuildEffectiveConfig:
    """Tests for build_effective_config function."""

    def test_defaults_only(self):
        """With only defaults, returns defaults copy."""
        defaults = {"key": "default"}
        result = build_effective_config(defaults)
        assert result == {"key": "default"}

    def test_profile_overrides_defaults(self):
        """Profile values override defaults."""
        defaults = {"key": "default", "other": "preserved"}
        profile = {"key": "profile"}
        result = build_effective_config(defaults, profile=profile)
        assert result == {"key": "profile", "other": "preserved"}

    def test_repo_overrides_profile(self):
        """Repo config overrides profile."""
        defaults = {"key": "default"}
        profile = {"key": "profile"}
        repo_config = {"key": "repo"}
        result = build_effective_config(
            defaults, profile=profile, repo_config=repo_config
        )
        assert result == {"key": "repo"}

    def test_repo_overrides_defaults_without_profile(self):
        """Repo config overrides defaults when no profile."""
        defaults = {"key": "default"}
        repo_config = {"key": "repo"}
        result = build_effective_config(defaults, repo_config=repo_config)
        assert result == {"key": "repo"}

    def test_merge_order_correct(self):
        """Merge order: defaults < profile < repo_config."""
        defaults = {"a": "defaults", "b": "defaults", "c": "defaults"}
        profile = {"b": "profile", "c": "profile"}
        repo_config = {"c": "repo"}

        result = build_effective_config(
            defaults, profile=profile, repo_config=repo_config
        )

        assert result["a"] == "defaults"
        assert result["b"] == "profile"
        assert result["c"] == "repo"

    def test_none_profile_ignored(self):
        """None profile is treated as no profile."""
        defaults = {"key": "default"}
        result = build_effective_config(defaults, profile=None)
        assert result == {"key": "default"}

    def test_none_repo_config_ignored(self):
        """None repo_config is treated as no repo config."""
        defaults = {"key": "default"}
        result = build_effective_config(defaults, repo_config=None)
        assert result == {"key": "default"}

    def test_nested_merge_across_layers(self):
        """Nested structures merge correctly across all layers."""
        defaults = {
            "java": {
                "version": "17",
                "tools": {"jacoco": True, "checkstyle": True},
            }
        }
        profile = {
            "java": {
                "tools": {"jacoco": True, "pmd": True},  # jacoco same, add pmd
            }
        }
        repo_config = {
            "java": {
                "version": "21",  # Override version
                "tools": {"checkstyle": False},  # Disable checkstyle
            }
        }

        result = build_effective_config(
            defaults, profile=profile, repo_config=repo_config
        )

        assert result["java"]["version"] == "21"
        assert result["java"]["tools"]["jacoco"] is True
        assert result["java"]["tools"]["checkstyle"] is False
        assert result["java"]["tools"]["pmd"] is True

    def test_defaults_deeply_copied(self):
        """Defaults are deeply copied, not shallow copied."""
        defaults = {"nested": {"deep": {"value": 1}}}

        result = build_effective_config(defaults)
        # Modify deeply nested value in result
        result["nested"]["deep"]["value"] = 999

        # Original defaults must be unchanged (requires deepcopy, not copy)
        assert defaults["nested"]["deep"]["value"] == 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestConfigIntegration:
    """Integration tests for config module workflow."""

    def test_full_workflow(self, tmp_path: Path):
        """Test complete workflow: create, save, load, merge."""
        paths = PathConfig(root=str(tmp_path))

        # Setup directories
        ensure_dirs(paths)

        # Create defaults
        defaults_file = Path(paths.defaults_file)
        defaults_file.write_text(
            yaml.dump(
                {
                    "java": {"version": "17", "tools": {"jacoco": True}},
                }
            )
        )

        # Create profile
        profiles_dir = Path(paths.profiles_dir)
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "security.yaml").write_text(
            yaml.dump(
                {
                    "java": {"tools": {"semgrep": True}},
                }
            )
        )

        # Create repo config
        save_repo_config(
            paths,
            "my-repo",
            {
                "repo": {"name": "my-repo"},
                "java": {"version": "21"},
            },
        )

        # Load and merge
        defaults = load_defaults(paths)
        profile = load_profile(paths, "security")
        repo_config = load_repo_config(paths, "my-repo")
        effective = build_effective_config(defaults, profile, repo_config)

        # Verify merge result
        assert effective["repo"]["name"] == "my-repo"
        assert effective["java"]["version"] == "21"
        assert effective["java"]["tools"]["jacoco"] is True
        assert effective["java"]["tools"]["semgrep"] is True

    def test_list_and_load_all_repos(self, tmp_path: Path):
        """Test listing repos and loading each one."""
        paths = PathConfig(root=str(tmp_path))
        repos_dir = Path(paths.repos_dir)
        repos_dir.mkdir(parents=True)

        # Create multiple repos
        for name in ["alpha", "beta", "gamma"]:
            (repos_dir / f"{name}.yaml").write_text(yaml.dump({"name": name}))

        # List and load each
        repos = list_repos(paths)
        assert len(repos) == 3

        for repo in repos:
            config = load_repo_config(paths, repo)
            assert config["name"] == repo

    def test_real_profiles_loadable(self):
        """Test that real profiles in templates/profiles/ are loadable."""
        # Use real project root
        paths = PathConfig(root=".")

        profiles = list_profiles(paths)
        assert len(profiles) >= 12  # We have 12 profiles

        for profile in profiles:
            data = load_profile(paths, profile)
            assert isinstance(data, dict)
            assert len(data) > 0  # Each profile has content
