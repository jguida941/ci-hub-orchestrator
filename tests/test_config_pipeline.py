import json
import sys
from pathlib import Path

import pytest

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load_config import (  # noqa: E402
    ConfigValidationError,
    generate_workflow_inputs,
    load_config,
)
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
