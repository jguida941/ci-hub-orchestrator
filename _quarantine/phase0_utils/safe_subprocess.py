"""
Utilities for invoking subprocess commands with basic safety checks.

These helpers enforce a simple allowlist to satisfy Ruff's S603 rule while
keeping the call-sites explicit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Sequence


def _normalise_allowlist(entries: Iterable[str | Path]) -> set[str]:
    """Normalise allowed program entries to both basename and resolved path strings."""
    normalised: set[str] = set()
    for entry in entries:
        path = Path(entry)
        normalised.add(path.name)
        try:
            normalised.add(str(path.resolve()))
        except OSError:
            # Resolution can fail for non-existent binaries; fall back to the raw string.
            normalised.add(str(path))
    return normalised


def run_checked(
    cmd: Sequence[str],
    *,
    allowed_programs: Iterable[str | Path] | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str]:
    """
    Execute ``subprocess.run`` after validating the program against an allowlist.

    ``allowed_programs`` accepts absolute paths or binary names. If omitted, no
    additional validation is performed beyond the standard ``subprocess.run`` semantics.
    """

    if not cmd:
        raise ValueError("command must not be empty")

    program_path = Path(cmd[0])
    if allowed_programs is not None:
        allowed = _normalise_allowlist(allowed_programs)
        program_name = program_path.name
        program_resolved = str(program_path.resolve()) if program_path.exists() else program_name
        if program_name not in allowed and program_resolved not in allowed:
            raise ValueError(f"disallowed command: {cmd[0]}")

    return subprocess.run(cmd, **kwargs)  # noqa: S603
