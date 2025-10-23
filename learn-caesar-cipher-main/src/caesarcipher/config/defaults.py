"""Default configuration values for the Caesar cipher GUI."""

from __future__ import annotations

DEFAULT_SHIFT = 3
MIN_SHIFT = 1
MAX_SHIFT = 25
HISTORY_LIMIT = 20
HISTORY_PREVIEW_LENGTH = 45

ACCENT_COLOR = "#00d2ff"
MUTED_COLOR = "#1f2933"
TEXT_COLOR = "#f5f7fa"
BACKGROUND_COLOR = "#121212"
PANEL_BACKGROUND = "#16161d"

MONOSPACE_FALLBACK = '"Fira Code", "Menlo", "Consolas", "Courier New", monospace'

__all__ = [
    "DEFAULT_SHIFT",
    "MIN_SHIFT",
    "MAX_SHIFT",
    "HISTORY_LIMIT",
    "HISTORY_PREVIEW_LENGTH",
    "ACCENT_COLOR",
    "MUTED_COLOR",
    "TEXT_COLOR",
    "BACKGROUND_COLOR",
    "PANEL_BACKGROUND",
    "MONOSPACE_FALLBACK",
]
