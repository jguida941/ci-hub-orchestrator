"""Normalization helpers for CI/CD Hub config."""

from __future__ import annotations

import copy
from typing import Any


def normalize_tool_configs(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize shorthand boolean tool configs to full object format."""
    if not isinstance(config, dict):
        return {}

    normalized = copy.deepcopy(config)
    for lang in ("python", "java"):
        lang_config = normalized.get(lang)
        if not isinstance(lang_config, dict):
            continue
        tools = lang_config.get("tools")
        if not isinstance(tools, dict):
            continue
        for tool_name, tool_value in list(tools.items()):
            if isinstance(tool_value, bool):
                tools[tool_name] = {"enabled": tool_value}
    return normalized
