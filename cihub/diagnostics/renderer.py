"""Diagnostic rendering utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cihub.diagnostics.models import Diagnostic


def format_console(diagnostics: list[Diagnostic]) -> str:
    """Format diagnostics for console output.

    Args:
        diagnostics: List of diagnostics to format.

    Returns:
        Formatted string for console display.
    """
    if not diagnostics:
        return "No issues found."

    lines: list[str] = []
    for diag in diagnostics:
        prefix = f"[{diag.severity.value.upper()}]"
        location = ""
        if diag.file:
            location = f"{diag.file}"
            if diag.line is not None:
                location += f":{diag.line}"
                if diag.column is not None:
                    location += f":{diag.column}"
            location += " - "

        code_str = f"({diag.code}) " if diag.code else ""
        source_str = f"[{diag.source}] " if diag.source else ""

        lines.append(f"{prefix} {location}{source_str}{code_str}{diag.message}")

    return "\n".join(lines)


def format_editor(diagnostics: list[Diagnostic]) -> list[dict]:
    """Format diagnostics for editor integration (LSP-style).

    Args:
        diagnostics: List of diagnostics to format.

    Returns:
        List of diagnostic dictionaries in LSP-compatible format.
    """
    result: list[dict] = []
    for diag in diagnostics:
        item: dict = {
            "severity": {
                "error": 1,
                "warning": 2,
                "info": 3,
                "hint": 4,
            }.get(diag.severity.value, 1),
            "message": diag.message,
        }
        if diag.file:
            item["uri"] = f"file://{diag.file}"
        if diag.line is not None:
            # LSP uses 0-based line numbers
            item["range"] = {
                "start": {
                    "line": diag.line - 1,
                    "character": (diag.column - 1) if diag.column else 0,
                },
                "end": {
                    "line": (diag.end_line - 1) if diag.end_line else diag.line - 1,
                    "character": (diag.end_column - 1) if diag.end_column else 0,
                },
            }
        if diag.code:
            item["code"] = diag.code
        if diag.source:
            item["source"] = diag.source
        result.append(item)
    return result
