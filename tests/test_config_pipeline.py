import json
import sys
from pathlib import Path

import pytest

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cihub.config.loader import (  # noqa: E402
    ConfigValidationError,
    generate_workflow_inputs,
    load_config,
)
from cihub.config.normalize import normalize_tool_configs  # noqa: E402
from scripts.validate_config import validate_config  # noqa: E402


def test_generate_workflow_inputs_java():
    cfg = {
        "language": "java",
        "repo": {"owner": "o", "name": "r", "language": "java"},
        "java": {
            "version": "17",
            "build_tool": "maven",
            "tools": {
                "jacoco": {"enabled": True, "min_coverage": 80},
                "pitest": {"enabled": True, "min_mutation_score": 75},
                "semgrep": {"enabled": True},
            },
        },
        "thresholds": {"max_critical_vulns": 1, "max_high_vulns": 2},
    }

    inputs = generate_workflow_inputs(cfg)

    # Tool toggles and essential settings - verify config drives behavior
    assert inputs["language"] == cfg["language"]
    assert inputs["java_version"] == cfg["java"]["version"]
    assert inputs["build_tool"] == cfg["java"]["build_tool"]
    assert inputs["run_pitest"] == cfg["java"]["tools"]["pitest"]["enabled"]
    assert inputs["run_semgrep"] == cfg["java"]["tools"]["semgrep"]["enabled"]

    # Thresholds are direct inputs
    assert inputs["coverage_min"] == cfg["java"]["tools"]["jacoco"]["min_coverage"]
    assert inputs["mutation_score_min"] == cfg["java"]["tools"]["pitest"]["min_mutation_score"]
    assert inputs["max_critical_vulns"] == cfg["thresholds"]["max_critical_vulns"]
    assert inputs["max_high_vulns"] == cfg["thresholds"]["max_high_vulns"]


def test_generate_workflow_inputs_python():
    cfg = {
        "language": "python",
        "repo": {"owner": "o", "name": "r", "language": "python"},
        "python": {
            "version": "3.11",
            "tools": {
                "pytest": {"enabled": True, "min_coverage": 85},
                "mutmut": {"enabled": True, "min_mutation_score": 70},
                "trivy": {"enabled": True},
            },
        },
        "thresholds": {"max_critical_vulns": 0, "max_high_vulns": 0},
    }

    inputs = generate_workflow_inputs(cfg)

    # Tool toggles and essential settings - verify config drives behavior
    assert inputs["language"] == cfg["language"]
    assert inputs["python_version"] == cfg["python"]["version"]
    assert inputs["run_mutmut"] == cfg["python"]["tools"]["mutmut"]["enabled"]
    assert inputs["run_trivy"] == cfg["python"]["tools"]["trivy"]["enabled"]

    # Thresholds are direct inputs
    assert inputs["coverage_min"] == cfg["python"]["tools"]["pytest"]["min_coverage"]
    assert inputs["mutation_score_min"] == cfg["python"]["tools"]["mutmut"]["min_mutation_score"]
    assert inputs["max_critical_vulns"] == cfg["thresholds"]["max_critical_vulns"]
    assert inputs["max_high_vulns"] == cfg["thresholds"]["max_high_vulns"]


def test_load_config_merge_and_no_exit(tmp_path: Path):
    hub_root = tmp_path
    # Copy real schema so validation is faithful
    schema_src = ROOT / "schema" / "ci-hub-config.schema.json"
    schema_dst = hub_root / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    schema_dst.joinpath("ci-hub-config.schema.json").write_text(schema_src.read_text(), encoding="utf-8")

    defaults = {
        "repo": {"owner": "owner", "name": "base", "language": "java"},
        "language": "java",
        "java": {"tools": {"jacoco": {"enabled": True}}},
    }
    repo_override = {
        "repo": {"owner": "owner", "name": "example", "language": "java"},
        "thresholds": {"max_high_vulns": 5},
    }

    (hub_root / "config" / "repos").mkdir(parents=True, exist_ok=True)
    (hub_root / "config" / "defaults.yaml").write_text(json.dumps(defaults), encoding="utf-8")
    (hub_root / "config" / "repos" / "example.yaml").write_text(json.dumps(repo_override), encoding="utf-8")

    cfg = load_config(repo_name="example", hub_root=hub_root, exit_on_validation_error=False)

    assert cfg["repo"]["name"] == "example"
    assert cfg["thresholds"]["max_high_vulns"] == 5
    assert cfg["language"] == "java"


def test_load_config_raises_validation_error(tmp_path: Path):
    hub_root = tmp_path
    schema_src = ROOT / "schema" / "ci-hub-config.schema.json"
    schema_dst = hub_root / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    schema_dst.joinpath("ci-hub-config.schema.json").write_text(schema_src.read_text(), encoding="utf-8")
    (hub_root / "config" / "repos").mkdir(parents=True, exist_ok=True)
    (hub_root / "config" / "defaults.yaml").write_text("{}", encoding="utf-8")
    (hub_root / "config" / "repos" / "badrepo.yaml").write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        load_config(repo_name="badrepo", hub_root=hub_root, exit_on_validation_error=False)


def test_validate_config_sorts_paths():
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "string"},
        },
        "required": ["a", "b"],
        "additionalProperties": False,
    }
    config = {"b": 1, "a": 2}

    errors = validate_config(config, schema)

    assert errors == [
        "a: 2 is not of type 'string'",
        "b: 1 is not of type 'string'",
    ]


# =====================================================================
# Phase B: Shorthand Boolean Tests
# =====================================================================


def test_normalize_tool_configs_python():
    """Test that shorthand booleans are normalized to full format."""
    config = {
        "python": {
            "tools": {
                "pytest": True,  # shorthand
                "ruff": False,  # shorthand
                "bandit": {"enabled": True, "fail_on_high": True},  # full format (unchanged)
            }
        }
    }

    result = normalize_tool_configs(config)

    # Shorthand booleans should be normalized
    assert result["python"]["tools"]["pytest"] == {"enabled": True}
    assert result["python"]["tools"]["ruff"] == {"enabled": False}
    # Full format should be unchanged
    assert result["python"]["tools"]["bandit"] == {"enabled": True, "fail_on_high": True}


def test_normalize_tool_configs_java():
    """Test that shorthand booleans are normalized for Java tools."""
    config = {
        "java": {
            "tools": {
                "jacoco": True,  # shorthand
                "checkstyle": False,  # shorthand
                "spotbugs": {"enabled": True, "max_bugs": 10},  # full format
            }
        }
    }

    result = normalize_tool_configs(config)

    assert result["java"]["tools"]["jacoco"] == {"enabled": True}
    assert result["java"]["tools"]["checkstyle"] == {"enabled": False}
    assert result["java"]["tools"]["spotbugs"] == {"enabled": True, "max_bugs": 10}


def test_normalize_tool_configs_preserves_other_keys():
    """Test that normalization doesn't affect non-tool config."""
    config = {
        "language": "python",
        "repo": {"owner": "test", "name": "test"},
        "python": {
            "version": "3.12",
            "tools": {"pytest": True},
        },
        "thresholds": {"coverage_min": 80},
    }

    result = normalize_tool_configs(config)

    assert result["language"] == "python"
    assert result["repo"] == {"owner": "test", "name": "test"}
    assert result["python"]["version"] == "3.12"
    assert result["thresholds"] == {"coverage_min": 80}


def test_generate_workflow_inputs_with_shorthand_booleans():
    """Test that generate_workflow_inputs handles shorthand booleans."""
    cfg = {
        "language": "python",
        "repo": {"owner": "o", "name": "r", "language": "python"},
        "python": {
            "version": "3.11",
            "tools": {
                "pytest": True,  # shorthand enabled
                "mutmut": False,  # shorthand disabled
                "ruff": True,  # shorthand enabled
                "bandit": {"enabled": False},  # full format disabled
            },
        },
    }

    inputs = generate_workflow_inputs(cfg)

    # Verify shorthand booleans work correctly
    assert inputs["run_pytest"] is True
    assert inputs["run_mutmut"] is False
    assert inputs["run_ruff"] is True
    assert inputs["run_bandit"] is False


def test_generate_workflow_inputs_java_with_shorthand():
    """Test Java shorthand booleans in generate_workflow_inputs."""
    cfg = {
        "language": "java",
        "repo": {"owner": "o", "name": "r", "language": "java"},
        "java": {
            "version": "21",
            "build_tool": "gradle",
            "tools": {
                "jacoco": True,  # shorthand
                "pitest": False,  # shorthand
                "checkstyle": {"enabled": True, "max_errors": 5},  # full
            },
        },
    }

    inputs = generate_workflow_inputs(cfg)

    assert inputs["run_jacoco"] is True
    assert inputs["run_pitest"] is False
    assert inputs["run_checkstyle"] is True


def test_load_config_with_shorthand_booleans(tmp_path: Path):
    """Test that shorthand booleans normalize without dropping defaults."""
    hub_root = tmp_path
    schema_src = ROOT / "schema" / "ci-hub-config.schema.json"
    schema_dst = hub_root / "schema"
    schema_dst.mkdir(parents=True, exist_ok=True)
    schema_dst.joinpath("ci-hub-config.schema.json").write_text(
        schema_src.read_text(), encoding="utf-8"
    )

    defaults = {
        "repo": {"owner": "owner", "name": "shorthand-test", "language": "python"},
        "language": "python",
        "python": {
            "tools": {
                "pytest": {"enabled": True, "min_coverage": 80},
                "ruff": {"enabled": True, "max_errors": 0},
            }
        },
    }
    repo_override = {"python": {"tools": {"pytest": True, "ruff": False}}}

    (hub_root / "config" / "repos").mkdir(parents=True, exist_ok=True)
    (hub_root / "config" / "defaults.yaml").write_text(json.dumps(defaults), encoding="utf-8")
    (hub_root / "config" / "repos" / "shorthand-test.yaml").write_text(
        json.dumps(repo_override), encoding="utf-8"
    )

    cfg = load_config(repo_name="shorthand-test", hub_root=hub_root, exit_on_validation_error=False)

    assert cfg["python"]["tools"]["pytest"] == {"enabled": True, "min_coverage": 80}
    assert cfg["python"]["tools"]["ruff"] == {"enabled": False, "max_errors": 0}
