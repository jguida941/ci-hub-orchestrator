"""Tests for apply_profile.py - Profile application functionality."""

import sys
from pathlib import Path

import pytest
import yaml

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.apply_profile import deep_merge, load_yaml  # noqa: E402


class TestLoadYaml:
    """Tests for load_yaml function."""

    def test_load_nonexistent_file(self, tmp_path: Path):
        """Loading nonexistent file returns empty dict."""
        result = load_yaml(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_load_valid_yaml(self, tmp_path: Path):
        """Loading valid YAML returns parsed dict."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nnested:\n  inner: data")

        result = load_yaml(yaml_file)
        assert result == {"key": "value", "nested": {"inner": "data"}}

    def test_load_empty_file(self, tmp_path: Path):
        """Loading empty file returns empty dict."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_yaml(yaml_file)
        assert result == {}

    def test_load_null_file(self, tmp_path: Path):
        """Loading file with null content returns empty dict."""
        yaml_file = tmp_path / "null.yaml"
        yaml_file.write_text("null")

        result = load_yaml(yaml_file)
        assert result == {}

    def test_load_non_mapping_raises(self, tmp_path: Path):
        """Loading non-mapping YAML raises ValueError."""
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(ValueError, match="must be a mapping"):
            load_yaml(yaml_file)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_empty_base_and_overlay(self):
        """Merging two empty dicts returns empty dict."""
        result = deep_merge({}, {})
        assert result == {}

    def test_empty_base(self):
        """Merging empty base with overlay returns overlay."""
        overlay = {"key": "value"}
        result = deep_merge({}, overlay)
        assert result == {"key": "value"}

    def test_empty_overlay(self):
        """Merging base with empty overlay returns base."""
        base = {"key": "value"}
        result = deep_merge(base, {})
        assert result == {"key": "value"}

    def test_simple_override(self):
        """Overlay values override base values."""
        base = {"key": "base_value"}
        overlay = {"key": "overlay_value"}
        result = deep_merge(base, overlay)
        assert result == {"key": "overlay_value"}

    def test_add_new_keys(self):
        """Overlay adds keys not in base."""
        base = {"a": 1}
        overlay = {"b": 2}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 2}

    def test_nested_merge(self):
        """Nested dicts are merged recursively."""
        base = {
            "outer": {
                "inner": "base_value",
                "base_only": "preserved",
            }
        }
        overlay = {
            "outer": {
                "inner": "overlay_value",
                "overlay_only": "added",
            }
        }
        result = deep_merge(base, overlay)

        assert result["outer"]["inner"] == "overlay_value"
        assert result["outer"]["base_only"] == "preserved"
        assert result["outer"]["overlay_only"] == "added"

    def test_list_replacement(self):
        """Lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        overlay = {"items": [4, 5]}
        result = deep_merge(base, overlay)
        assert result == {"items": [4, 5]}

    def test_type_mismatch_overlay_wins(self):
        """When types differ, overlay wins."""
        base = {"key": {"nested": "value"}}
        overlay = {"key": "simple_string"}
        result = deep_merge(base, overlay)
        assert result == {"key": "simple_string"}

    def test_preserves_base_key_order(self):
        """Base key order is preserved, overlay-only keys appended."""
        base = {"z": 1, "a": 2, "m": 3}
        overlay = {"a": 20, "x": 40}
        result = deep_merge(base, overlay)

        keys = list(result.keys())
        assert keys == ["z", "a", "m", "x"]

    def test_deep_nested_merge(self):
        """Deeply nested structures merge correctly."""
        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "base_value": "preserved",
                    }
                }
            }
        }
        overlay = {
            "level1": {
                "level2": {
                    "level3": {
                        "overlay_value": "added",
                    }
                }
            }
        }
        result = deep_merge(base, overlay)

        assert result["level1"]["level2"]["level3"]["base_value"] == "preserved"
        assert result["level1"]["level2"]["level3"]["overlay_value"] == "added"

    def test_original_dicts_unchanged(self):
        """Original dicts are not modified."""
        base = {"key": "base"}
        overlay = {"key": "overlay"}

        result = deep_merge(base, overlay)

        assert base == {"key": "base"}
        assert overlay == {"key": "overlay"}
        assert result == {"key": "overlay"}


class TestProfileApplication:
    """Integration tests for profile application workflow."""

    def test_profile_provides_defaults(self, tmp_path: Path):
        """Profile values provide defaults for target config."""
        profile = tmp_path / "profile.yaml"
        profile.write_text(
            yaml.dump(
                {
                    "language": "java",
                    "java": {
                        "version": "21",
                        "tools": {"checkstyle": {"enabled": True}},
                    },
                }
            )
        )

        target = tmp_path / "target.yaml"
        target.write_text(
            yaml.dump(
                {
                    "repo": {"name": "my-repo"},
                }
            )
        )

        profile_data = load_yaml(profile)
        target_data = load_yaml(target)
        merged = deep_merge(profile_data, target_data)

        assert merged["language"] == "java"
        assert merged["java"]["version"] == "21"
        assert merged["repo"]["name"] == "my-repo"

    def test_target_overrides_profile(self, tmp_path: Path):
        """Target config values override profile defaults."""
        profile = tmp_path / "profile.yaml"
        profile.write_text(
            yaml.dump(
                {
                    "java": {
                        "version": "21",
                        "tools": {"checkstyle": {"enabled": True}},
                    },
                }
            )
        )

        target = tmp_path / "target.yaml"
        target.write_text(
            yaml.dump(
                {
                    "java": {
                        "version": "17",  # Override profile's version
                    },
                }
            )
        )

        profile_data = load_yaml(profile)
        target_data = load_yaml(target)
        merged = deep_merge(profile_data, target_data)

        assert merged["java"]["version"] == "17"  # Target wins
        assert merged["java"]["tools"]["checkstyle"]["enabled"] is True  # Profile preserved

    def test_tool_toggle_override(self, tmp_path: Path):
        """Target can disable tools enabled by profile."""
        profile = tmp_path / "profile.yaml"
        profile.write_text(
            yaml.dump(
                {
                    "python": {
                        "tools": {
                            "mypy": {"enabled": True},
                            "black": {"enabled": True},
                        },
                    },
                }
            )
        )

        target = tmp_path / "target.yaml"
        target.write_text(
            yaml.dump(
                {
                    "python": {
                        "tools": {
                            "mypy": {"enabled": False},  # Disable mypy
                        },
                    },
                }
            )
        )

        profile_data = load_yaml(profile)
        target_data = load_yaml(target)
        merged = deep_merge(profile_data, target_data)

        assert merged["python"]["tools"]["mypy"]["enabled"] is False  # Disabled by target
        assert merged["python"]["tools"]["black"]["enabled"] is True  # Preserved from profile


class TestMain:
    """Tests for main() CLI function."""

    def test_main_applies_profile(self, tmp_path: Path, monkeypatch, capsys):
        """Main applies profile to target and writes output."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("language: python\npython:\n  version: '3.11'")

        target = tmp_path / "target.yaml"
        target.write_text("repo:\n  name: test-repo")

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target)],
        )

        main()

        # Verify output file was updated
        result = yaml.safe_load(target.read_text())
        assert result["language"] == "python"
        assert result["python"]["version"] == "3.11"
        assert result["repo"]["name"] == "test-repo"

        captured = capsys.readouterr()
        assert "Profile applied" in captured.out

    def test_main_with_output_option(self, tmp_path: Path, monkeypatch):
        """Main writes to specified output path."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("language: java")

        target = tmp_path / "target.yaml"
        target.write_text("repo:\n  name: my-repo")

        output = tmp_path / "output" / "merged.yaml"

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target), "-o", str(output)],
        )

        main()

        assert output.exists()
        result = yaml.safe_load(output.read_text())
        assert result["language"] == "java"
        assert result["repo"]["name"] == "my-repo"

        # Original target unchanged
        original = yaml.safe_load(target.read_text())
        assert "language" not in original

    def test_main_creates_parent_dirs(self, tmp_path: Path, monkeypatch):
        """Main creates parent directories for output."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("key: value")

        target = tmp_path / "target.yaml"
        target.write_text("")

        output = tmp_path / "deep" / "nested" / "output.yaml"

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target), "-o", str(output)],
        )

        main()

        assert output.exists()
        assert output.parent.exists()

    def test_main_nonexistent_profile(self, tmp_path: Path, monkeypatch):
        """Main handles nonexistent profile (returns empty dict)."""
        from scripts.apply_profile import main

        profile = tmp_path / "nonexistent.yaml"
        target = tmp_path / "target.yaml"
        target.write_text("existing: data")

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target)],
        )

        main()

        result = yaml.safe_load(target.read_text())
        assert result == {"existing": "data"}

    def test_main_nonexistent_target(self, tmp_path: Path, monkeypatch):
        """Main handles nonexistent target (returns empty dict)."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("default: value")

        target = tmp_path / "new_target.yaml"

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target)],
        )

        main()

        assert target.exists()
        result = yaml.safe_load(target.read_text())
        assert result == {"default": "value"}

    def test_main_atomic_write(self, tmp_path: Path, monkeypatch):
        """Main uses atomic write pattern."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("key: value")

        target = tmp_path / "target.yaml"
        target.write_text("old: data")

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target)],
        )

        main()

        # No temp file should remain
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_main_preserves_yaml_formatting(self, tmp_path: Path, monkeypatch):
        """Main outputs readable YAML (not flow style)."""
        from scripts.apply_profile import main

        profile = tmp_path / "profile.yaml"
        profile.write_text("nested:\n  key: value\n  list:\n    - item1\n    - item2")

        target = tmp_path / "target.yaml"
        target.write_text("")

        monkeypatch.setattr(
            "sys.argv",
            ["apply_profile.py", str(profile), str(target)],
        )

        main()

        content = target.read_text()
        # Should be block style, not {nested: {key: value}}
        assert "nested:" in content
        assert "{" not in content or "}" not in content
