#!/usr/bin/env python3
"""Execute the disaster recovery drill defined by a manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.dr_drill import DrDrillError, run_drill


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DR drill from a manifest.")
    parser.add_argument("--manifest", type=Path, default=Path("data/dr/manifest.json"), help="Path to the DR drill manifest")
    parser.add_argument("--output", required=True, type=Path, help="JSON report output path")
    parser.add_argument("--ndjson", required=True, type=Path, help="NDJSON events output path")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Directory for additional drill artifacts (defaults to report directory)",
    )
    parser.add_argument(
        "--current-time",
        type=str,
        default=None,
        help="Override the current time (ISO-8601, used for testing RPO calculations)",
    )
    return parser.parse_args()


def parse_current_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"invalid --current-time value: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def write_report(report_path: Path, payload: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_events(events_path: Path, events: list[dict]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def main() -> int:
    args = parse_args()
    evidence_dir = args.evidence_dir or args.output.parent
    current_time = parse_current_time(args.current_time)

    try:
        result = run_drill(args.manifest, evidence_dir, now=current_time)
    except DrDrillError as exc:
        print(f"DR drill failed: {exc}", file=sys.stderr)
        return 1

    write_report(args.output, result.report.to_dict())
    write_events(args.ndjson, [event.to_dict() for event in result.events])

    # Persist machine-readable metrics alongside the primary report.
    metrics_path = evidence_dir / "drill-metrics.json"
    write_report(
        metrics_path,
        {
            "run_id": result.report.run_id,
            "backup_captured_at": result.report.backup_captured_at,
            "metrics": result.report.metrics,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
