#!/usr/bin/env python3
"""
Validate a CI/CD Hub config file against the schema.

Usage:
  python scripts/validate_config.py config/repos/my-repo.yaml
  python scripts/validate_config.py path/to/.ci-hub.yml \
    --schema hub-release/schema/ci-hub-config.schema.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must start with a YAML mapping")
    return data


def validate_config(config: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft7Validator(schema)
    errors = []
    for err in sorted(
        validator.iter_errors(config),
        key=lambda e: ".".join(map(str, e.path)),
    ):
        path = ".".join([str(p) for p in err.path]) or "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def main() -> int:
    description = "Validate CI/CD Hub config YAML against schema."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config",
        type=Path,
        help="Path to config YAML (.ci-hub.yml or hub config)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "schema"
        / "ci-hub-config.schema.json",
        help="Path to JSON schema",
    )
    args = parser.parse_args()

    schema_path = args.schema
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}", file=sys.stderr)
        return 1

    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema_data, dict):
        print("Schema must be a JSON object at the top level", file=sys.stderr)
        return 1
    schema = schema_data
    config = load_yaml(args.config)
    if "language" not in config:
        repo_block = config.get("repo")
        if isinstance(repo_block, dict) and repo_block.get("language"):
            config["language"] = repo_block["language"]

    errors = validate_config(config, schema)
    if errors:
        print(f"Validation failed for {args.config}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK: {args.config} is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
