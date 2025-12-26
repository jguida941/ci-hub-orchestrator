"""Config management module for CI/CD Hub."""

from __future__ import annotations

from cihub.config.io import (
    ensure_dirs,
    list_profiles,
    list_repos,
    load_defaults,
    load_profile,
    load_profile_strict,
    load_repo_config,
    load_yaml_file,
    save_repo_config,
    save_yaml_file,
)
from cihub.config.merge import (
    build_effective_config,
    deep_merge,
    get_effective_config_for_repo,
)
from cihub.config.paths import PathConfig
from cihub.config.schema import get_schema, validate_config

__all__ = [
    "PathConfig",
    "build_effective_config",
    "deep_merge",
    "ensure_dirs",
    "get_effective_config_for_repo",
    "get_schema",
    "list_profiles",
    "list_repos",
    "load_defaults",
    "load_profile",
    "load_profile_strict",
    "load_repo_config",
    "load_yaml_file",
    "save_repo_config",
    "save_yaml_file",
    "validate_config",
]
