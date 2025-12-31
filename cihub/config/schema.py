"""Schema loading and validation utilities for CI/CD Hub config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from cihub.config.paths import PathConfig


def get_schema(paths: PathConfig) -> dict[str, Any]:
    """Load the CI Hub config schema.

    Args:
        paths: PathConfig instance.

    Returns:
        Parsed JSON schema as a dict.
    """
    schema_path = Path(paths.schema_dir) / "ci-hub-config.schema.json"
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Schema at {schema_path} is not a JSON object")
    return data


def validate_config(config: dict[str, Any], paths: PathConfig) -> list[str]:
    """Validate a config dict against the CI Hub schema.

    Args:
        config: Configuration data to validate.
        paths: PathConfig instance.

    Returns:
        Sorted list of validation error strings.
    """
    schema = get_schema(paths)
    validator = Draft7Validator(schema)
    errors: list[str] = []
    for err in validator.iter_errors(config):
        path = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return sorted(errors)
