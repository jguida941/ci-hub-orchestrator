"""Tests for cihub.commands module."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.detect import cmd_detect  # noqa: E402
from cihub.commands.init import cmd_init  # noqa: E402
from cihub.commands.update import cmd_update  # noqa: E402
from cihub.commands.validate import cmd_validate  # noqa: E402

# ==============================================================================
# Tests for cmd_detect
# ==============================================================================


class TestCmdDetect:
    """Tests for the detect command."""

    def test_detect_python_project(self, tmp_path: Path) -> None:
        """Detect Python project from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
        result = cmd_detect(args)
        assert result == 0

    def test_detect_java_project(self, tmp_path: Path) -> None:
        """Detect Java project from pom.xml."""
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False)
        result = cmd_detect(args)
        assert result == 0

    def test_detect_with_explain_flag(self, tmp_path: Path, capsys) -> None:
        """Detect with explain flag shows reasons."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "python"
        assert "reasons" in output

    def test_detect_with_override(self, tmp_path: Path, capsys) -> None:
        """Detect respects language override."""
        # Create Python markers but override to Java
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language="java", explain=False)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "java"


# ==============================================================================
# Tests for cmd_validate
# ==============================================================================


class TestCmdValidate:
    """Tests for the validate command."""

    def test_validate_missing_config(self, tmp_path: Path, capsys) -> None:
        """Validate returns error when config missing."""
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "Config not found" in captured.err

    def test_validate_valid_config(self, tmp_path: Path, capsys) -> None:
        """Validate returns success for valid config."""
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
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Config OK" in captured.out

    def test_validate_invalid_config_schema(self, tmp_path: Path, capsys) -> None:
        """Validate returns error for invalid schema."""
        # Missing required fields
        config_content = """
repo:
  owner: test
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Validation failed" in captured.out

    def test_validate_java_project_with_pom(self, tmp_path: Path, capsys) -> None:
        """Validate Java project checks POM warnings."""
        config_content = """
repo:
  owner: test
  name: example
  language: java
  default_branch: main
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        # Create a minimal valid pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        # Should succeed (may have POM warnings but not in strict mode)
        assert result in (0, 1)  # 0 if no warnings, 1 if warnings in strict mode

    def test_validate_java_strict_mode(self, tmp_path: Path, capsys) -> None:
        """Validate Java project in strict mode fails on POM warnings."""
        config_content = """
repo:
  owner: test
  name: example
  language: java
  default_branch: main
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config_content, encoding="utf-8")
        # Create pom.xml without jacoco plugin (will trigger warning)
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
"""
        (tmp_path / "pom.xml").write_text(pom_content, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=True)
        result = cmd_validate(args)
        # In strict mode, POM warnings cause failure
        assert result == 1


# ==============================================================================
# Additional edge case tests
# ==============================================================================


class TestDetectEdgeCases:
    """Edge case tests for detect command."""

    def test_detect_empty_directory(self, tmp_path: Path, capsys) -> None:
        """Detect returns EXIT_FAILURE for empty directory with no language markers."""
        from cihub.exit_codes import EXIT_FAILURE
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=False, json=False)
        result = cmd_detect(args)
        assert result == EXIT_FAILURE
        err = capsys.readouterr().err
        assert "Unable to detect language" in err

    def test_detect_empty_directory_with_override(self, tmp_path: Path, capsys) -> None:
        """Detect succeeds with language override even for empty directory."""
        args = argparse.Namespace(repo=str(tmp_path), language="python", explain=False)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "python"

    def test_detect_gradle_project(self, tmp_path: Path, capsys) -> None:
        """Detect Java project from build.gradle."""
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "java"
        assert "build.gradle" in str(output.get("reasons", []))

    def test_detect_requirements_txt_python(self, tmp_path: Path, capsys) -> None:
        """Detect Python from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "python"

    def test_detect_setup_py_python(self, tmp_path: Path, capsys) -> None:
        """Detect Python from setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), language=None, explain=True)
        result = cmd_detect(args)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["language"] == "python"


class TestValidateEdgeCases:
    """Edge case tests for validate command."""

    def test_validate_malformed_yaml(self, tmp_path: Path) -> None:
        """Validate raises ParserError for malformed YAML.

        This tests that yaml.ParserError propagates - the CLI layer should
        catch and convert to a proper exit code.
        """
        import yaml

        (tmp_path / ".ci-hub.yml").write_text("repo:\n  owner: test\n  - invalid list", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)

        # Malformed YAML should raise ParserError
        with pytest.raises(yaml.parser.ParserError, match="expected <block end>"):
            cmd_validate(args)

    def test_validate_empty_config(self, tmp_path: Path, capsys) -> None:
        """Validate handles empty config file."""
        (tmp_path / ".ci-hub.yml").write_text("", encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), strict=False)
        result = cmd_validate(args)
        # Empty config should fail validation
        assert result == 1


# ==============================================================================
# Tests for cmd_init
# ==============================================================================


class TestCmdInit:
    """Tests for the init command."""

    def test_init_python_project(self, tmp_path: Path, capsys) -> None:
        """Init creates config for Python project."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
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
        )
        result = cmd_init(args)
        assert result == 0
        # Check config was created
        config_path = tmp_path / ".ci-hub.yml"
        assert config_path.exists()
        # Check workflow was created
        workflow_path = tmp_path / ".github" / "workflows" / "hub-ci.yml"
        assert workflow_path.exists()

    def test_init_java_project(self, tmp_path: Path, capsys) -> None:
        """Init creates config for Java project."""
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
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
        )
        result = cmd_init(args)
        assert result == 0
        assert (tmp_path / ".ci-hub.yml").exists()
        assert (tmp_path / ".github" / "workflows" / "hub-ci.yml").exists()

    def test_init_dry_run(self, tmp_path: Path, capsys) -> None:
        """Init dry run prints config without writing."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
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
        )
        result = cmd_init(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Would write" in captured.out
        # Config should NOT be written in dry run
        assert not (tmp_path / ".ci-hub.yml").exists()

    def test_init_with_subdir(self, tmp_path: Path) -> None:
        """Init handles subdir parameter."""
        subdir = "services/backend"
        (tmp_path / subdir).mkdir(parents=True)
        (tmp_path / subdir / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language="python",
            owner="testowner",
            name="testrepo",
            branch="main",
            subdir=subdir,
            wizard=False,
            dry_run=False,
            apply=True,
            force=False,
            fix_pom=False,
        )
        result = cmd_init(args)
        assert result == 0
        config_path = tmp_path / ".ci-hub.yml"
        assert config_path.exists()
        config_text = config_path.read_text()
        assert subdir in config_text

    def test_init_missing_owner_uses_fallback(self, tmp_path: Path, capsys) -> None:
        """Init uses fallback owner when not provided and no git remote."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
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
        )
        result = cmd_init(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "could not detect repo owner" in captured.err
        config_text = (tmp_path / ".ci-hub.yml").read_text()
        assert "unknown" in config_text or tmp_path.name in config_text


# ==============================================================================
# Tests for cmd_update
# ==============================================================================


class TestCmdUpdate:
    """Tests for the update command."""

    def test_update_creates_config_if_missing(self, tmp_path: Path) -> None:
        """Update creates config if it doesn't exist."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
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
        )
        result = cmd_update(args)
        assert result == 0
        # Config should be created
        assert (tmp_path / ".ci-hub.yml").exists()
        assert (tmp_path / ".github" / "workflows" / "hub-ci.yml").exists()

    def test_update_existing_config(self, tmp_path: Path) -> None:
        """Update regenerates workflow from existing config."""
        # Create initial config
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
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
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
        )
        result = cmd_update(args)
        assert result == 0
        # Workflow should be created/updated
        workflow_path = tmp_path / ".github" / "workflows" / "hub-ci.yml"
        assert workflow_path.exists()

    def test_update_dry_run(self, tmp_path: Path, capsys) -> None:
        """Update dry run shows changes without writing."""
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
        (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
        args = argparse.Namespace(
            repo=str(tmp_path),
            language=None,
            owner=None,
            name=None,
            branch=None,
            subdir="",
            dry_run=True,
            apply=False,
            force=False,
            fix_pom=False,
        )
        result = cmd_update(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Would write" in captured.out
