#!/usr/bin/env python3
"""
Aggregate emitted artifacts (pipeline runs, autopsy, scheduler, etc.)
into a lightweight "warehouse" directory for dashboards/dbt runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"[ingest] artifact missing: {path}")
    rows: list[dict[str, Any]] = []
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
                raise SystemExit(f"[ingest] {path}:{lineno} must contain objects")
            rows.append(payload)
    return rows


def load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ingest] {path} invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"[ingest] {path} must contain a JSON object")
    return payload


def write_records(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle)
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Load CI artifacts into a local warehouse directory.")
    parser.add_argument("--warehouse-dir", required=True, type=Path, help="Destination directory")
    parser.add_argument("--pipeline-run", type=Path, help="pipeline_run NDJSON")
    parser.add_argument("--autopsy", type=Path, help="autopsy findings NDJSON")
    parser.add_argument("--scheduler", type=Path, help="predictive scheduler JSON report")
    parser.add_argument("--telemetry", type=Path, help="job telemetry NDJSON")
    args = parser.parse_args()

    warehouse = args.warehouse_dir
    warehouse.mkdir(parents=True, exist_ok=True)

    if args.pipeline_run:
        runs = load_ndjson(args.pipeline_run)
        write_records(warehouse / "pipeline_runs.ndjson", runs)
        print(f"[ingest] wrote {len(runs)} pipeline_run rows")

    if args.autopsy:
        findings = load_ndjson(args.autopsy)
        write_records(warehouse / "autopsy_findings.ndjson", findings)
        print(f"[ingest] wrote {len(findings)} autopsy rows")

    if args.telemetry:
        telemetry_rows = load_ndjson(args.telemetry)
        write_records(warehouse / "job_telemetry.ndjson", telemetry_rows)
        print(f"[ingest] wrote {len(telemetry_rows)} telemetry rows")

    if args.scheduler:
        report = load_json(args.scheduler)
        (warehouse / "scheduler_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("[ingest] stored scheduler recommendation")

    summary_path = warehouse / "SUMMARY.md"
    summary_lines = [
        "# Warehouse Snapshot",
        "",
        f"- pipeline runs: {count_lines(warehouse / 'pipeline_runs.ndjson')}",
        f"- autopsy findings: {count_lines(warehouse / 'autopsy_findings.ndjson')}",
        f"- telemetry samples: {count_lines(warehouse / 'job_telemetry.ndjson')}",
        f"- scheduler report: {'present' if (warehouse / 'scheduler_report.json').exists() else 'absent'}",
        "",
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"[ingest] summary written to {summary_path}")
    return 0


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle if _.strip())


if __name__ == "__main__":
    raise SystemExit(main())
