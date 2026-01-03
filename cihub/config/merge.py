"""Deep merge utilities for CI/CD Hub config management."""

from __future__ import annotations

import copy
from typing import Any

from cihub.config.paths import PathConfig
from cihub.config.normalize import normalize_tool_configs


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with overlay taking precedence.

    Creates a new dictionary without modifying the originals.
    Nested dictionaries are deep copied to prevent shared references.

    Args:
        base: The base dictionary.
        overlay: The overlay dictionary (takes precedence).

    Returns:
        A new dictionary with merged values.

    Example:
        >>> base = {"a": 1, "b": {"c": 2, "d": 3}}
        >>> overlay = {"b": {"c": 10}, "e": 5}
        >>> deep_merge(base, overlay)
        {'a': 1, 'b': {'c': 10, 'd': 3}, 'e': 5}
    """
    # Deep copy base to ensure no shared references
    result = copy.deepcopy(base)

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Overlay value takes precedence (deep copy to avoid sharing)
            result[key] = copy.deepcopy(value)

    return result


def build_effective_config(
    defaults: dict[str, Any],
    profile: dict[str, Any] | None = None,
    repo_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the effective configuration by merging layers.

    Merge order (lowest to highest priority):
    1. defaults.yaml (hub defaults)
    2. Profile config (if specified)
    3. Repo-specific config (config/repos/<repo>.yaml)

    Args:
        defaults: Default configuration from defaults.yaml.
        profile: Optional profile configuration.
        repo_config: Optional repo-specific configuration.

    Returns:
        The merged effective configuration.
    """
    result = normalize_tool_configs(defaults)

    if profile:
        result = deep_merge(result, normalize_tool_configs(profile))

    if repo_config:
        result = deep_merge(result, normalize_tool_configs(repo_config))

    return normalize_tool_configs(result)


def get_effective_config_for_repo(
    paths: PathConfig,
    repo: str,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Get the effective configuration for a specific repository.

    This is a convenience function that loads all config layers
    and merges them.

    Args:
        paths: PathConfig instance.
        repo: Repository name.
        profile_name: Optional profile to apply.

    Returns:
        The merged effective configuration.
    """
    # Import here to avoid circular imports
    from cihub.config.io import load_defaults, load_profile, load_repo_config

    defaults = load_defaults(paths)

    profile = None
    if profile_name:
        profile = load_profile(paths, profile_name)

    repo_config = load_repo_config(paths, repo)

    return build_effective_config(defaults, profile, repo_config)
