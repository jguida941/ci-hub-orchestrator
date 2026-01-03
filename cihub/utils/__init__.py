"""Shared utility functions for cihub.

This module provides common utilities used across the cihub package.
All public items here should remain stable for backward compatibility.
"""

from __future__ import annotations

from cihub.utils.env import _parse_env_bool
from cihub.utils.exec_utils import resolve_executable
from cihub.utils.git import (
    GIT_REMOTE_RE,
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
)
from cihub.utils.github_api import fetch_remote_file, gh_api_json, update_remote_file
from cihub.utils.paths import hub_root, validate_repo_path, validate_subdir
from cihub.utils.progress import _bar

__all__ = [
    "_parse_env_bool",
    "_bar",
    "resolve_executable",
    "GIT_REMOTE_RE",
    "get_git_branch",
    "get_git_remote",
    "parse_repo_from_remote",
    "gh_api_json",
    "fetch_remote_file",
    "update_remote_file",
    "hub_root",
    "validate_repo_path",
    "validate_subdir",
]
