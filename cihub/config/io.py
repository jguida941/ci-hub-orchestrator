"""YAML I/O utilities for CI/CD Hub config management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from cihub.config.paths import PathConfig


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict.

    Args:
        path: Path to the YAML file.

    Returns:
        Dictionary containing the YAML contents, or empty dict if file doesn't exist.

    Raises:
        ValueError: If the YAML root is not a mapping (dict).
    """
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected YAML file {path} to contain a mapping (dict), "
            f"but got {type(data).__name__}"
        )
    return data


def save_yaml_file(
    path: str | Path,
    data: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Save data to a YAML file.

    Args:
        path: Path to the YAML file.
        data: Dictionary to save.
        dry_run: If True, don't actually write the file.

    Returns:
        True if the file was written (or would be written in dry_run mode).
    """
    path = Path(path)
    if dry_run:
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    return True


def ensure_dirs(paths: PathConfig) -> None:
    """Ensure all required directories exist.

    Args:
        paths: PathConfig instance with directory paths.
    """
    os.makedirs(paths.config_dir, exist_ok=True)
    os.makedirs(paths.repos_dir, exist_ok=True)
    os.makedirs(paths.profiles_dir, exist_ok=True)


def load_defaults(paths: PathConfig) -> dict[str, Any]:
    """Load the defaults.yaml file.

    Args:
        paths: PathConfig instance.

    Returns:
        Dictionary containing default configuration.
    """
    return load_yaml_file(paths.defaults_file)


def load_profile(paths: PathConfig, name: str) -> dict[str, Any]:
    """Load a profile configuration.

    Args:
        paths: PathConfig instance.
        name: Profile name (without .yaml extension).

    Returns:
        Dictionary containing the profile configuration.
    """
    return load_yaml_file(paths.profile_file(name))


def load_profile_strict(paths: PathConfig, name: str) -> dict[str, Any]:
    """Load a profile configuration, failing if missing.

    Args:
        paths: PathConfig instance.
        name: Profile name (without .yaml extension).

    Returns:
        Dictionary containing the profile configuration.

    Raises:
        FileNotFoundError: If the profile file does not exist.
    """
    profile_path = Path(paths.profile_file(name))
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    return load_yaml_file(profile_path)


def load_repo_config(paths: PathConfig, repo: str) -> dict[str, Any]:
    """Load a repository-specific configuration.

    Args:
        paths: PathConfig instance.
        repo: Repository name (without .yaml extension).

    Returns:
        Dictionary containing the repo configuration.
    """
    return load_yaml_file(paths.repo_file(repo))


def save_repo_config(
    paths: PathConfig,
    repo: str,
    data: dict[str, Any],
    dry_run: bool = False,
) -> bool:
    """Save a repository-specific configuration.

    Args:
        paths: PathConfig instance.
        repo: Repository name (without .yaml extension).
        data: Configuration data to save.
        dry_run: If True, don't actually write the file.

    Returns:
        True if the file was written (or would be written in dry_run mode).
    """
    return save_yaml_file(paths.repo_file(repo), data, dry_run=dry_run)


def list_repos(paths: PathConfig) -> list[str]:
    """List all repository configurations.

    Args:
        paths: PathConfig instance.

    Returns:
        List of repository names (without .yaml extension).
    """
    repos_dir = Path(paths.repos_dir)
    if not repos_dir.exists():
        return []
    return sorted(p.stem for p in repos_dir.glob("*.yaml") if p.is_file())


def list_profiles(paths: PathConfig) -> list[str]:
    """List all available profiles.

    Args:
        paths: PathConfig instance.

    Returns:
        List of profile names (without .yaml extension).
    """
    profiles_dir = Path(paths.profiles_dir)
    if not profiles_dir.exists():
        return []
    return sorted(p.stem for p in profiles_dir.glob("*.yaml") if p.is_file())
