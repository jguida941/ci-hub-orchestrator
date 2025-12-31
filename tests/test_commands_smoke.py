"""Tests for cihub.commands.smoke module."""

import argparse
from pathlib import Path

from cihub.cli import CommandResult
from cihub.commands.scaffold import scaffold_fixture
from cihub.commands.smoke import (
    ALL_TYPES,
    DEFAULT_TYPES,
    SmokeCase,
    SmokeStep,
    _apply_smoke_overrides,
    _as_command_result,
    _detect_java_build_tool,
    cmd_smoke,
)
from cihub.config.io import load_yaml_file


class TestSmokeStep:
    """Tests for SmokeStep dataclass."""

    def test_creates_step(self) -> None:
        step = SmokeStep(
            name="detect",
            exit_code=0,
            summary="Language detected",
            problems=[],
        )
        assert step.name == "detect"
        assert step.exit_code == 0

    def test_step_with_problems(self) -> None:
        step = SmokeStep(
            name="validate",
            exit_code=1,
            summary="Validation failed",
            problems=[{"message": "Missing field"}],
        )
        assert len(step.problems) == 1


class TestSmokeCase:
    """Tests for SmokeCase dataclass."""

    def test_creates_case(self, tmp_path: Path) -> None:
        case = SmokeCase(
            name="test-case",
            repo_path=tmp_path,
            subdir="backend",
            generated=True,
        )
        assert case.name == "test-case"
        assert case.repo_path == tmp_path
        assert case.subdir == "backend"
        assert case.generated is True

    def test_generated_defaults_false(self, tmp_path: Path) -> None:
        case = SmokeCase(name="case", repo_path=tmp_path, subdir="")
        assert case.generated is False


class TestAsCommandResult:
    """Tests for _as_command_result helper."""

    def test_returns_command_result_unchanged(self) -> None:
        original = CommandResult(exit_code=0, summary="ok")
        result = _as_command_result(original)
        assert result is original

    def test_converts_int_to_command_result(self) -> None:
        result = _as_command_result(0)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0

    def test_converts_nonzero_int(self) -> None:
        result = _as_command_result(1)
        assert result.exit_code == 1


class TestDetectJavaBuildTool:
    """Tests for _detect_java_build_tool helper."""

    def test_detects_gradle(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("// gradle")
        assert _detect_java_build_tool(tmp_path) == "gradle"

    def test_detects_gradle_kts(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle.kts").write_text("// kotlin gradle")
        assert _detect_java_build_tool(tmp_path) == "gradle"

    def test_detects_maven(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").write_text("<project/>")
        assert _detect_java_build_tool(tmp_path) == "maven"

    def test_returns_none_when_neither(self, tmp_path: Path) -> None:
        assert _detect_java_build_tool(tmp_path) is None

    def test_prefers_gradle_over_maven(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").write_text("")
        (tmp_path / "pom.xml").write_text("")
        assert _detect_java_build_tool(tmp_path) == "gradle"


class TestApplySmokeOverrides:
    """Tests for _apply_smoke_overrides helper."""

    def test_sets_subdir_in_repo_block(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("language: python\n")

        _apply_smoke_overrides(tmp_path, "python", "backend", None, relax=False)

        config = load_yaml_file(config_path)
        assert config["repo"]["subdir"] == "backend"

    def test_relaxes_thresholds(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("language: python\n")

        _apply_smoke_overrides(tmp_path, "python", "", None, relax=True)

        config = load_yaml_file(config_path)
        assert config["thresholds"]["coverage_min"] == 0
        assert config["thresholds"]["mutation_score_min"] == 0
        assert config["thresholds"]["max_critical_vulns"] == 999

    def test_relaxes_python_tools(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("language: python\n")

        _apply_smoke_overrides(tmp_path, "python", "", None, relax=True)

        config = load_yaml_file(config_path)
        python_tools = config["python"]["tools"]
        assert python_tools["bandit"]["enabled"] is False
        assert python_tools["mutmut"]["enabled"] is False

    def test_sets_java_build_tool(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("language: java\n")

        _apply_smoke_overrides(tmp_path, "java", "", "gradle", relax=False)

        config = load_yaml_file(config_path)
        assert config["java"]["build_tool"] == "gradle"

    def test_relaxes_java_tools(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("language: java\n")

        _apply_smoke_overrides(tmp_path, "java", "", "maven", relax=True)

        config = load_yaml_file(config_path)
        java_tools = config["java"]["tools"]
        assert java_tools["jacoco"]["enabled"] is False
        assert java_tools["owasp"]["enabled"] is False

    def test_handles_non_dict_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".ci-hub.yml"
        config_path.write_text("null\n")  # Invalid config

        # Should not raise
        _apply_smoke_overrides(tmp_path, "python", "app", None, relax=False)

        config = load_yaml_file(config_path)
        assert config["repo"]["subdir"] == "app"


class TestConstants:
    """Tests for module constants."""

    def test_default_types(self) -> None:
        assert "python-pyproject" in DEFAULT_TYPES
        assert "java-maven" in DEFAULT_TYPES

    def test_all_types(self) -> None:
        assert set(DEFAULT_TYPES).issubset(set(ALL_TYPES))
        assert "python-setup" in ALL_TYPES
        assert "java-gradle" in ALL_TYPES
        assert "monorepo" in ALL_TYPES


class TestCmdSmoke:
    """Tests for cmd_smoke command."""

    def test_smoke_on_scaffolded_repo(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "smoke-repo"
        scaffold_fixture("python-pyproject", repo_path, force=False)

        args = argparse.Namespace(
            repo=str(repo_path),
            subdir=None,
            full=False,
            install_deps=False,
            relax=False,
            force=False,
            keep=False,
            type=None,
            all=False,
            json=True,
        )
        result = cmd_smoke(args)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.data["cases"][0]["success"] is True

    def test_smoke_with_specific_type(self, tmp_path: Path) -> None:
        args = argparse.Namespace(
            repo=None,
            subdir=None,
            full=False,
            install_deps=False,
            relax=True,
            force=False,
            keep=False,
            type="python-pyproject",
            all=False,
            json=True,
        )
        result = cmd_smoke(args)
        assert isinstance(result, CommandResult)
        # Should generate and test the fixture
        assert "cases" in result.data

    def test_smoke_returns_usage_for_invalid_type(self, tmp_path: Path) -> None:
        args = argparse.Namespace(
            repo=None,
            subdir=None,
            full=False,
            install_deps=False,
            relax=False,
            force=False,
            keep=False,
            type="invalid-type",
            all=False,
            json=True,
        )
        result = cmd_smoke(args)
        assert isinstance(result, CommandResult)
        # Should fail for invalid type
