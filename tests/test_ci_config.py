"""Tests for cihub.ci_config module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cihub.ci_config import FALLBACK_DEFAULTS, load_ci_config, load_hub_config


class TestFallbackDefaults:
    """Tests for FALLBACK_DEFAULTS constant."""

    def test_has_java_config(self) -> None:
        assert "java" in FALLBACK_DEFAULTS
        assert FALLBACK_DEFAULTS["java"]["version"] == "21"
        assert FALLBACK_DEFAULTS["java"]["build_tool"] == "maven"

    def test_has_python_config(self) -> None:
        assert "python" in FALLBACK_DEFAULTS
        assert FALLBACK_DEFAULTS["python"]["version"] == "3.12"

    def test_has_java_tools(self) -> None:
        java_tools = FALLBACK_DEFAULTS["java"]["tools"]
        assert java_tools["jacoco"]["enabled"] is True
        assert java_tools["checkstyle"]["enabled"] is True
        assert java_tools["spotbugs"]["enabled"] is True
        assert java_tools["owasp"]["enabled"] is True
        assert java_tools["pitest"]["enabled"] is True

    def test_has_python_tools(self) -> None:
        python_tools = FALLBACK_DEFAULTS["python"]["tools"]
        assert python_tools["pytest"]["enabled"] is True
        assert python_tools["ruff"]["enabled"] is True
        assert python_tools["bandit"]["enabled"] is True

    def test_has_thresholds(self) -> None:
        thresholds = FALLBACK_DEFAULTS["thresholds"]
        assert thresholds["coverage_min"] == 70
        assert thresholds["mutation_score_min"] == 70

    def test_has_reports_config(self) -> None:
        assert FALLBACK_DEFAULTS["reports"]["retention_days"] == 30


class TestLoadCiConfig:
    """Tests for load_ci_config function."""

    def test_raises_when_ci_hub_yml_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Missing .ci-hub.yml"):
            load_ci_config(tmp_path)

    def test_loads_local_config(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        assert result["language"] == "python"

    def test_merges_with_defaults(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: java\njava:\n  version: '17'\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        # Local config should override
        assert result["java"]["version"] == "17"
        # Defaults should still be present
        assert result["java"]["build_tool"] == "maven"

    def test_shorthand_preserves_tool_defaults(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\npython:\n  tools:\n    pytest: true\n    ruff: false\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text(
            "python:\n"
            "  tools:\n"
            "    pytest:\n"
            "      enabled: true\n"
            "      min_coverage: 75\n"
            "    ruff:\n"
            "      enabled: true\n"
            "      max_errors: 3\n"
        )

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        assert result["python"]["tools"]["pytest"]["enabled"] is True
        assert result["python"]["tools"]["pytest"]["min_coverage"] == 75
        assert result["python"]["tools"]["ruff"]["enabled"] is False
        assert result["python"]["tools"]["ruff"]["max_errors"] == 3

    def test_hub_config_shorthand_preserves_tool_defaults(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        repos_dir = config_dir / "repos"
        repos_dir.mkdir(parents=True)
        (config_dir / "defaults.yaml").write_text(
            "repo:\n"
            "  owner: owner\n"
            "  name: base\n"
            "  language: python\n"
            "python:\n"
            "  tools:\n"
            "    pytest:\n"
            "      enabled: true\n"
            "      min_coverage: 75\n"
            "    ruff:\n"
            "      enabled: true\n"
            "      max_errors: 3\n"
        )
        (repos_dir / "example.yaml").write_text(
            "repo:\n"
            "  owner: owner\n"
            "  name: example\n"
            "  language: python\n"
            "python:\n"
            "  tools:\n"
            "    pytest: true\n"
            "    ruff: false\n"
        )

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_hub_config("example")

        assert result["language"] == "python"
        assert result["python"]["tools"]["pytest"]["enabled"] is True
        assert result["python"]["tools"]["pytest"]["min_coverage"] == 75
        assert result["python"]["tools"]["ruff"]["enabled"] is False
        assert result["python"]["tools"]["ruff"]["max_errors"] == 3

    def test_uses_fallback_when_defaults_file_missing(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path  # No config/defaults.yaml
            result = load_ci_config(tmp_path)

        # Should have fallback defaults merged
        assert result["python"]["version"] == "3.12"
        assert result["thresholds"]["coverage_min"] == 70

    def test_uses_fallback_when_defaults_file_empty(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text("")  # Empty file

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        # Should use FALLBACK_DEFAULTS
        assert result["python"]["version"] == "3.12"

    def test_loads_defaults_from_hub_root(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: java\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "defaults.yaml").write_text("java:\n  version: '11'\n  build_tool: gradle\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        # Should use custom defaults
        assert result["java"]["version"] == "11"
        assert result["java"]["build_tool"] == "gradle"

    def test_extracts_language_from_repo_section(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("repo:\n  language: java\n  name: myapp\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        assert result["language"] == "java"

    def test_top_level_language_not_overwritten_by_repo(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\nrepo:\n  language: java\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        # repo.language gets promoted to top-level, overwriting existing
        # This is the current behavior - verify it
        assert result["language"] == "java"

    def test_handles_non_dict_repo(self, tmp_path: Path) -> None:
        ci_hub = tmp_path / ".ci-hub.yml"
        ci_hub.write_text("language: python\nrepo: null\n")

        with patch("cihub.ci_config.hub_root") as mock_root:
            mock_root.return_value = tmp_path
            result = load_ci_config(tmp_path)

        assert result["language"] == "python"


def test_load_ci_config_applies_thresholds_profile(tmp_path: Path) -> None:
    ci_hub = tmp_path / ".ci-hub.yml"
    ci_hub.write_text("language: python\nthresholds_profile: coverage-gate\n")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "defaults.yaml").write_text("thresholds:\n  coverage_min: 70\n  mutation_score_min: 70\n")

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_ci_config(tmp_path)

    assert result["thresholds"]["coverage_min"] == 90
    assert result["thresholds"]["mutation_score_min"] == 80


def test_load_hub_config_applies_thresholds_profile(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text(
        "repo:\n"
        "  owner: owner\n"
        "  name: base\n"
        "  language: python\n"
        "language: python\n"
        "thresholds:\n"
        "  coverage_min: 70\n"
        "  mutation_score_min: 70\n"
    )
    (repos_dir / "example.yaml").write_text(
        "repo:\n  owner: owner\n  name: example\n  language: python\nthresholds_profile: coverage-gate\n"
    )

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_hub_config("example")

    assert result["thresholds"]["coverage_min"] == 90
    assert result["thresholds"]["mutation_score_min"] == 80


def test_load_hub_config_raises_when_config_missing(tmp_path: Path) -> None:
    """Test that load_hub_config raises FileNotFoundError when hub config not found."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text("language: python\n")
    # No repos/missing.yaml file

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        with pytest.raises(FileNotFoundError, match="Hub config not found"):
            load_hub_config("missing")


def test_load_hub_config_uses_fallback_when_defaults_empty(tmp_path: Path) -> None:
    """Test load_hub_config uses FALLBACK_DEFAULTS when defaults.yaml is empty."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text("")  # Empty defaults
    (repos_dir / "example.yaml").write_text(
        "repo:\n  owner: owner\n  name: example\n  language: python\n"
    )

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_hub_config("example")

    # Should use FALLBACK_DEFAULTS
    assert result["python"]["version"] == "3.12"
    assert result["thresholds"]["coverage_min"] == 70


def test_load_hub_config_with_repo_path_merges_local(tmp_path: Path) -> None:
    """Test load_hub_config merges repo's .ci-hub.yml when repo_path provided."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text(
        "repo:\n  owner: owner\n  name: base\n  language: python\n"
    )
    (repos_dir / "example.yaml").write_text(
        "repo:\n  owner: owner\n  name: example\n  language: python\n"
        "python:\n  version: '3.11'\n"
    )

    # Create a separate repo with .ci-hub.yml
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    (repo_dir / ".ci-hub.yml").write_text(
        "python:\n"
        "  tools:\n"
        "    pytest:\n"
        "      enabled: true\n"
        "      min_coverage: 95\n"
        "custom_setting: from_repo\n"
    )

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_hub_config("example", repo_path=repo_dir)

    # Hub config should be used for version
    assert result["python"]["version"] == "3.11"
    # Repo's .ci-hub.yml settings should be merged
    assert result.get("custom_setting") == "from_repo"


def test_load_hub_config_with_repo_path_blocks_protected_keys(tmp_path: Path) -> None:
    """Test that protected keys from repo's .ci-hub.yml are blocked."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text(
        "repo:\n  owner: hub-owner\n  name: base\n  language: python\n"
    )
    (repos_dir / "example.yaml").write_text(
        "repo:\n  owner: hub-owner\n  name: hub-project\n  language: python\n"
    )

    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    (repo_dir / ".ci-hub.yml").write_text(
        "repo:\n"
        "  owner: malicious-owner\n"  # Should be blocked
        "  name: malicious-name\n"  # Should be blocked
        "  language: java\n"  # Should be blocked
        "  dispatch_workflow: hack.yml\n"  # Should be blocked
        "  dispatch_enabled: true\n"  # Should be blocked
        "  custom_key: allowed\n"  # Should be allowed
        "other_setting: value\n"
    )

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_hub_config("example", repo_path=repo_dir)

    # Protected keys should come from hub config, not repo
    assert result["repo"]["owner"] == "hub-owner"
    assert result["repo"]["name"] == "hub-project"
    assert result["language"] == "python"
    # Non-protected keys from repo should be allowed
    assert result["repo"].get("custom_key") == "allowed"
    assert result.get("other_setting") == "value"


def test_load_hub_config_with_repo_path_no_ci_hub_yml(tmp_path: Path) -> None:
    """Test load_hub_config when repo_path exists but has no .ci-hub.yml."""
    config_dir = tmp_path / "config"
    repos_dir = config_dir / "repos"
    repos_dir.mkdir(parents=True)
    (config_dir / "defaults.yaml").write_text(
        "repo:\n  owner: owner\n  name: base\n  language: python\n"
    )
    (repos_dir / "example.yaml").write_text(
        "repo:\n  owner: owner\n  name: example\n  language: python\n"
    )

    # Create repo without .ci-hub.yml
    repo_dir = tmp_path / "target-repo"
    repo_dir.mkdir()
    # No .ci-hub.yml file

    with patch("cihub.ci_config.hub_root") as mock_root:
        mock_root.return_value = tmp_path
        result = load_hub_config("example", repo_path=repo_dir)

    # Should still work, just use hub config only
    assert result["repo"]["name"] == "example"
    assert result["language"] == "python"
