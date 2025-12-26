"""Tests for POM parsing functions in cihub/cli.py.

These tests target high-complexity functions identified in the SDLC analysis:
- parse_pom_plugins()
- parse_pom_dependencies()
- collect_java_pom_warnings()
- insert_plugins_into_pom()
- insert_dependencies_into_pom()
"""

from __future__ import annotations

import sys
from pathlib import Path

import defusedxml.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.cli import (  # noqa: E402
    collect_java_pom_warnings,
    elem_text,
    get_xml_namespace,
    indent_block,
    insert_dependencies_into_pom,
    insert_plugins_into_pom,
    line_indent,
    ns_tag,
    parse_pom_dependencies,
    parse_pom_plugins,
    parse_xml_file,
    parse_xml_text,
    plugin_matches,
)

# ==============================================================================
# Tests for XML utility functions
# ==============================================================================


class TestXmlUtilities:
    """Tests for low-level XML utilities."""

    def test_get_xml_namespace_with_namespace(self) -> None:
        """Extract namespace from element with namespace prefix."""
        xml = '<project xmlns="http://maven.apache.org/POM/4.0.0"></project>'
        root = ET.fromstring(xml)
        ns = get_xml_namespace(root)
        assert ns == "http://maven.apache.org/POM/4.0.0"

    def test_get_xml_namespace_without_namespace(self) -> None:
        """Return empty string for element without namespace."""
        xml = "<project></project>"
        root = ET.fromstring(xml)
        ns = get_xml_namespace(root)
        assert ns == ""

    def test_ns_tag_with_namespace(self) -> None:
        """Create namespaced tag."""
        result = ns_tag("http://maven.apache.org/POM/4.0.0", "build")
        assert result == "{http://maven.apache.org/POM/4.0.0}build"

    def test_ns_tag_without_namespace(self) -> None:
        """Return plain tag when namespace is empty."""
        result = ns_tag("", "build")
        assert result == "build"

    def test_elem_text_with_text(self) -> None:
        """Extract text from element."""
        elem = ET.fromstring("<groupId>org.example</groupId>")
        assert elem_text(elem) == "org.example"

    def test_elem_text_with_whitespace(self) -> None:
        """Strip whitespace from element text."""
        elem = ET.fromstring("<groupId>  org.example  </groupId>")
        assert elem_text(elem) == "org.example"

    def test_elem_text_none_element(self) -> None:
        """Return empty string for None element."""
        assert elem_text(None) == ""

    def test_elem_text_empty_element(self) -> None:
        """Return empty string for element without text."""
        elem = ET.fromstring("<groupId></groupId>")
        assert elem_text(elem) == ""


class TestParseXml:
    """Tests for XML parsing with security checks."""

    def test_parse_xml_text_valid(self) -> None:
        """Parse valid XML text."""
        elem = parse_xml_text("<project><build/></project>")
        assert elem.tag == "project"

    def test_parse_xml_text_rejects_doctype(self) -> None:
        """Reject XML with DOCTYPE declaration."""
        with pytest.raises(ValueError, match="disallowed DTD"):
            parse_xml_text("<!DOCTYPE foo><project></project>")

    def test_parse_xml_text_rejects_entity(self) -> None:
        """Reject XML with ENTITY declaration."""
        with pytest.raises(ValueError, match="disallowed DTD"):
            parse_xml_text('<!ENTITY foo "bar"><project></project>')

    def test_parse_xml_file_valid(self, tmp_path: Path) -> None:
        """Parse valid XML file."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><build/></project>", encoding="utf-8")
        elem = parse_xml_file(pom)
        assert elem.tag == "project"

    def test_parse_xml_file_invalid(self, tmp_path: Path) -> None:
        """Raise error for invalid XML file."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><unclosed>", encoding="utf-8")
        with pytest.raises(ET.ParseError):
            parse_xml_file(pom)


# ==============================================================================
# Tests for parse_pom_plugins
# ==============================================================================


class TestParsePomPlugins:
    """Tests for parse_pom_plugins function."""

    def test_parse_plugins_simple(self, tmp_path: Path) -> None:
        """Parse plugins from simple pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <plugins>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
""",
            encoding="utf-8",
        )
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert ("org.jacoco", "jacoco-maven-plugin") in plugins
        assert has_modules is False

    def test_parse_plugins_with_namespace(self, tmp_path: Path) -> None:
        """Parse plugins from pom.xml with Maven namespace."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-checkstyle-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
""",
            encoding="utf-8",
        )
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert ("org.apache.maven.plugins", "maven-checkstyle-plugin") in plugins

    def test_parse_plugins_in_plugin_management(self, tmp_path: Path) -> None:
        """Parse plugins from pluginManagement section."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <pluginManagement>
      <plugins>
        <plugin>
          <groupId>com.github.spotbugs</groupId>
          <artifactId>spotbugs-maven-plugin</artifactId>
        </plugin>
      </plugins>
    </pluginManagement>
  </build>
</project>
""",
            encoding="utf-8",
        )
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert len(plugins) == 0
        assert ("com.github.spotbugs", "spotbugs-maven-plugin") in plugins_mgmt

    def test_parse_plugins_multi_module(self, tmp_path: Path) -> None:
        """Detect multi-module project."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <modules>
    <module>core</module>
    <module>web</module>
  </modules>
</project>
""",
            encoding="utf-8",
        )
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert has_modules is True

    def test_parse_plugins_missing_group_id(self, tmp_path: Path) -> None:
        """Handle plugin without groupId."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-compiler-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
""",
            encoding="utf-8",
        )
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert ("", "maven-compiler-plugin") in plugins

    def test_parse_plugins_invalid_xml(self, tmp_path: Path) -> None:
        """Return error for invalid XML."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><unclosed>", encoding="utf-8")
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is not None
        assert "Invalid pom.xml" in error

    def test_parse_plugins_empty_pom(self, tmp_path: Path) -> None:
        """Handle empty pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project></project>", encoding="utf-8")
        plugins, plugins_mgmt, has_modules, error = parse_pom_plugins(pom)
        assert error is None
        assert len(plugins) == 0
        assert len(plugins_mgmt) == 0


# ==============================================================================
# Tests for parse_pom_dependencies
# ==============================================================================


class TestParsePomDependencies:
    """Tests for parse_pom_dependencies function."""

    def test_parse_dependencies_simple(self, tmp_path: Path) -> None:
        """Parse dependencies from simple pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <dependencies>
    <dependency>
      <groupId>net.jqwik</groupId>
      <artifactId>jqwik</artifactId>
    </dependency>
  </dependencies>
</project>
""",
            encoding="utf-8",
        )
        deps, deps_mgmt, error = parse_pom_dependencies(pom)
        assert error is None
        assert ("net.jqwik", "jqwik") in deps

    def test_parse_dependencies_with_namespace(self, tmp_path: Path) -> None:
        """Parse dependencies from pom.xml with Maven namespace."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
    </dependency>
  </dependencies>
</project>
""",
            encoding="utf-8",
        )
        deps, deps_mgmt, error = parse_pom_dependencies(pom)
        assert error is None
        assert ("org.junit.jupiter", "junit-jupiter") in deps

    def test_parse_dependencies_in_management(self, tmp_path: Path) -> None:
        """Parse dependencies from dependencyManagement section."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.springframework</groupId>
        <artifactId>spring-core</artifactId>
      </dependency>
    </dependencies>
  </dependencyManagement>
</project>
""",
            encoding="utf-8",
        )
        deps, deps_mgmt, error = parse_pom_dependencies(pom)
        assert error is None
        assert len(deps) == 0
        assert ("org.springframework", "spring-core") in deps_mgmt

    def test_parse_dependencies_invalid_xml(self, tmp_path: Path) -> None:
        """Return error for invalid XML."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project><unclosed>", encoding="utf-8")
        deps, deps_mgmt, error = parse_pom_dependencies(pom)
        assert error is not None
        assert "Invalid pom.xml" in error


# ==============================================================================
# Tests for plugin_matches
# ==============================================================================


class TestPluginMatches:
    """Tests for plugin_matches function."""

    def test_exact_match(self) -> None:
        """Match plugin with exact groupId and artifactId."""
        plugins = {("org.jacoco", "jacoco-maven-plugin")}
        assert plugin_matches(plugins, "org.jacoco", "jacoco-maven-plugin") is True

    def test_no_match(self) -> None:
        """No match for different plugin."""
        plugins = {("org.jacoco", "jacoco-maven-plugin")}
        assert (
            plugin_matches(plugins, "com.github.spotbugs", "spotbugs-maven-plugin")
            is False
        )

    def test_match_with_empty_group(self) -> None:
        """Match plugin with empty groupId in set."""
        plugins = {("", "maven-compiler-plugin")}
        assert (
            plugin_matches(plugins, "org.apache.maven.plugins", "maven-compiler-plugin")
            is True
        )

    def test_no_match_different_artifact(self) -> None:
        """No match when artifactId differs."""
        plugins = {("org.jacoco", "jacoco-maven-plugin")}
        assert plugin_matches(plugins, "org.jacoco", "different-plugin") is False


# ==============================================================================
# Tests for collect_java_pom_warnings
# ==============================================================================


class TestCollectJavaPomWarnings:
    """Tests for collect_java_pom_warnings function."""

    def test_missing_pom(self, tmp_path: Path) -> None:
        """Warn when pom.xml is missing."""
        config = {"java": {"build_tool": "maven"}}
        warnings, missing = collect_java_pom_warnings(tmp_path, config)
        assert any("pom.xml not found" in w for w in warnings)

    def test_gradle_project_skipped(self, tmp_path: Path) -> None:
        """Skip POM checks for Gradle projects."""
        pom = tmp_path / "pom.xml"
        pom.write_text("<project></project>", encoding="utf-8")
        config = {"java": {"build_tool": "gradle"}}
        warnings, missing = collect_java_pom_warnings(tmp_path, config)
        assert len(warnings) == 0
        assert len(missing) == 0

    def test_missing_enabled_plugin(self, tmp_path: Path) -> None:
        """Warn about missing plugin for enabled tool."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <plugins></plugins>
  </build>
</project>
""",
            encoding="utf-8",
        )
        config = {
            "java": {
                "build_tool": "maven",
                "tools": {
                    "jacoco": {"enabled": True},
                },
            }
        }
        warnings, missing = collect_java_pom_warnings(tmp_path, config)
        assert any("missing plugin" in w and "jacoco" in w for w in warnings)
        assert ("org.jacoco", "jacoco-maven-plugin") in missing

    def test_plugin_in_management_only(self, tmp_path: Path) -> None:
        """Warn when plugin is only in pluginManagement."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <pluginManagement>
      <plugins>
        <plugin>
          <groupId>org.jacoco</groupId>
          <artifactId>jacoco-maven-plugin</artifactId>
        </plugin>
      </plugins>
    </pluginManagement>
  </build>
</project>
""",
            encoding="utf-8",
        )
        config = {
            "java": {
                "build_tool": "maven",
                "tools": {
                    "jacoco": {"enabled": True},
                },
            }
        }
        warnings, missing = collect_java_pom_warnings(tmp_path, config)
        assert any("pluginManagement" in w for w in warnings)

    def test_missing_checkstyle_config(self, tmp_path: Path) -> None:
        """Warn about missing checkstyle config file."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-checkstyle-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
""",
            encoding="utf-8",
        )
        config = {
            "java": {
                "build_tool": "maven",
                "tools": {
                    "checkstyle": {
                        "enabled": True,
                        "config_file": "checkstyle.xml",
                    },
                },
            }
        }
        warnings, _ = collect_java_pom_warnings(tmp_path, config)
        assert any("checkstyle config file not found" in w for w in warnings)

    def test_subdir_project(self, tmp_path: Path) -> None:
        """Handle project in subdirectory."""
        subdir = tmp_path / "backend"
        subdir.mkdir()
        pom = subdir / "pom.xml"
        pom.write_text("<project></project>", encoding="utf-8")
        config = {
            "repo": {"subdir": "backend"},
            "java": {"build_tool": "maven"},
        }
        warnings, _ = collect_java_pom_warnings(tmp_path, config)
        # Should not warn about missing pom.xml since it exists in subdir
        assert not any("pom.xml not found" in w for w in warnings)


# ==============================================================================
# Tests for insert_plugins_into_pom
# ==============================================================================


class TestInsertPluginsIntoPom:
    """Tests for insert_plugins_into_pom function."""

    def test_insert_into_existing_plugins(self) -> None:
        """Insert plugin into existing <plugins> section."""
        pom_text = """<project>
  <build>
    <plugins>
      <plugin>
        <artifactId>existing-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>"""
        plugin_block = """<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
</plugin>"""
        result, success = insert_plugins_into_pom(pom_text, plugin_block)
        assert success is True
        assert "jacoco-maven-plugin" in result
        assert "existing-plugin" in result

    def test_insert_creates_plugins_section(self) -> None:
        """Create <plugins> section when only <build> exists."""
        pom_text = """<project>
  <build>
  </build>
</project>"""
        plugin_block = """<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
</plugin>"""
        result, success = insert_plugins_into_pom(pom_text, plugin_block)
        assert success is True
        assert "<plugins>" in result
        assert "jacoco-maven-plugin" in result

    def test_insert_creates_build_section(self) -> None:
        """Create <build> and <plugins> sections when neither exists."""
        pom_text = """<project>
</project>"""
        plugin_block = """<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
</plugin>"""
        result, success = insert_plugins_into_pom(pom_text, plugin_block)
        assert success is True
        assert "<build>" in result
        assert "<plugins>" in result
        assert "jacoco-maven-plugin" in result

    def test_insert_fails_without_project(self) -> None:
        """Fail when </project> is missing."""
        pom_text = """<project>
  <build>
"""
        plugin_block = "<plugin/>"
        result, success = insert_plugins_into_pom(pom_text, plugin_block)
        assert success is False
        assert result == pom_text


# ==============================================================================
# Tests for insert_dependencies_into_pom
# ==============================================================================


class TestInsertDependenciesIntoPom:
    """Tests for insert_dependencies_into_pom function."""

    def test_insert_into_existing_dependencies(self) -> None:
        """Insert dependency into existing <dependencies> section."""
        pom_text = """<project>
  <dependencies>
    <dependency>
      <artifactId>existing-dep</artifactId>
    </dependency>
  </dependencies>
</project>"""
        dep_block = """<dependency>
  <groupId>net.jqwik</groupId>
  <artifactId>jqwik</artifactId>
</dependency>"""
        result, success = insert_dependencies_into_pom(pom_text, dep_block)
        assert success is True
        assert "jqwik" in result
        assert "existing-dep" in result

    def test_insert_creates_dependencies_section(self) -> None:
        """Create <dependencies> section when it doesn't exist."""
        pom_text = """<project>
</project>"""
        dep_block = """<dependency>
  <groupId>net.jqwik</groupId>
  <artifactId>jqwik</artifactId>
</dependency>"""
        result, success = insert_dependencies_into_pom(pom_text, dep_block)
        assert success is True
        assert "<dependencies>" in result
        assert "jqwik" in result

    def test_insert_avoids_dependency_management(self) -> None:
        """Don't insert into dependencyManagement section."""
        pom_text = """<project>
  <dependencyManagement>
    <dependencies>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <artifactId>existing</artifactId>
    </dependency>
  </dependencies>
</project>"""
        dep_block = """<dependency>
  <groupId>net.jqwik</groupId>
  <artifactId>jqwik</artifactId>
</dependency>"""
        result, success = insert_dependencies_into_pom(pom_text, dep_block)
        assert success is True
        # Should insert into project dependencies, not dependencyManagement
        # Verify jqwik appears after dependencyManagement section
        dep_mgmt_end = result.find("</dependencyManagement>")
        jqwik_pos = result.find("jqwik")
        assert jqwik_pos > dep_mgmt_end


# ==============================================================================
# Tests for indentation utilities
# ==============================================================================


class TestIndentationUtilities:
    """Tests for indentation helper functions."""

    def test_line_indent_spaces(self) -> None:
        """Extract space indentation."""
        text = "  <build>\n    <plugins>\n  </build>"
        indent = line_indent(text, text.find("<plugins>"))
        assert indent == "    "

    def test_line_indent_tabs(self) -> None:
        """Extract tab indentation."""
        text = "\t<build>\n\t\t<plugins>\n\t</build>"
        indent = line_indent(text, text.find("<plugins>"))
        assert indent == "\t\t"

    def test_line_indent_start_of_line(self) -> None:
        """Handle text at start of line."""
        text = "<project>\n  <build>"
        indent = line_indent(text, 0)
        assert indent == ""

    def test_indent_block_simple(self) -> None:
        """Indent a simple block."""
        block = "<plugin>\n  <groupId>org.example</groupId>\n</plugin>"
        result = indent_block(block, "    ")
        lines = result.split("\n")
        assert lines[0] == "    <plugin>"
        assert lines[1] == "      <groupId>org.example</groupId>"
        assert lines[2] == "    </plugin>"

    def test_indent_block_preserves_empty_lines(self) -> None:
        """Don't add indent to empty lines."""
        block = "<plugin>\n\n</plugin>"
        result = indent_block(block, "  ")
        lines = result.split("\n")
        assert lines[1] == ""  # Empty line should stay empty
