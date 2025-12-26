"""Tests for validate_config.py - Config validation functionality."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_config import load_yaml, main, validate_config  # noqa: E402


class TestLoadYaml:
    """Tests for load_yaml function."""

    def test_load_valid_yaml(self, tmp_path: Path):
        """Loading valid YAML returns parsed dict."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nnested:\n  inner: data")

        result = load_yaml(yaml_file)
        assert result == {"key": "value", "nested": {"inner": "data"}}

    def test_load_nonexistent_file_raises(self, tmp_path: Path):
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Config not found"):
            load_yaml(tmp_path / "nonexistent.yaml")

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

        with pytest.raises(ValueError, match="must start with a YAML mapping"):
            load_yaml(yaml_file)


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config_returns_no_errors(self):
        """Valid config returns empty error list."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        config = {"name": "test"}

        errors = validate_config(config, schema)
        assert errors == []

    def test_invalid_type_returns_error(self):
        """Invalid type returns error message."""
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        }
        config = {"count": "not-an-int"}

        errors = validate_config(config, schema)
        assert len(errors) == 1
        assert "count" in errors[0]

    def test_missing_required_returns_error(self):
        """Missing required field returns error."""
        schema = {
            "type": "object",
            "properties": {"required_field": {"type": "string"}},
            "required": ["required_field"],
        }
        config = {}

        errors = validate_config(config, schema)
        assert len(errors) == 1
        assert "required_field" in errors[0]

    def test_nested_validation_error(self):
        """Nested validation errors include path."""
        schema = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {"inner": {"type": "integer"}},
                }
            },
        }
        config = {"outer": {"inner": "not-an-int"}}

        errors = validate_config(config, schema)
        assert len(errors) == 1
        assert "outer.inner" in errors[0]

    def test_multiple_errors_sorted(self):
        """Multiple errors are sorted by path."""
        schema = {
            "type": "object",
            "properties": {
                "a_field": {"type": "integer"},
                "b_field": {"type": "integer"},
            },
        }
        config = {"a_field": "wrong", "b_field": "also_wrong"}

        errors = validate_config(config, schema)
        assert len(errors) == 2
        # Errors should be sorted by path
        assert "a_field" in errors[0]
        assert "b_field" in errors[1]


class TestMain:
    """Tests for main CLI function."""

    def test_missing_schema_returns_error(self, tmp_path: Path, monkeypatch):
        """Missing schema file returns exit code 1."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value")

        monkeypatch.setattr(
            "sys.argv",
            [
                "validate_config.py",
                str(config_file),
                "--schema",
                str(tmp_path / "nonexistent.json"),
            ],
        )

        result = main()
        assert result == 1

    def test_invalid_schema_json_returns_error(self, tmp_path: Path, monkeypatch):
        """Schema that is not a JSON object returns exit code 1."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value")

        schema_file = tmp_path / "schema.json"
        schema_file.write_text('"just a string"')

        monkeypatch.setattr(
            "sys.argv",
            ["validate_config.py", str(config_file), "--schema", str(schema_file)],
        )

        result = main()
        assert result == 1

    def test_valid_config_returns_success(self, tmp_path: Path, monkeypatch, capsys):
        """Valid config returns exit code 0."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("language: python")

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {"language": {"type": "string"}},
                }
            )
        )

        monkeypatch.setattr(
            "sys.argv",
            ["validate_config.py", str(config_file), "--schema", str(schema_file)],
        )

        result = main()
        assert result == 0

        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_invalid_config_returns_failure(self, tmp_path: Path, monkeypatch, capsys):
        """Invalid config returns exit code 1 with errors."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("language: 123")  # Should be string

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {"language": {"type": "string"}},
                }
            )
        )

        monkeypatch.setattr(
            "sys.argv",
            ["validate_config.py", str(config_file), "--schema", str(schema_file)],
        )

        result = main()
        assert result == 1

        captured = capsys.readouterr()
        assert "Validation failed" in captured.err

    def test_extracts_language_from_repo_block(self, tmp_path: Path, monkeypatch):
        """Extracts language from repo block if not at root."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("repo:\n  language: python\n  name: test")

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "repo": {"type": "object"},
                    },
                }
            )
        )

        monkeypatch.setattr(
            "sys.argv",
            ["validate_config.py", str(config_file), "--schema", str(schema_file)],
        )

        result = main()
        assert result == 0
