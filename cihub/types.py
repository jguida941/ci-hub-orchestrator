"""Shared type definitions for cihub.

This module contains types that are used across multiple modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandResult:
    """Structured command result for JSON output."""

    exit_code: int = 0
    summary: str = ""
    problems: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    files_generated: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_payload(self, command: str, status: str, duration_ms: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "command": command,
            "status": status,
            "exit_code": self.exit_code,
            "duration_ms": duration_ms,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "problems": self.problems,
            "suggestions": self.suggestions,
            "files_generated": self.files_generated,
            "files_modified": self.files_modified,
        }
        if self.data:
            payload["data"] = self.data
        return payload
