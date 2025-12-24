"""
Tests for template and profile validation.

Validates that:
1. All hub config templates pass schema validation
2. All profiles, when merged with a minimal repo config, produce valid configs
3. Templates don't reference stale repo names
"""

import re
import sys
from pathlib import Path

import pytest
import yaml

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.apply_profile import deep_merge, load_yaml
from scripts.load_config import ConfigValidationError, load_config
from scripts.validate_config import validate_config

TEMPLATES_DIR = ROOT / "templates"
PROFILES_DIR = TEMPLATES_DIR / "profiles"
HUB_TEMPLATES_DIR = TEMPLATES_DIR / "hub" / "config" / "repos"
SCHEMA_PATH = ROOT / "schema" / "ci-hub-config.schema.json"


def load_schema():
    """Load the JSON schema for config validation."""
    import json
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# Minimal valid repo configs for testing profile merges
MINIMAL_JAVA_REPO = {
    "repo": {
        "owner": "test-owner",
        "name": "test-repo",
        "language": "java",
    },
    "language": "java",
}

MINIMAL_PYTHON_REPO = {
    "repo": {
        "owner": "test-owner",
        "name": "test-repo",
        "language": "python",
    },
    "language": "python",
}


class TestHubConfigTemplates:
    """Test hub-side config templates."""

    def get_hub_templates(self):
        """Get all hub config template files."""
        if not HUB_TEMPLATES_DIR.exists():
            return []
        return list(HUB_TEMPLATES_DIR.glob("*.yaml"))

    def test_hub_templates_exist(self):
        """Ensure hub templates directory has templates."""
        templates = self.get_hub_templates()
        assert len(templates) > 0, "No hub config templates found"

    @pytest.mark.parametrize("template_path", [
        pytest.param(p, id=p.name)
        for p in (HUB_TEMPLATES_DIR.glob("*.yaml") if HUB_TEMPLATES_DIR.exists() else [])
    ])
    def test_hub_template_is_valid_yaml(self, template_path):
        """Each hub template should be valid YAML."""
        data = load_yaml(template_path)
        assert isinstance(data, dict), f"{template_path.name} should be a mapping"

    @pytest.mark.parametrize("template_path", [
        pytest.param(p, id=p.name)
        for p in (HUB_TEMPLATES_DIR.glob("*.yaml") if HUB_TEMPLATES_DIR.exists() else [])
    ])
    def test_hub_template_has_required_fields(self, template_path):
        """Hub templates should have repo section with required fields."""
        data = load_yaml(template_path)

        # Templates might be partial (for merging), but full templates need repo
        if "repo" in data:
            repo = data["repo"]
            assert "owner" in repo or "name" in repo, \
                f"{template_path.name} repo section should have owner or name"


class TestProfileTemplates:
    """Test profile templates."""

    def get_python_profiles(self):
        """Get all Python profile files."""
        if not PROFILES_DIR.exists():
            return []
        return list(PROFILES_DIR.glob("python-*.yaml"))

    def get_java_profiles(self):
        """Get all Java profile files."""
        if not PROFILES_DIR.exists():
            return []
        return list(PROFILES_DIR.glob("java-*.yaml"))

    def test_profiles_exist(self):
        """Ensure profiles directory has profiles."""
        python_profiles = self.get_python_profiles()
        java_profiles = self.get_java_profiles()
        assert len(python_profiles) > 0, "No Python profiles found"
        assert len(java_profiles) > 0, "No Java profiles found"

    @pytest.mark.parametrize("profile_path", [
        pytest.param(p, id=p.name)
        for p in (PROFILES_DIR.glob("*.yaml") if PROFILES_DIR.exists() else [])
    ])
    def test_profile_is_valid_yaml(self, profile_path):
        """Each profile should be valid YAML."""
        data = load_yaml(profile_path)
        assert isinstance(data, dict), f"{profile_path.name} should be a mapping"

    @pytest.mark.parametrize("profile_path", [
        pytest.param(p, id=p.name)
        for p in (PROFILES_DIR.glob("python-*.yaml") if PROFILES_DIR.exists() else [])
    ])
    def test_python_profile_merged_is_valid(self, profile_path):
        """Python profile + minimal repo config should pass schema validation."""
        profile_data = load_yaml(profile_path)
        merged = deep_merge(profile_data, MINIMAL_PYTHON_REPO)

        schema = load_schema()
        errors = validate_config(merged, schema)

        assert not errors, \
            f"{profile_path.name} merged with minimal repo has errors: {errors}"

    @pytest.mark.parametrize("profile_path", [
        pytest.param(p, id=p.name)
        for p in (PROFILES_DIR.glob("java-*.yaml") if PROFILES_DIR.exists() else [])
    ])
    def test_java_profile_merged_is_valid(self, profile_path):
        """Java profile + minimal repo config should pass schema validation."""
        profile_data = load_yaml(profile_path)
        merged = deep_merge(profile_data, MINIMAL_JAVA_REPO)

        schema = load_schema()
        errors = validate_config(merged, schema)

        assert not errors, \
            f"{profile_path.name} merged with minimal repo has errors: {errors}"


class TestNoStaleReferences:
    """Test that templates don't reference old/stale names."""

    STALE_PATTERNS = [
        "ci-hub-orchestrator",  # Old repo name
        "jguida941/ci-hub-orchestrator",  # Old full name
    ]

    def get_all_template_files(self):
        """Get all template files (YAML and MD)."""
        files = []
        if TEMPLATES_DIR.exists():
            files.extend(TEMPLATES_DIR.rglob("*.yaml"))
            files.extend(TEMPLATES_DIR.rglob("*.yml"))
            files.extend(TEMPLATES_DIR.rglob("*.md"))
        return files

    @pytest.mark.parametrize("template_path", [
        pytest.param(p, id=str(p.relative_to(ROOT)))
        for p in (TEMPLATES_DIR.rglob("*") if TEMPLATES_DIR.exists() else [])
        if p.is_file() and p.suffix in {".yaml", ".yml", ".md"}
    ])
    def test_no_stale_repo_references(self, template_path):
        """Templates should not reference old repo names."""
        content = template_path.read_text(encoding="utf-8")

        for pattern in self.STALE_PATTERNS:
            assert pattern not in content, \
                f"{template_path} contains stale reference: {pattern}"


class TestRepoTemplate:
    """Test the main repo template used for onboarding."""

    REPO_TEMPLATE = TEMPLATES_DIR / "repo" / ".ci-hub.yml"

    def test_repo_template_exists(self):
        """The repo-side .ci-hub.yml template should exist."""
        assert self.REPO_TEMPLATE.exists(), \
            f"Repo template not found at {self.REPO_TEMPLATE}"

    def test_repo_template_is_valid_yaml(self):
        """Repo template should be valid YAML."""
        if not self.REPO_TEMPLATE.exists():
            pytest.skip("Repo template not found")

        data = load_yaml(self.REPO_TEMPLATE)
        assert isinstance(data, dict), "Repo template should be a mapping"


class TestDispatchTemplates:
    """Test dispatch workflow templates."""

    JAVA_DISPATCH = TEMPLATES_DIR / "java" / "java-ci-dispatch.yml"
    PYTHON_DISPATCH = TEMPLATES_DIR / "python" / "python-ci-dispatch.yml"

    def test_java_dispatch_template_exists(self):
        """Java dispatch template should exist."""
        assert self.JAVA_DISPATCH.exists(), \
            f"Java dispatch template not found at {self.JAVA_DISPATCH}"

    def test_python_dispatch_template_exists(self):
        """Python dispatch template should exist."""
        assert self.PYTHON_DISPATCH.exists(), \
            f"Python dispatch template not found at {self.PYTHON_DISPATCH}"

    def test_java_dispatch_is_valid_yaml(self):
        """Java dispatch template should be valid YAML."""
        if not self.JAVA_DISPATCH.exists():
            pytest.skip("Java dispatch template not found")

        data = load_yaml(self.JAVA_DISPATCH)
        assert isinstance(data, dict), "Java dispatch should be a mapping"
        assert "on" in data or "jobs" in data, "Should look like a workflow"

    def test_python_dispatch_is_valid_yaml(self):
        """Python dispatch template should be valid YAML."""
        if not self.PYTHON_DISPATCH.exists():
            pytest.skip("Python dispatch template not found")

        data = load_yaml(self.PYTHON_DISPATCH)
        assert isinstance(data, dict), "Python dispatch should be a mapping"
        assert "on" in data or "jobs" in data, "Should look like a workflow"


class TestHubRunAllSummary:
    """Guard against summary fallbacks masking disabled tools."""

    HUB_RUN_ALL = ROOT / ".github" / "workflows" / "hub-run-all.yml"

    def test_summary_does_not_force_true(self) -> None:
        content = self.HUB_RUN_ALL.read_text(encoding="utf-8")
        assert not re.search(r"matrix\.run_[A-Za-z0-9_]+\s*\|\|", content), (
            "hub-run-all.yml should not force matrix.run_* values with '||' fallbacks"
        )


class TestActualConfigs:
    """Test that actual repo configs in config/repos/ are valid."""

    CONFIG_DIR = ROOT / "config" / "repos"

    def get_actual_configs(self):
        """Get all actual repo config files."""
        if not self.CONFIG_DIR.exists():
            return []
        return list(self.CONFIG_DIR.glob("*.yaml"))

    def test_configs_exist(self):
        """Ensure we have actual repo configs."""
        configs = self.get_actual_configs()
        assert len(configs) > 0, "No repo configs found in config/repos/"

    @pytest.mark.parametrize("config_path", [
        pytest.param(p, id=p.stem)
        for p in ((ROOT / "config" / "repos").glob("*.yaml")
                  if (ROOT / "config" / "repos").exists() else [])
    ])
    def test_actual_config_is_valid(self, config_path):
        """Each actual repo config should pass validation."""
        try:
            cfg = load_config(
                repo_name=config_path.stem,
                hub_root=ROOT,
                exit_on_validation_error=False,
            )
            assert cfg is not None
            assert "repo" in cfg
        except ConfigValidationError as e:
            pytest.fail(f"{config_path.stem} failed validation: {e}")
