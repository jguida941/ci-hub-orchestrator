"""
CI/CD Hub - Configuration Loader Core

Merges configuration from multiple sources with proper precedence:
  1. Repo's .ci-hub.yml (highest priority)
  2. Hub's config/repos/<repo-name>.yaml
  3. Hub's config/defaults.yaml (lowest priority)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from cihub.config.io import load_yaml_file
from cihub.config.merge import deep_merge
from cihub.config.normalize import normalize_config


class ConfigValidationError(Exception):
    """Raised when a merged CI/CD Hub config fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _load_yaml(path: Path, source: str) -> dict:
    """Load YAML with consistent error handling for the loader."""
    try:
        return load_yaml_file(path)
    except ValueError as exc:
        raise ConfigValidationError(f"{source}: {exc}") from exc


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
        exit_on_validation_error: If True, sys.exit(1) on validation failure

    Returns:
        Merged configuration dictionary
    """
    from jsonschema import Draft7Validator

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
            raise ConfigValidationError(f"Validation failed for {source}", errors=messages)

    # 1. Load defaults (lowest priority)
    defaults_path = hub_root / "config" / "defaults.yaml"
    config = _load_yaml(defaults_path, "defaults")

    if not config:
        print(f"Warning: No defaults found at {defaults_path}", file=sys.stderr)
        config = {}
    config = normalize_config(config)

    # 2. Merge hub's repo-specific config
    repo_override_path = hub_root / "config" / "repos" / f"{repo_name}.yaml"
    repo_override = normalize_config(_load_yaml(repo_override_path, "hub override"))

    if repo_override:
        config = deep_merge(config, repo_override)

    # 3. Merge repo's own .ci-hub.yml (highest priority)
    if repo_config_path:
        repo_local_config = _load_yaml(repo_config_path, "repo local config")
        if repo_local_config:
            # Block repo-local from overriding protected keys (hub controls these)
            repo_block = repo_local_config.get("repo", {})
            if isinstance(repo_block, dict):
                repo_block.pop("owner", None)
                repo_block.pop("name", None)
                repo_block.pop("language", None)
                repo_block.pop("dispatch_workflow", None)
                repo_block.pop("dispatch_enabled", None)
                repo_local_config["repo"] = repo_block
            repo_local_config = normalize_config(repo_local_config)
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


def get_tool_enabled(config: dict[str, Any], language: str, tool: str) -> bool:
    """Check if a specific tool is enabled for the given language."""
    lang_config = config.get(language, {})
    if not isinstance(lang_config, dict):
        return False
    tools = lang_config.get("tools", {})
    if not isinstance(tools, dict):
        return False
    tool_config = tools.get(tool, {})
    if isinstance(tool_config, dict):
        return bool(tool_config.get("enabled", False))
    if isinstance(tool_config, bool):
        return tool_config
    return False


def get_tool_config(config: dict[str, Any], language: str, tool: str) -> dict[str, Any]:
    """Get the full configuration for a specific tool."""
    lang_config = config.get(language, {})
    if not isinstance(lang_config, dict):
        return {}
    tools = lang_config.get("tools", {})
    if not isinstance(tools, dict):
        return {}
    tool_config = tools.get(tool, {})
    return tool_config if isinstance(tool_config, dict) else {}


def _main() -> None:
    """CLI entry point for standalone usage."""
    from cihub.config.loader.inputs import generate_workflow_inputs

    parser = argparse.ArgumentParser(description="Load CI/CD Hub configuration")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument(
        "--hub-root",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent,
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
        print(yaml.safe_dump(config, default_flow_style=False, sort_keys=False))
    elif args.output == "workflow-inputs":
        inputs = generate_workflow_inputs(config)
        print(json.dumps(inputs, indent=2))