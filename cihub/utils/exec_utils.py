"""Executable resolution utilities."""

from __future__ import annotations

import shutil


def resolve_executable(name: str) -> str:
    """Resolve an executable name to its full path.

    Args:
        name: The executable name to resolve.

    Returns:
        The full path if found, otherwise the original name.
    """
    return shutil.which(name) or name
