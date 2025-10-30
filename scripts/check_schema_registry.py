#!/usr/bin/env python3
"""Validate schema registry metadata and fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import jsonschema

ALLOWED_COMPATIBILITY_MODES = {
    "backward",
    "backward_transitive",
    "forward",
    "forward_transitive",
    "full",
    "full_transitive",
    "none",
}
ALLOWED_VERSION_STATUSES = {"active", "deprecated"}


def _load_registry(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[schema-registry] {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("[schema-registry] registry root must be a JSON object")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _validate_date(value: str, *, field: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"[schema-registry] {field} must be ISO-8601 date (YYYY-MM-DD): {value}") from exc


def _iter_ndjson(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[schema-registry] {path}:{lineno} invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise SystemExit(f"[schema-registry] {path}:{lineno} entry must be an object")
            yield payload


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[schema-registry] schema {schema_path} is not valid JSON: {exc}") from exc


def _validate_fixtures(
    *,
    schema_path: Path,
    fixtures: list[Path],
    schema_id: str,
) -> None:
    schema = _load_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    for fixture in fixtures:
        for lineno, record in enumerate(_iter_ndjson(fixture), start=1):
            record_schema = record.get("schema")
            if record_schema != schema_id:
                raise SystemExit(
                    f"[schema-registry] {fixture}:{lineno} has schema '{record_schema}' "
                    f"but registry expects '{schema_id}'"
                )
            errors = sorted(validator.iter_errors(record), key=lambda err: err.path)
            if errors:
                error_messages = "; ".join(error.message for error in errors)
                raise SystemExit(f"[schema-registry] {fixture}:{lineno} fails validation: {error_messages}")


def _validate_topic(topic_name: str, topic: dict[str, Any], registry_dir: Path) -> None:
    owners = topic.get("owners") or []
    _require(isinstance(owners, list) and owners, f"[schema-registry] topic '{topic_name}' must list owners")
    for idx, owner in enumerate(owners):
        if not isinstance(owner, dict):
            raise SystemExit(f"[schema-registry] topic '{topic_name}' owner #{idx} must be an object")
        if not owner.get("team"):
            raise SystemExit(f"[schema-registry] topic '{topic_name}' owner #{idx} missing 'team'")
        if not (owner.get("slack") or owner.get("email")):
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' owner #{idx} must specify 'slack' or 'email' contact"
            )

    default_version = topic.get("default_version")
    _require(
        isinstance(default_version, str) and default_version,
        f"[schema-registry] topic '{topic_name}' missing 'default_version'",
    )

    description = topic.get("description")
    _require(
        isinstance(description, str) and description.strip(),
        f"[schema-registry] topic '{topic_name}' missing description",
    )

    schema_versions = topic.get("schema_versions") or []
    _require(
        isinstance(schema_versions, list) and schema_versions,
        f"[schema-registry] topic '{topic_name}' must declare schema_versions",
    )

    seen_versions: set[str] = set()

    for idx, version_info in enumerate(schema_versions):
        if not isinstance(version_info, dict):
            raise SystemExit(f"[schema-registry] topic '{topic_name}' version entry #{idx} must be an object")
        version = version_info.get("version")
        schema_id = version_info.get("schema_id")
        status = version_info.get("status")
        introduced = version_info.get("introduced")
        relative_path = version_info.get("path")
        fixtures = version_info.get("fixtures")
        compatibility = version_info.get("compatibility") or {}

        _require(
            isinstance(version, str) and version,
            f"[schema-registry] topic '{topic_name}' version #{idx} missing 'version'",
        )
        if version in seen_versions:
            raise SystemExit(f"[schema-registry] topic '{topic_name}' declares duplicate version '{version}'")
        seen_versions.add(version)

        _require(
            isinstance(schema_id, str) and schema_id,
            f"[schema-registry] topic '{topic_name}' version '{version}' missing 'schema_id'",
        )
        _require(
            isinstance(status, str) and status in ALLOWED_VERSION_STATUSES,
            f"[schema-registry] topic '{topic_name}' version '{version}' has invalid status '{status}'",
        )
        _require(
            isinstance(introduced, str) and introduced,
            f"[schema-registry] topic '{topic_name}' version '{version}' missing 'introduced' date",
        )
        _validate_date(introduced, field=f"topic '{topic_name}' version '{version}' introduced")

        _require(
            isinstance(relative_path, str) and relative_path,
            f"[schema-registry] topic '{topic_name}' version '{version}' missing schema 'path'",
        )
        schema_path = (registry_dir / relative_path).resolve()
        if not schema_path.is_file():
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' version '{version}' schema path missing: {schema_path}"
            )

        compat_mode = compatibility.get("mode")
        if compat_mode not in ALLOWED_COMPATIBILITY_MODES:
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' version '{version}' has invalid compatibility mode "
                f"'{compat_mode}'. Allowed: {sorted(ALLOWED_COMPATIBILITY_MODES)}"
            )
        prev_versions = compatibility.get("previous_versions") or []
        if not isinstance(prev_versions, list):
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' version '{version}' field 'previous_versions' "
                "must be a list"
            )

        if not isinstance(fixtures, list) or not fixtures:
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' version '{version}' must list validation fixtures"
            )
        fixture_paths = []
        for fixture_idx, fixture_rel in enumerate(fixtures):
            if not isinstance(fixture_rel, str) or not fixture_rel:
                raise SystemExit(
                    f"[schema-registry] topic '{topic_name}' version '{version}' fixture #{fixture_idx} invalid"
                )
            fixture_path = (registry_dir / fixture_rel).resolve()
            if not fixture_path.is_file():
                raise SystemExit(
                    f"[schema-registry] topic '{topic_name}' version '{version}' missing fixture: {fixture_path}"
                )
            fixture_paths.append(fixture_path)

        _validate_fixtures(schema_path=schema_path, fixtures=fixture_paths, schema_id=schema_id)

    if default_version not in seen_versions:
        raise SystemExit(
            f"[schema-registry] topic '{topic_name}' default_version '{default_version}' "
            "not present in schema_versions"
        )

    ingestion = topic.get("ingestion") or {}
    if not isinstance(ingestion, dict):
        raise SystemExit(f"[schema-registry] topic '{topic_name}' ingestion metadata must be an object")
    warehouse_model = ingestion.get("warehouse_model")
    if warehouse_model:
        model_path = (registry_dir / warehouse_model).resolve()
        if not model_path.is_file():
            raise SystemExit(
                f"[schema-registry] topic '{topic_name}' ingestion warehouse model missing: {model_path}"
            )
    dbt_models = ingestion.get("dbt_models") or []
    if dbt_models:
        if not isinstance(dbt_models, list):
            raise SystemExit(f"[schema-registry] topic '{topic_name}' ingestion dbt_models must be a list")
        for idx, model in enumerate(dbt_models):
            if not isinstance(model, str) or not model:
                raise SystemExit(
                    f"[schema-registry] topic '{topic_name}' ingestion dbt_models entry #{idx} invalid"
                )
            model_path = (registry_dir / model).resolve()
            if not model_path.is_file():
                raise SystemExit(
                    f"[schema-registry] topic '{topic_name}' ingestion dbt model not found: {model_path}"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate schema registry metadata and fixtures.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("schema/registry.json"),
        help="Path to registry JSON document (default: schema/registry.json)",
    )
    args = parser.parse_args(argv)

    registry_path = args.registry.resolve()
    if not registry_path.is_file():
        raise SystemExit(f"[schema-registry] registry document not found: {registry_path}")

    data = _load_registry(registry_path)

    topics = data.get("topics")
    if not isinstance(topics, dict) or not topics:
        raise SystemExit("[schema-registry] registry must contain non-empty 'topics' mapping")

    registry_dir = registry_path.parent.parent  # project root (schema/..)

    for topic_name, topic in topics.items():
        if not isinstance(topic, dict):
            raise SystemExit(f"[schema-registry] topic '{topic_name}' must be an object")
        _validate_topic(topic_name, topic, registry_dir)

    print(f"[schema-registry] validated {len(topics)} topic(s) from {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
