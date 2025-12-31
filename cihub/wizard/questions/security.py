"""Security tool prompts shared across languages."""

from __future__ import annotations

import questionary

from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style


def _prompt_security_tools(base: dict) -> dict:
    semgrep_default = base.get("semgrep", {}).get("enabled", False)
    trivy_default = base.get("trivy", {}).get("enabled", False)
    codeql_default = base.get("codeql", {}).get("enabled", False)

    semgrep: bool = _check_cancelled(
        questionary.confirm(
            "Enable semgrep?",
            default=bool(semgrep_default),
            style=get_style(),
        ).ask(),
        "Semgrep toggle",
    )
    trivy: bool = _check_cancelled(
        questionary.confirm(
            "Enable trivy?",
            default=bool(trivy_default),
            style=get_style(),
        ).ask(),
        "Trivy toggle",
    )
    codeql: bool = _check_cancelled(
        questionary.confirm(
            "Enable codeql?",
            default=bool(codeql_default),
            style=get_style(),
        ).ask(),
        "CodeQL toggle",
    )
    return {
        "semgrep": {"enabled": bool(semgrep)},
        "trivy": {"enabled": bool(trivy)},
        "codeql": {"enabled": bool(codeql)},
    }


def configure_security_tools(language: str, defaults: dict) -> dict:
    """Prompt for security tool toggles.

    Returns a dict of overrides to merge into config.
    """
    overrides: dict = {}
    if language == "java":
        base = defaults.get("java", {}).get("tools", {})
        overrides = {"java": {"tools": _prompt_security_tools(base)}}
    elif language == "python":
        base = defaults.get("python", {}).get("tools", {})
        overrides = {"python": {"tools": _prompt_security_tools(base)}}
    return overrides
