"""Python tool selection prompts."""

from __future__ import annotations

from copy import deepcopy

import questionary  # type: ignore[import-untyped]

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


def configure_python_tools(defaults: dict) -> dict:
    """Prompt to enable/disable Python tools.

    Args:
        defaults: Defaults config (expects python.tools).

    Returns:
        Tool config dict with updated enabled flags.
    """
    tools = deepcopy(defaults.get("python", {}).get("tools", {}))
    for tool in PYTHON_TOOL_ORDER:
        if tool not in tools:
            continue
        enabled = tools[tool].get("enabled", False)
        answer: bool = _check_cancelled(
            questionary.confirm(
                f"Enable {tool}?",
                default=bool(enabled),
                style=get_style(),
            ).ask(),
            f"{tool} toggle",
        )
        tools[tool]["enabled"] = bool(answer)
    return tools
