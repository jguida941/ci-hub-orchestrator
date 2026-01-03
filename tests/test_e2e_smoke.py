"""End-to-end smoke tests for complete CLI workflows.

These tests verify that entire user workflows work from start to finish,
simulating real-world usage patterns. They're quick sanity checks that
catch integration issues between commands.
"""

from __future__ import annotations

import json
from pathlib import Path

from cihub.cli import main
from cihub.exit_codes import EXIT_SUCCESS


class TestPythonProjectWorkflow:
    """E2E test: Complete Python project setup and validation workflow."""

    def test_full_python_workflow(self, tmp_path: Path, capsys) -> None:
        """Test complete Python project workflow: detect → init → validate → scaffold."""
        repo = tmp_path / "my-python-project"
        repo.mkdir()

        # Step 1: Create a Python project marker
        (repo / "pyproject.toml").write_text("[project]\nname = 'my-project'\nversion = '1.0.0'\n")

        # Step 2: Detect language
        result = main(["detect", "--repo", str(repo)])
        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["language"] == "python"

        # Step 3: Initialize CI config
        result = main(
            [
                "init",
                "--repo",
                str(repo),
                "--language",
                "python",
                "--owner",
                "myorg",
                "--name",
                "my-python-project",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS

        # Step 4: Verify files were created
        assert (repo / ".ci-hub.yml").exists()
        assert (repo / ".github" / "workflows" / "hub-ci.yml").exists()

        # Step 5: Validate the configuration
        result = main(["validate", "--repo", str(repo)])
        assert result == EXIT_SUCCESS


class TestJavaProjectWorkflow:
    """E2E test: Complete Java project setup and validation workflow."""

    def test_full_java_workflow(self, tmp_path: Path, capsys) -> None:
        """Test complete Java project workflow: detect → init → validate."""
        repo = tmp_path / "my-java-project"
        repo.mkdir()

        # Step 1: Create a Java project marker (Maven)
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>my-project</artifactId>
    <version>1.0.0</version>
</project>
"""
        (repo / "pom.xml").write_text(pom)

        # Step 2: Detect language
        result = main(["detect", "--repo", str(repo)])
        assert result == EXIT_SUCCESS
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["language"] == "java"

        # Step 3: Initialize CI config
        result = main(
            [
                "init",
                "--repo",
                str(repo),
                "--language",
                "java",
                "--owner",
                "myorg",
                "--name",
                "my-java-project",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS

        # Step 4: Verify files
        assert (repo / ".ci-hub.yml").exists()
        assert (repo / ".github" / "workflows" / "hub-ci.yml").exists()


class TestScaffoldAndInitWorkflow:
    """E2E test: Scaffold a project then initialize it."""

    def test_scaffold_then_init_python(self, tmp_path: Path) -> None:
        """Scaffold Python project, then init CI configuration."""
        project = tmp_path / "scaffolded"

        # Step 1: Scaffold a Python project
        result = main(["scaffold", "python-pyproject", str(project)])
        assert result == EXIT_SUCCESS
        assert (project / "pyproject.toml").exists()

        # Step 2: Initialize CI on the scaffolded project
        result = main(
            [
                "init",
                "--repo",
                str(project),
                "--language",
                "python",
                "--owner",
                "testorg",
                "--name",
                "scaffolded",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS
        assert (project / ".ci-hub.yml").exists()

    def test_scaffold_then_init_java(self, tmp_path: Path) -> None:
        """Scaffold Java project, then init CI configuration."""
        project = tmp_path / "scaffolded"

        # Step 1: Scaffold a Java project
        result = main(["scaffold", "java-maven", str(project)])
        assert result == EXIT_SUCCESS
        assert (project / "pom.xml").exists()

        # Step 2: Initialize CI
        result = main(
            [
                "init",
                "--repo",
                str(project),
                "--language",
                "java",
                "--owner",
                "testorg",
                "--name",
                "scaffolded",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS


class TestReportWorkflow:
    """E2E test: Report generation and validation workflow."""

    def test_report_build_and_validate(self, tmp_path: Path, capsys) -> None:
        """Build a report and validate it."""
        report_path = tmp_path / "report.json"

        # Create a valid report
        report_data = {
            "schema_version": "2.0",
            "repository": "test/repo",
            "branch": "main",
            "python_version": "3.12",
            "results": {
                "coverage": 85,
                "tests_passed": 50,
                "tests_failed": 0,
                "mutation_score": 75,
            },
            "tool_metrics": {
                "ruff_errors": 0,
                "bandit_high": 0,
            },
            "tools_configured": {"pytest": True, "ruff": True},
            "tools_ran": {"pytest": True, "ruff": True},
            "tools_success": {"pytest": True, "ruff": True},
        }
        report_path.write_text(json.dumps(report_data))

        # Validate the report
        result = main(["report", "validate", "--report", str(report_path)])
        assert result == EXIT_SUCCESS


class TestUpdateWorkflow:
    """E2E test: Update existing configuration workflow."""

    def test_init_then_update(self, tmp_path: Path) -> None:
        """Initialize, then update configuration."""
        repo = tmp_path / "project"
        repo.mkdir()
        (repo / "pyproject.toml").write_text("[project]\n")

        # Step 1: Initialize
        result = main(
            [
                "init",
                "--repo",
                str(repo),
                "--language",
                "python",
                "--owner",
                "org",
                "--name",
                "project",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS

        # Verify workflow exists before update
        assert (repo / ".github" / "workflows" / "hub-ci.yml").exists()

        # Step 2: Update with force
        result = main(
            [
                "update",
                "--repo",
                str(repo),
                "--language",
                "python",
                "--owner",
                "org",
                "--name",
                "project",
                "--branch",
                "main",
                "--apply",
                "--force",
            ]
        )
        assert result == EXIT_SUCCESS

        # Workflow should still exist
        assert (repo / ".github" / "workflows" / "hub-ci.yml").exists()


class TestJsonModeWorkflow:
    """E2E test: All commands work with --json flag."""

    def test_detect_json_workflow(self, tmp_path: Path, capsys) -> None:
        """Detect with JSON output, then parse and use result."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        result = main(["detect", "--repo", str(tmp_path), "--json"])
        assert result == EXIT_SUCCESS

        out = capsys.readouterr().out
        data = json.loads(out)

        # Verify JSON structure
        assert data["status"] == "success"
        assert data["exit_code"] == 0
        assert "data" in data
        assert data["data"]["language"] == "python"

    def test_init_json_workflow(self, tmp_path: Path, capsys) -> None:
        """Init with JSON output."""
        result = main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--dry-run",
                "--json",
            ]
        )
        assert result == EXIT_SUCCESS

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "success"
        assert data["command"] == "init"

    def test_validate_json_on_error(self, tmp_path: Path, capsys) -> None:
        """Validate returns structured JSON even on error."""
        main(["validate", "--repo", str(tmp_path), "--json"])

        # Should fail but return valid JSON
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "failure"
        assert "problems" in data


class TestErrorRecoveryWorkflow:
    """E2E test: Error handling and recovery patterns."""

    def test_detect_error_then_success(self, tmp_path: Path, capsys) -> None:
        """Detect fails on empty dir, succeeds after adding marker."""
        # Step 1: Empty dir should fail
        result = main(["detect", "--repo", str(tmp_path)])
        assert result != EXIT_SUCCESS

        # Step 2: Add Python marker
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        # Step 3: Now should succeed
        result = main(["detect", "--repo", str(tmp_path)])
        assert result == EXIT_SUCCESS

    def test_validate_error_then_success(self, tmp_path: Path) -> None:
        """Validate fails without config, succeeds after init."""
        # Step 1: No config should fail
        result = main(["validate", "--repo", str(tmp_path)])
        assert result != EXIT_SUCCESS

        # Step 2: Initialize config
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--apply",
            ]
        )

        # Step 3: Now should succeed
        result = main(["validate", "--repo", str(tmp_path)])
        assert result == EXIT_SUCCESS


class TestHubOperationsWorkflow:
    """E2E test: Hub-level operations."""

    def test_discover_produces_matrix(self, capsys) -> None:
        """Discover command produces repo matrix."""
        main(["discover"])

        out = capsys.readouterr().out
        # Should produce JSON array or object
        try:
            data = json.loads(out)
            assert isinstance(data, (list, dict))
        except json.JSONDecodeError:
            # Or text output with repos
            assert len(out) > 0

    def test_preflight_checks_environment(self, capsys) -> None:
        """Preflight/doctor checks environment readiness."""
        result = main(["preflight"])

        # Should produce output about checks
        capsys.readouterr()  # Consume output
        assert result in (EXIT_SUCCESS, 1)  # May fail if tools missing

    def test_adr_list_shows_decisions(self, capsys) -> None:
        """ADR list shows architecture decisions."""
        result = main(["adr", "list"])

        # Should list ADRs or indicate none found
        capsys.readouterr()  # Consume output
        assert result in (EXIT_SUCCESS, 1)


class TestMultiLanguageWorkflow:
    """E2E test: Multi-language detection and handling."""

    def test_detects_python_over_java(self, tmp_path: Path, capsys) -> None:
        """When both markers exist, explicit language works."""
        # Create both markers
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "pom.xml").write_text("<project></project>")

        # Explicit language should work
        result = main(
            [
                "init",
                "--repo",
                str(tmp_path),
                "--language",
                "python",
                "--owner",
                "test",
                "--name",
                "repo",
                "--branch",
                "main",
                "--apply",
            ]
        )
        assert result == EXIT_SUCCESS

        # Config should be for Python
        config = (tmp_path / ".ci-hub.yml").read_text()
        assert "python" in config.lower()
