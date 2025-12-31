"""Language and runtime selection prompts."""

from __future__ import annotations

import questionary

from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style
from cihub.wizard.validators import validate_version


def select_language(default: str = "java") -> str:
    """Prompt for language selection."""
    return str(
        _check_cancelled(
            questionary.select(
                "Select language:",
                choices=["java", "python"],
                default=default,
                style=get_style(),
            ).ask(),
            "Language selection",
        )
    )


def select_java_version(default: str = "21") -> str:
    """Prompt for Java version selection."""
    return str(
        _check_cancelled(
            questionary.text(
                "Java version:",
                default=default,
                validate=validate_version,
                style=get_style(),
            ).ask(),
            "Java version",
        )
    )


def select_python_version(default: str = "3.12") -> str:
    """Prompt for Python version selection."""
    return str(
        _check_cancelled(
            questionary.text(
                "Python version:",
                default=default,
                validate=validate_version,
                style=get_style(),
            ).ask(),
            "Python version",
        )
    )


def select_build_tool(default: str = "maven") -> str:
    """Prompt for Java build tool selection."""
    return str(
        _check_cancelled(
            questionary.select(
                "Build tool:",
                choices=["maven", "gradle"],
                default=default,
                style=get_style(),
            ).ask(),
            "Build tool",
        )
    )
