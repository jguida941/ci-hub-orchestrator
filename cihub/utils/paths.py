"""Path-related utilities."""

from __future__ import annotations

from pathlib import Path


def hub_root() -> Path:
    """Return the root directory of the hub-release project."""
    return Path(__file__).resolve().parents[2]


def validate_repo_path(repo_path: Path) -> Path:
    """Validate and canonicalize a repository path.

    Prevents path traversal attacks and ensures the path is a valid directory.

    Args:
        repo_path: The path to validate.

    Returns:
        The canonicalized path.

    Raises:
        ValueError: If the path is invalid or not a directory.
    """
    resolved = repo_path.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Repository path is not a valid directory: {repo_path}")
    return resolved


def validate_subdir(subdir: str) -> str:
    """Validate a subdirectory path to prevent path traversal.

    Args:
        subdir: The subdirectory path to validate.

    Returns:
        The validated subdirectory path.

    Raises:
        ValueError: If the path contains traversal sequences.
    """
    if not subdir:
        return subdir

    # Normalize the path
    normalized = Path(subdir).as_posix()

    # Check for path traversal attempts
    if ".." in normalized.split("/"):
        raise ValueError(f"Invalid subdirectory (path traversal detected): {subdir}")

    # Ensure it's a relative path
    if normalized.startswith("/"):
        raise ValueError(f"Subdirectory must be a relative path: {subdir}")

    return subdir
