"""Threshold configuration prompts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import questionary

from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style
from cihub.wizard.validators import validate_percentage


def configure_thresholds(defaults: dict) -> dict[str, Any]:
    """Prompt for global thresholds.

    Args:
        defaults: Defaults config (expects thresholds).

    Returns:
        Thresholds dict.
    """
    raw_thresholds = deepcopy(defaults.get("thresholds", {}))
    thresholds: dict[str, Any] = raw_thresholds if isinstance(raw_thresholds, dict) else {}
    coverage_min: str = _check_cancelled(
        questionary.text(
            "Minimum coverage (%):",
            default=str(thresholds.get("coverage_min", 70)),
            validate=validate_percentage,
            style=get_style(),
        ).ask(),
        "Coverage threshold",
    )
    mutation_min: str = _check_cancelled(
        questionary.text(
            "Minimum mutation score (%):",
            default=str(thresholds.get("mutation_score_min", 70)),
            validate=validate_percentage,
            style=get_style(),
        ).ask(),
        "Mutation threshold",
    )
    thresholds["coverage_min"] = int(coverage_min)
    thresholds["mutation_score_min"] = int(mutation_min)
    return thresholds
