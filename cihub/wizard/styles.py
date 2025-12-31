"""Questionary style configuration."""

from __future__ import annotations

import questionary

SUCCESS = "bold fg:ansigreen"
ERROR = "bold fg:ansired"
WARNING = "bold fg:ansiyellow"
INFO = "fg:ansiblue"
PROMPT = "bold"


def get_style() -> questionary.Style:
    """Return the shared questionary style for wizard prompts."""
    return questionary.Style(
        [
            ("question", PROMPT),
            ("answer", SUCCESS),
            ("pointer", INFO),
            ("highlighted", INFO),
            ("error", ERROR),
            ("warning", WARNING),
        ]
    )
