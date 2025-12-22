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
from jsonschema import Draft7Validator


class ConfigValidationError(Exception):
    """Raised when a merged CI/CD Hub config fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


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

    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content if content else {}


def load_config(
    repo_name: str,
    hub_root: Path,
    repo_config_path: Path | None = None,
    exit_on_validation_error: bool = True,
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
            messages: list[str] = []
            for err in errors:
                path = ".".join([str(p) for p in err.path]) or "<root>"
                message = f"{path}: {err.message}"
                messages.append(message)
                print(f"  - {message}", file=sys.stderr)
            raise ConfigValidationError(
                f"Validation failed for {source}", errors=messages
            )

    # 1. Load defaults (lowest priority)
    defaults_path = hub_root / "config" / "defaults.yaml"
    config = load_yaml_file(defaults_path)

    if not config:
        print(f"Warning: No defaults found at {defaults_path}", file=sys.stderr)
        config = {}

    # 2. Merge hub's repo-specific config
    repo_override_path = hub_root / "config" / "repos" / f"{repo_name}.yaml"
    repo_override = load_yaml_file(repo_override_path)

    if repo_override:
        config = deep_merge(config, repo_override)

    # 3. Merge repo's own .ci-hub.yml (highest priority)
    if repo_config_path:
        repo_local_config = load_yaml_file(repo_config_path)
        if repo_local_config:
            config = deep_merge(config, repo_local_config)

    # Validate merged config once more
    # Ensure top-level language is set from repo.language if present
    repo_info = config.get("repo", {})
    if repo_info.get("language"):
        config["language"] = repo_info["language"]

    try:
        validate_config(config, "merged-config")
    except ConfigValidationError:
        if exit_on_validation_error:
            sys.exit(1)
        raise

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
        inputs["run_jqwik"] = tools.get("jqwik", {}).get("enabled", False)
        inputs["run_pmd"] = tools.get("pmd", {}).get("enabled", True)
        inputs["run_semgrep"] = tools.get("semgrep", {}).get("enabled", False)
        inputs["run_trivy"] = tools.get("trivy", {}).get("enabled", False)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", False)
        inputs["run_docker"] = tools.get("docker", {}).get("enabled", False)

        # Thresholds
        inputs["coverage_min"] = tools.get("jacoco", {}).get("min_coverage", 70)
        inputs["mutation_score_min"] = tools.get("pitest", {}).get(
            "min_mutation_score", 70
        )
        inputs["owasp_cvss_fail"] = tools.get("owasp", {}).get("fail_on_cvss", 7)
        inputs["max_checkstyle_errors"] = tools.get("checkstyle", {}).get(
            "max_errors", 0
        )
        inputs["max_spotbugs_bugs"] = tools.get("spotbugs", {}).get("max_bugs", 0)
        inputs["max_pmd_violations"] = tools.get("pmd", {}).get("max_violations", 0)
        inputs["max_semgrep_findings"] = tools.get("semgrep", {}).get(
            "max_findings", 0
        )

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
        inputs["run_mypy"] = tools.get("mypy", {}).get("enabled", False)
        inputs["run_black"] = tools.get("black", {}).get("enabled", True)
        inputs["run_isort"] = tools.get("isort", {}).get("enabled", True)
        inputs["run_mutmut"] = tools.get("mutmut", {}).get("enabled", False)
        inputs["run_hypothesis"] = tools.get("hypothesis", {}).get("enabled", True)
        inputs["run_semgrep"] = tools.get("semgrep", {}).get("enabled", False)
        inputs["run_trivy"] = tools.get("trivy", {}).get("enabled", False)
        inputs["run_codeql"] = tools.get("codeql", {}).get("enabled", False)
        inputs["run_docker"] = tools.get("docker", {}).get("enabled", False)

        inputs["coverage_min"] = tools.get("pytest", {}).get("min_coverage", 70)
        inputs["mutation_score_min"] = tools.get("mutmut", {}).get(
            "min_mutation_score", 70
        )
        inputs["max_ruff_errors"] = tools.get("ruff", {}).get("max_errors", 0)
        inputs["max_black_issues"] = tools.get("black", {}).get("max_issues", 0)
        inputs["max_isort_issues"] = tools.get("isort", {}).get("max_issues", 0)
        inputs["max_semgrep_findings"] = tools.get("semgrep", {}).get(
            "max_findings", 0
        )

    # Global thresholds (override tool defaults if provided)
    thresholds = config.get("thresholds", {})
    if "coverage_min" in thresholds:
        inputs["coverage_min"] = thresholds.get("coverage_min", inputs.get("coverage_min", 0))
    if "mutation_score_min" in thresholds:
        inputs["mutation_score_min"] = thresholds.get("mutation_score_min", inputs.get("mutation_score_min", 0))
    inputs["max_critical_vulns"] = thresholds.get("max_critical_vulns", 0)
    inputs["max_high_vulns"] = thresholds.get("max_high_vulns", 0)

    # Dispatch flags and grouping
    repo = config.get("repo", {})
    inputs["dispatch_enabled"] = repo.get("dispatch_enabled", True)
    inputs["run_group"] = repo.get("run_group", "full")

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
