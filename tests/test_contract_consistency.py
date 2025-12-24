import copy
import sys
from pathlib import Path

import json
import yaml

# Allow importing scripts as modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.load_config import generate_workflow_inputs
from scripts.validate_config import validate_config

PYTHON_WORKFLOW = ROOT / ".github" / "workflows" / "python-ci.yml"
JAVA_WORKFLOW = ROOT / ".github" / "workflows" / "java-ci.yml"
PYTHON_TEMPLATE = ROOT / "templates" / "repo" / "hub-python-ci.yml"
JAVA_TEMPLATE = ROOT / "templates" / "repo" / "hub-java-ci.yml"

WORKFLOW_ONLY_INPUTS = {"workdir", "artifact_prefix"}
ALLOWED_NON_WORKFLOW_INPUTS = {
    "language",
    "dispatch_enabled",
    "run_group",
    "force_all_tools",
    "badges_enabled",
    "codecov_enabled",
}


def load_inputs(path: Path, trigger: str) -> set[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    on_section = data.get("on")
    if on_section is None and True in data:
        on_section = data.get(True)
    if not isinstance(on_section, dict):
        return set()
    trigger_section = on_section.get(trigger, {})
    if not isinstance(trigger_section, dict):
        return set()
    inputs = trigger_section.get("inputs", {})
    if not isinstance(inputs, dict):
        return set()
    return set(inputs.keys())


def build_config(language: str) -> dict:
    defaults_path = ROOT / "config" / "defaults.yaml"
    defaults = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
    cfg = copy.deepcopy(defaults)
    cfg["repo"] = {"owner": "test", "name": "example", "language": language}
    cfg["language"] = language
    return cfg


def validate_against_schema(config: dict) -> list[str]:
    schema_path = ROOT / "schema" / "ci-hub-config.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return validate_config(config, schema)


def test_defaults_merge_validate_schema():
    for language in ("java", "python"):
        cfg = build_config(language)
        errors = validate_against_schema(cfg)
        assert not errors, f"Defaults+repo should validate for {language}: {errors}"


def collect_generated_inputs(cfg: dict, include_java_docker: bool = False) -> set[str]:
    inputs = generate_workflow_inputs(cfg)
    keys = set(inputs.keys())

    if include_java_docker:
        docker_cfg = copy.deepcopy(cfg)
        tools = docker_cfg.setdefault("java", {}).setdefault("tools", {})
        tools.setdefault("docker", {})["enabled"] = True
        docker_inputs = generate_workflow_inputs(docker_cfg)
        keys.update(docker_inputs.keys())

    return keys


def test_python_workflow_inputs_are_config_driven():
    workflow_inputs = load_inputs(PYTHON_WORKFLOW, "workflow_call")
    cfg = build_config("python")
    generated = collect_generated_inputs(cfg)

    missing = sorted((workflow_inputs - WORKFLOW_ONLY_INPUTS) - generated)
    assert not missing, f"Python workflow inputs missing in load_config: {missing}"

    extras = sorted(generated - workflow_inputs - ALLOWED_NON_WORKFLOW_INPUTS)
    assert not extras, f"Unexpected load_config outputs (python): {extras}"


def test_java_workflow_inputs_are_config_driven():
    workflow_inputs = load_inputs(JAVA_WORKFLOW, "workflow_call")
    cfg = build_config("java")
    generated = collect_generated_inputs(cfg, include_java_docker=True)

    missing = sorted((workflow_inputs - WORKFLOW_ONLY_INPUTS) - generated)
    assert not missing, f"Java workflow inputs missing in load_config: {missing}"

    extras = sorted(generated - workflow_inputs - ALLOWED_NON_WORKFLOW_INPUTS)
    assert not extras, f"Unexpected load_config outputs (java): {extras}"


def test_python_caller_template_matches_workflow():
    workflow_inputs = load_inputs(PYTHON_WORKFLOW, "workflow_call")
    template_inputs = load_inputs(PYTHON_TEMPLATE, "workflow_dispatch")
    allowed_missing = {"run_docker"}

    missing = sorted((workflow_inputs - allowed_missing) - template_inputs)
    assert not missing, f"Python caller missing workflow inputs: {missing}"

    unexpected = sorted(template_inputs - workflow_inputs)
    assert not unexpected, f"Python caller has unknown inputs: {unexpected}"


def test_java_caller_template_matches_workflow():
    workflow_inputs = load_inputs(JAVA_WORKFLOW, "workflow_call")
    template_inputs = load_inputs(JAVA_TEMPLATE, "workflow_dispatch")
    allowed_missing = {"run_docker", "docker_compose_file", "docker_health_endpoint"}

    missing = sorted((workflow_inputs - allowed_missing) - template_inputs)
    assert not missing, f"Java caller missing workflow inputs: {missing}"

    unexpected = sorted(template_inputs - workflow_inputs)
    assert not unexpected, f"Java caller has unknown inputs: {unexpected}"
