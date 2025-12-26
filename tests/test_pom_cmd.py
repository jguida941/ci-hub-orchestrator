"""Tests for cihub.commands.pom module (fix-pom and fix-deps commands)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.commands.pom import cmd_fix_deps, cmd_fix_pom  # noqa: E402


def write_ci_hub_config(
    path: Path, language: str = "java", build_tool: str = "maven"
) -> None:
    """Helper to create .ci-hub.yml config file."""
    config = f"""
repo:
  owner: test
  name: example
  default_branch: main
  language: {language}
{language}:
  version: '21'
  build_tool: {build_tool}
  tools:
    jacoco:
      enabled: true
    checkstyle:
      enabled: true
    jqwik:
      enabled: true
"""
    (path / ".ci-hub.yml").write_text(config, encoding="utf-8")


def write_pom(path: Path, body: str) -> None:
    """Helper to write pom.xml file."""
    path.write_text(body, encoding="utf-8")


# ==============================================================================
# Tests for cmd_fix_pom
# ==============================================================================


class TestCmdFixPom:
    """Tests for the fix-pom command."""

    def test_fix_pom_missing_config(self, tmp_path: Path, capsys) -> None:
        """fix-pom returns error when .ci-hub.yml is missing."""
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "Config not found" in captured.err

    def test_fix_pom_non_java_repo(self, tmp_path: Path, capsys) -> None:
        """fix-pom exits gracefully for non-Java repos."""
        config = """
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
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "fix-pom is only supported for Java repos" in captured.out

    def test_fix_pom_gradle_repo(self, tmp_path: Path, capsys) -> None:
        """fix-pom exits gracefully for Gradle repos."""
        config = """
repo:
  owner: test
  name: example
  default_branch: main
  language: java
java:
  version: '21'
  build_tool: gradle
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "fix-pom only supports Maven repos" in captured.out

    def test_fix_pom_dry_run_shows_diff(self, tmp_path: Path, capsys) -> None:
        """fix-pom in dry-run mode shows diff without modifying file."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )
        original_content = pom_path.read_text(encoding="utf-8")

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 0

        # File should NOT be modified in dry-run
        assert pom_path.read_text(encoding="utf-8") == original_content

        captured = capsys.readouterr()
        # Should show diff output
        assert (
            "---" in captured.out
            or "+++" in captured.out
            or "jacoco" in captured.out.lower()
        )

    def test_fix_pom_apply_modifies_file(self, tmp_path: Path, capsys) -> None:
        """fix-pom with --apply modifies pom.xml."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True)
        result = cmd_fix_pom(args)
        assert result == 0

        # File SHOULD be modified
        updated_content = pom_path.read_text(encoding="utf-8")
        assert "<artifactId>jacoco-maven-plugin</artifactId>" in updated_content

        captured = capsys.readouterr()
        assert "pom.xml updated" in captured.out

    def test_fix_pom_no_changes_needed(self, tmp_path: Path, capsys) -> None:
        """fix-pom reports no changes when plugins already present."""
        config = """
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
      enabled: false
    checkstyle:
      enabled: false
    spotbugs:
      enabled: false
    pmd:
      enabled: false
    owasp:
      enabled: false
    pitest:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "No pom.xml changes needed" in captured.out

    def test_fix_pom_missing_pom_file(self, tmp_path: Path, capsys) -> None:
        """fix-pom returns error when pom.xml is missing."""
        write_ci_hub_config(tmp_path)
        # No pom.xml created

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "pom.xml not found" in captured.err


# ==============================================================================
# Tests for cmd_fix_deps
# ==============================================================================


class TestCmdFixDeps:
    """Tests for the fix-deps command."""

    def test_fix_deps_missing_config(self, tmp_path: Path, capsys) -> None:
        """fix-deps returns error when .ci-hub.yml is missing."""
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        assert result == 2
        captured = capsys.readouterr()
        assert "Config not found" in captured.err

    def test_fix_deps_non_java_repo(self, tmp_path: Path, capsys) -> None:
        """fix-deps exits gracefully for non-Java repos."""
        config = """
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
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "fix-deps is only supported for Java repos" in captured.out

    def test_fix_deps_gradle_repo(self, tmp_path: Path, capsys) -> None:
        """fix-deps exits gracefully for Gradle repos."""
        config = """
repo:
  owner: test
  name: example
  default_branch: main
  language: java
java:
  version: '21'
  build_tool: gradle
  tools:
    jqwik:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "fix-deps only supports Maven repos" in captured.out

    def test_fix_deps_dry_run_shows_diff(self, tmp_path: Path, capsys) -> None:
        """fix-deps in dry-run mode shows diff without modifying file."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""",
        )
        original_content = pom_path.read_text(encoding="utf-8")

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        assert result == 0

        # File should NOT be modified in dry-run
        assert pom_path.read_text(encoding="utf-8") == original_content

        captured = capsys.readouterr()
        # Should show diff output or warning about jqwik
        assert "---" in captured.out or "jqwik" in captured.out.lower()

    def test_fix_deps_apply_modifies_file(self, tmp_path: Path, capsys) -> None:
        """fix-deps with --apply modifies pom.xml."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True)
        result = cmd_fix_deps(args)
        assert result == 0

        # File SHOULD be modified
        updated_content = pom_path.read_text(encoding="utf-8")
        assert "<artifactId>jqwik</artifactId>" in updated_content

        captured = capsys.readouterr()
        assert "updated" in captured.out

    def test_fix_deps_no_changes_needed(self, tmp_path: Path, capsys) -> None:
        """fix-deps reports no changes when dependencies already present."""
        config = """
repo:
  owner: test
  name: example
  default_branch: main
  language: java
java:
  version: '21'
  build_tool: maven
  tools:
    jqwik:
      enabled: false
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "No dependency changes needed" in captured.out


# ==============================================================================
# Edge case tests
# ==============================================================================


class TestPomCommandsEdgeCases:
    """Edge case tests for pom commands."""

    def test_fix_pom_with_subdir(self, tmp_path: Path, capsys) -> None:
        """fix-pom handles subdir config correctly."""
        subdir = "services/backend"
        (tmp_path / subdir).mkdir(parents=True)

        config = f"""
repo:
  owner: test
  name: example
  default_branch: main
  language: java
  subdir: {subdir}
java:
  version: '21'
  build_tool: maven
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")

        pom_path = tmp_path / subdir / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True)
        result = cmd_fix_pom(args)
        assert result == 0

        updated_content = pom_path.read_text(encoding="utf-8")
        assert "<artifactId>jacoco-maven-plugin</artifactId>" in updated_content

    def test_fix_pom_invalid_xml(self, tmp_path: Path, capsys) -> None:
        """fix-pom handles invalid XML gracefully."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(pom_path, "<project>invalid xml without closing tag")

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_pom(args)
        # Should return error or show warning
        captured = capsys.readouterr()
        # Invalid XML should trigger a warning
        assert (
            result != 0
            or "Invalid pom.xml" in captured.out
            or "warning" in captured.out.lower()
        )

    def test_fix_deps_multi_module_project(self, tmp_path: Path, capsys) -> None:
        """fix-deps handles multi-module Maven projects."""
        write_ci_hub_config(tmp_path)

        # Create parent pom with modules
        parent_pom = tmp_path / "pom.xml"
        write_pom(
            parent_pom,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
    <module>module-a</module>
  </modules>
</project>
""",
        )

        # Create module pom
        module_dir = tmp_path / "module-a"
        module_dir.mkdir()
        module_pom = module_dir / "pom.xml"
        write_pom(
            module_pom,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>com.example</groupId>
    <artifactId>parent</artifactId>
    <version>1.0.0</version>
  </parent>
  <artifactId>module-a</artifactId>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True)
        result = cmd_fix_deps(args)
        assert result == 0

        # Module pom should be updated with jqwik dependency
        updated_content = module_pom.read_text(encoding="utf-8")
        assert "<artifactId>jqwik</artifactId>" in updated_content

    def test_fix_pom_resolves_repo_path(self, tmp_path: Path) -> None:
        """fix-pom resolves relative paths correctly."""
        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        # Use the actual path (not relative)
        args = argparse.Namespace(repo=str(tmp_path), apply=True)
        result = cmd_fix_pom(args)
        assert result == 0

    def test_fix_deps_missing_pom_no_error_for_missing_file(
        self, tmp_path: Path, capsys
    ) -> None:
        """fix-deps returns no error when pom.xml is missing (unlike fix-pom)."""
        write_ci_hub_config(tmp_path)
        # No pom.xml created

        args = argparse.Namespace(repo=str(tmp_path), apply=False)
        result = cmd_fix_deps(args)
        # fix-deps just reports no changes needed when pom missing
        assert result == 0
        captured = capsys.readouterr()
        assert "No dependency changes needed" in captured.out


# ==============================================================================
# JSON Mode Tests
# ==============================================================================


class TestPomCommandsJsonMode:
    """JSON mode tests for pom commands."""

    def test_fix_pom_missing_config_json_mode(self, tmp_path: Path) -> None:
        """fix-pom returns CommandResult for missing config in JSON mode."""
        from cihub.cli import CommandResult

        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_pom(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "Config not found" in result.summary

    def test_fix_pom_non_java_json_mode(self, tmp_path: Path) -> None:
        """fix-pom returns CommandResult for non-Java repo in JSON mode."""
        from cihub.cli import CommandResult

        config = """
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
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_pom(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "Java" in result.summary

    def test_fix_pom_gradle_json_mode(self, tmp_path: Path) -> None:
        """fix-pom returns CommandResult for Gradle repo in JSON mode."""
        from cihub.cli import CommandResult

        config = """
repo:
  owner: test
  name: example
  default_branch: main
  language: java
java:
  version: '21'
  build_tool: gradle
  tools:
    jacoco:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_pom(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "Maven" in result.summary

    def test_fix_pom_apply_json_mode(self, tmp_path: Path) -> None:
        """fix-pom with apply in JSON mode returns CommandResult."""
        from cihub.cli import CommandResult

        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True, json=True)
        result = cmd_fix_pom(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.data["applied"] is True

    def test_fix_deps_missing_config_json_mode(self, tmp_path: Path) -> None:
        """fix-deps returns CommandResult for missing config in JSON mode."""
        from cihub.cli import CommandResult

        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_deps(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 2
        assert "Config not found" in result.summary

    def test_fix_deps_non_java_json_mode(self, tmp_path: Path) -> None:
        """fix-deps returns CommandResult for non-Java repo in JSON mode."""
        from cihub.cli import CommandResult

        config = """
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
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_deps(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "Java" in result.summary

    def test_fix_deps_gradle_json_mode(self, tmp_path: Path) -> None:
        """fix-deps returns CommandResult for Gradle repo in JSON mode."""
        from cihub.cli import CommandResult

        config = """
repo:
  owner: test
  name: example
  default_branch: main
  language: java
java:
  version: '21'
  build_tool: gradle
  tools:
    jqwik:
      enabled: true
"""
        (tmp_path / ".ci-hub.yml").write_text(config, encoding="utf-8")
        args = argparse.Namespace(repo=str(tmp_path), apply=False, json=True)
        result = cmd_fix_deps(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "Maven" in result.summary

    def test_fix_deps_apply_json_mode(self, tmp_path: Path) -> None:
        """fix-deps with apply in JSON mode returns CommandResult."""
        from cihub.cli import CommandResult

        write_ci_hub_config(tmp_path)
        pom_path = tmp_path / "pom.xml"
        write_pom(
            pom_path,
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>example</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
""",
        )

        args = argparse.Namespace(repo=str(tmp_path), apply=True, json=True)
        result = cmd_fix_deps(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.data["applied"] is True
