"""Python tool selection prompts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import questionary

from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style

PYTHON_TOOL_ORDER = [
    "pytest",
    "ruff",
    "black",
    "isort",
    "mypy",
    "bandit",
    "pip_audit",
    "mutmut",
    "hypothesis",
    "semgrep",
    "trivy",
    "codeql",
    "docker",
]


def configure_python_tools(defaults: dict) -> dict[str, Any]:
    """Prompt to enable/disable Python tools.

    Args:
        defaults: Defaults config (expects python.tools).

    Returns:
        Tool config dict with updated enabled flags.
    """
    raw_tools = deepcopy(defaults.get("python", {}).get("tools", {}))
    tools: dict[str, Any] = raw_tools if isinstance(raw_tools, dict) else {}
    for tool in PYTHON_TOOL_ORDER:
        tool_cfg = tools.get(tool)
        if not isinstance(tool_cfg, dict):
            continue
        enabled = tool_cfg.get("enabled", False)
        answer: bool = _check_cancelled(
            questionary.confirm(
                f"Enable {tool}?",
                default=bool(enabled),
                style=get_style(),
            ).ask(),
            f"{tool} toggle",
        )
        tool_cfg["enabled"] = bool(answer)
    return tools
