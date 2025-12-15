#!/usr/bin/env python3
"""
CI/CD Hub - Configuration Loader

Merges configuration from multiple sources with proper precedence:
  1. Repo's .ci-hub.yml (highest priority)
  2. Hub's config/repos/<repo-name>.yaml
  3. Hub's config/defaults.yaml (lowest priority)

Usage:
    python load_config.py --repo <repo-name> [--repo-config-path <path>] [--output json|yaml]

Output:
    Merged configuration as JSON (default) or YAML
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator, ValidationError


def deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge two dictionaries. Override values take precedence.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_yaml_file(path: Path) -> dict:
    """Load a YAML file, return empty dict if not found."""
    if not path.exists():
        return {}

    with open(path) as f:
        content = yaml.safe_load(f)
        return content if content else {}


def load_config(
    repo_name: str,
    hub_root: Path,
    repo_config_path: Path | None = None,
) -> dict:
    """
    Load and merge configuration for a repository.

    Args:
        repo_name: Name of the repository (e.g., 'contact-suite-spring-react')
        hub_root: Path to the hub-release directory
        repo_config_path: Optional path to the repo's .ci-hub.yml

    Returns:
        Merged configuration dictionary
    """
    # Load schema for validation
    schema_path = hub_root / "schema" / "ci-hub-config.schema.json"
    schema: dict[str, Any] = {}
    if schema_path.exists():
        schema = json.loads(schema_path.read_text())
    else:
        print(f"Warning: schema not found at {schema_path}", file=sys.stderr)

    def validate_config(cfg: dict, source: str) -> None:
        if not schema:
            return
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(cfg))
        if errors:
            print(f"Config validation failed for {source}:", file=sys.stderr)
            for err in errors:
                path = ".".join([str(p) for p in err.path]) or "<root>"
                print(f"  - {path}: {err.message}", file=sys.stderr)
            raise ValidationError(f"Validation failed for {source}")

    # 1. Load defaults (lowest priority)
    defaults_path = hub_root / "config" / "defaults.yaml"
    config = load_yaml_file(defaults_path)

    if not config:
        print(f"Warning: No defaults found at {defaults_path}", file=sys.stderr)
        config = {}
    else:
        validate_config(config, str(defaults_path))

    # 2. Merge hub's repo-specific config
    repo_override_path = hub_root / "config" / "repos" / f"{repo_name}.yaml"
    repo_override = load_yaml_file(repo_override_path)

    if repo_override:
        validate_config(repo_override, str(repo_override_path))
        config = deep_merge(config, repo_override)

    # 3. Merge repo's own .ci-hub.yml (highest priority)
    if repo_config_path:
        repo_local_config = load_yaml_file(repo_config_path)
        if repo_local_config:
            validate_config(repo_local_config, str(repo_config_path))
            config = deep_merge(config, repo_local_config)

    # Validate merged config once more
    try:
        validate_config(config, "merged-config")
    except ValidationError:
        sys.exit(1)

    # Add metadata
    config["_meta"] = {
        "repo_name": repo_name,
        "config_sources": {
            "defaults": str(defaults_path),
            "hub_override": str(repo_override_path) if repo_override else None,
            "repo_local": str(repo_config_path) if repo_config_path else None,
        },
    }

    return config


def get_tool_enabled(config: dict, language: str, tool: str) -> bool:
    """Check if a specific tool is enabled for the given language."""
    lang_config = config.get(language, {})
    tools = lang_config.get("tools", {})
    tool_config = tools.get(tool, {})
    return tool_config.get("enabled", False)


def get_tool_config(config: dict, language: str, tool: str) -> dict:
    """Get the full configuration for a specific tool."""
    lang_config = config.get(language, {})
    tools = lang_config.get("tools", {})
    return tools.get(tool, {})


def generate_workflow_inputs(config: dict) -> dict:
    """
    Generate inputs for GitHub Actions workflow based on config.

    Returns a flat dict suitable for workflow inputs.
    """
    # Determine language
    language = config.get("language") or config.get("repo", {}).get("language", "java")

    inputs = {
        "language": language,
    }

    if language == "java":
        java = config.get("java", {})
        inputs["java_version"] = java.get("version", "21")
        inputs["build_tool"] = java.get("build_tool", "maven")

        tools = java.get("tools", {})
        inputs["run_jacoco"] = tools.get("jacoco", {}).get("enabled", True)
        inputs["run_checkstyle"] = tools.get("checkstyle", {}).get("enabled", True)
        inputs["run_spotbugs"] = tools.get("spotbugs", {}).get("enabled", True)
        inputs["run_owasp"] = tools.get("owasp", {}).get("enabled", True)
        inputs["run_pitest"] = tools.get("pitest", {}).get("enabled", True)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", True)
        inputs["run_docker"] = tools.get("docker", {}).get("enabled", False)

        # Thresholds
        inputs["coverage_min"] = tools.get("jacoco", {}).get("min_coverage", 70)
        inputs["mutation_score_min"] = tools.get("pitest", {}).get(
            "min_mutation_score", 70
        )
        inputs["owasp_cvss_fail"] = tools.get("owasp", {}).get("fail_on_cvss", 7)

        # Docker settings
        if inputs["run_docker"]:
            docker = tools.get("docker", {})
            inputs["docker_compose_file"] = docker.get(
                "compose_file", "docker-compose.yml"
            )
            inputs["docker_health_endpoint"] = docker.get(
                "health_endpoint", "/actuator/health"
            )

    elif language == "python":
        python = config.get("python", {})
        inputs["python_version"] = python.get("version", "3.12")

        tools = python.get("tools", {})
        inputs["run_pytest"] = tools.get("pytest", {}).get("enabled", True)
        inputs["run_ruff"] = tools.get("ruff", {}).get("enabled", True)
        inputs["run_bandit"] = tools.get("bandit", {}).get("enabled", True)
        inputs["run_pip_audit"] = tools.get("pip_audit", {}).get("enabled", True)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", True)

        inputs["coverage_min"] = tools.get("pytest", {}).get("min_coverage", 70)

    # Reports
    reports = config.get("reports", {})
    inputs["retention_days"] = reports.get("retention_days", 30)
    inputs["badges_enabled"] = reports.get("badges", {}).get("enabled", True)
    inputs["codecov_enabled"] = reports.get("codecov", {}).get("enabled", True)

    return inputs


def main():
    parser = argparse.ArgumentParser(description="Load CI/CD Hub configuration")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument(
        "--hub-root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Path to hub-release directory",
    )
    parser.add_argument(
        "--repo-config-path",
        type=Path,
        help="Path to repo's .ci-hub.yml file",
    )
    parser.add_argument(
        "--output",
        choices=["json", "yaml", "workflow-inputs"],
        default="json",
        help="Output format",
    )

    args = parser.parse_args()

    config = load_config(
        repo_name=args.repo,
        hub_root=args.hub_root,
        repo_config_path=args.repo_config_path,
    )

    if args.output == "json":
        print(json.dumps(config, indent=2))
    elif args.output == "yaml":
        print(yaml.dump(config, default_flow_style=False, sort_keys=False))
    elif args.output == "workflow-inputs":
        inputs = generate_workflow_inputs(config)
        print(json.dumps(inputs, indent=2))


if __name__ == "__main__":
    main()
