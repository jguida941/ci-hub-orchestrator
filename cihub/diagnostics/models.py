"""Diagnostic data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DiagnosticSeverity(Enum):
    """Severity level for diagnostics."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class Diagnostic:
    """A single diagnostic message with location and context.

    Attributes:
        message: The diagnostic message.
        severity: Severity level (error, warning, info, hint).
        file: Path to the file containing the issue.
        line: Line number (1-based).
        column: Column number (1-based).
        end_line: End line for multi-line diagnostics.
        end_column: End column for multi-line diagnostics.
        code: Error code or rule ID.
        source: Tool that generated the diagnostic.
        data: Additional context data.
    """

    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    file: Path | None = None
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    code: str | None = None
    source: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "message": self.message,
            "severity": self.severity.value,
        }
        if self.file:
            result["file"] = str(self.file)
        if self.line is not None:
            result["line"] = self.line
        if self.column is not None:
            result["column"] = self.column
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.end_column is not None:
            result["end_column"] = self.end_column
        if self.code:
            result["code"] = self.code
        if self.source:
            result["source"] = self.source
        if self.data:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnostic:
        """Create from dictionary."""
        return cls(
            message=data["message"],
            severity=DiagnosticSeverity(data.get("severity", "error")),
            file=Path(data["file"]) if data.get("file") else None,
            line=data.get("line"),
            column=data.get("column"),
            end_line=data.get("end_line"),
            end_column=data.get("end_column"),
            code=data.get("code"),
            source=data.get("source"),
            data=data.get("data", {}),
        )
