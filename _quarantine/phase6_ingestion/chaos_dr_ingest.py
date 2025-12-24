#!/usr/bin/env python3
"""
Load chaos and DR drill NDJSON artifacts into BigQuery tables.

The release and DR workflows already emit `artifacts/evidence/chaos/*.ndjson`
and `artifacts/evidence/dr/events.ndjson`. This script attaches run/load IDs,
optionally validates basic fields, and appends the rows to the configured
BigQuery dataset so dashboards and SLO checks can query them alongside
`pipeline_run.v1.2` records.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Sequence

try:  # Optional dependency; required when not running in --dry-run mode.
    from google.cloud import bigquery
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bigquery = None  # type: ignore
try:
    import jsonschema
except ModuleNotFoundError:  # pragma: no cover - jsonschema already required for tooling
    jsonschema = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SCHEMA_PATH = ROOT / "schema/pipeline_run.v1.2.json"
PIPELINE_SCHEMA = json.loads(PIPELINE_SCHEMA_PATH.read_text())
DR_EVENT_SCHEMA_PATH = ROOT / "schema/dr_drill.event.v1.json"
DR_EVENT_SCHEMA = json.loads(DR_EVENT_SCHEMA_PATH.read_text())

CHAOS_SCHEMA = [
    {"name": "run_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "load_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "ingested_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "fault", "field_type": "STRING"},
    {"name": "target", "field_type": "STRING"},
    {"name": "seed", "field_type": "INTEGER"},
    {"name": "rate", "field_type": "FLOAT"},
    {"name": "started_at", "field_type": "TIMESTAMP"},
    {"name": "ended_at", "field_type": "TIMESTAMP"},
    {"name": "outcome", "field_type": "STRING"},
    {"name": "retries", "field_type": "INTEGER"},
]

DR_SCHEMA = [
    {"name": "run_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "load_id", "field_type": "STRING", "mode": "REQUIRED"},
    {"name": "ingested_at", "field_type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "step", "field_type": "STRING"},
    {"name": "started_at", "field_type": "TIMESTAMP"},
    {"name": "ended_at", "field_type": "TIMESTAMP"},
    {"name": "status", "field_type": "STRING"},
    {"name": "notes", "field_type": "STRING"},
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest chaos/DR NDJSON into BigQuery tables.")
    parser.add_argument("--project", required=True, help="BigQuery project ID")
    parser.add_argument("--dataset", required=True, help="Target BigQuery dataset (e.g. ci_intel)")
    parser.add_argument("--chaos-ndjson", type=Path, help="Path to chaos NDJSON file")
    parser.add_argument("--dr-ndjson", type=Path, help="Path to DR drill NDJSON file")
    parser.add_argument(
        "--pipeline-run-ndjson",
        type=Path,
        help="Path to pipeline_run.v1.2 NDJSON artifact",
    )
    parser.add_argument("--chaos-table", default="chaos_events", help="Chaos table name (default: chaos_events)")
    parser.add_argument("--dr-table", default="dr_drills", help="DR table name (default: dr_drills)")
    parser.add_argument(
        "--pipeline-run-table",
        default="pipeline_runs",
        help="Table name for pipeline_run records (default: pipeline_runs)",
    )
    parser.add_argument("--chaos-run-id", help="Override run_id for chaos events")
    parser.add_argument("--dr-run-id", help="Override run_id for DR events")
    parser.add_argument("--load-tag", help="Optional load identifier appended to both datasets")
    parser.add_argument("--location", help="BigQuery location; defaults to dataset location")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files and print summary without calling the BigQuery API",
    )
    return parser.parse_args()


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[ingest] {path}:{lineno} invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise SystemExit(f"[ingest] {path}:{lineno} must be an object")
            items.append(payload)
    return items


def _load_pipeline_records(path: Path) -> list[dict[str, Any]]:
    if jsonschema is None:
        raise SystemExit("jsonschema is required to validate pipeline_run NDJSON")
    records = _read_ndjson(path)
    for lineno, record in enumerate(records, start=1):
        try:
            jsonschema.validate(record, PIPELINE_SCHEMA)
        except jsonschema.ValidationError as exc:
            raise SystemExit(
                f"[ingest] {path}:{lineno} fails pipeline_run.v1.2 schema validation: {exc.message}"
            ) from exc
    return records


def _validate_rows(
    rows: list[dict[str, Any]],
    *,
    schema: dict[str, Any],
    source: Path,
) -> None:
    if jsonschema is None:
        raise SystemExit("jsonschema is required to validate ingestion NDJSON")
    for lineno, row in enumerate(rows, start=1):
        try:
            jsonschema.validate(row, schema)
        except jsonschema.ValidationError as exc:
            raise SystemExit(f"[ingest] {source}:{lineno} fails schema validation: {exc.message}") from exc


def _augment_rows(
    rows: list[dict[str, Any]],
    *,
    default_run_id: str | None,
    load_tag: str | None,
) -> list[dict[str, Any]]:
    if not rows:
        return rows
    run_id = default_run_id or rows[0].get("run_id") or f"run-{uuid.uuid4()}"
    load_id = load_tag or f"load-{uuid.uuid4()}"
    ingested_at = datetime.now(tz=timezone.utc).isoformat()
    for row in rows:
        row.setdefault("run_id", run_id)
        row["load_id"] = load_id
        row["ingested_at"] = ingested_at
    return rows


def _schema_fields(raw_schema: Sequence[dict[str, Any]]):
    if bigquery is None:
        return None
    return [
        bigquery.SchemaField(field["name"], field["field_type"], mode=field.get("mode", "NULLABLE"))
        for field in raw_schema
    ]


def _load_rows(
    client: "bigquery.Client",
    table_id: str,
    rows: list[dict[str, Any]],
    schema: Sequence[dict[str, Any]],
) -> None:
    if not rows:
        print(f"[ingest] Skipping {table_id}; no rows to load")
        return
    job_config = bigquery.LoadJobConfig(
        schema=_schema_fields(schema),
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    result = job.result()  # Wait for completion
    print(f"[ingest] Loaded {result.output_rows} rows into {table_id}")


def _ensure_bigquery_available() -> None:
    if bigquery is None:  # pragma: no cover - depends on runtime env
        raise SystemExit(
            "google-cloud-bigquery is required for ingestion. "
            "Install it via `python -m pip install google-cloud-bigquery`."
        )


def _summarize(label: str, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        print(f"[ingest] {label}: 0 rows")
        return
    sample = rows[0] if rows else {}
    print(f"[ingest] {label}: {len(rows)} rows (sample keys: {sorted(sample.keys())})")


def main() -> int:
    args = _parse_args()
    chaos_rows: list[dict[str, Any]] = []
    dr_rows: list[dict[str, Any]] = []
    pipeline_rows: list[dict[str, Any]] = []

    if args.chaos_ndjson:
        if not args.chaos_ndjson.exists():
            raise SystemExit(f"[ingest] chaos NDJSON missing: {args.chaos_ndjson}")
        chaos_raw = _read_ndjson(args.chaos_ndjson)
        chaos_rows = _augment_rows(
            chaos_raw,
            default_run_id=args.chaos_run_id,
            load_tag=args.load_tag,
        )

    if args.dr_ndjson:
        if not args.dr_ndjson.exists():
            raise SystemExit(f"[ingest] DR NDJSON missing: {args.dr_ndjson}")
        dr_raw = _read_ndjson(args.dr_ndjson)
        _validate_rows(dr_raw, schema=DR_EVENT_SCHEMA, source=args.dr_ndjson)
        dr_rows = _augment_rows(
            dr_raw,
            default_run_id=args.dr_run_id,
            load_tag=args.load_tag,
        )

    if args.pipeline_run_ndjson:
        if not args.pipeline_run_ndjson.exists():
            raise SystemExit(f"[ingest] pipeline_run NDJSON missing: {args.pipeline_run_ndjson}")
        pipeline_rows = _load_pipeline_records(args.pipeline_run_ndjson)

    if args.dry_run:
        _summarize("chaos", chaos_rows)
        _summarize("dr", dr_rows)
        _summarize("pipeline_run", pipeline_rows)
        return 0

    _ensure_bigquery_available()

    client = bigquery.Client(project=args.project, location=args.location)
    if chaos_rows:
        table_id = f"{args.project}.{args.dataset}.{args.chaos_table}"
        _load_rows(client, table_id, chaos_rows, CHAOS_SCHEMA)

    if dr_rows:
        table_id = f"{args.project}.{args.dataset}.{args.dr_table}"
        _load_rows(client, table_id, dr_rows, DR_SCHEMA)

    if pipeline_rows:
        table_id = f"{args.project}.{args.dataset}.{args.pipeline_run_table}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        job = client.load_table_from_json(pipeline_rows, table_id, job_config=job_config)
        result = job.result()
        print(f"[ingest] Loaded {result.output_rows} rows into {table_id}")

    if not chaos_rows and not dr_rows and not pipeline_rows:
        print("[ingest] No files ingested; nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
