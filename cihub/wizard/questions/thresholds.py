"""Threshold configuration prompts."""

from __future__ import annotations

from copy import deepcopy

import questionary  # type: ignore[import-untyped]

from cihub.wizard.core import _check_cancelled
from cihub.wizard.styles import get_style
from cihub.wizard.validators import validate_percentage


def configure_thresholds(defaults: dict) -> dict:
    """Prompt for global thresholds.

    Args:
        defaults: Defaults config (expects thresholds).

    Returns:
        Thresholds dict.
    """
    thresholds = deepcopy(defaults.get("thresholds", {}))
    coverage_min = _check_cancelled(
        questionary.text(
            "Minimum coverage (%):",
            default=str(thresholds.get("coverage_min", 70)),
            validate=validate_percentage,
            style=get_style(),
        ).ask(),
        "Coverage threshold",
    )
    mutation_min = _check_cancelled(
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
