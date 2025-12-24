#!/usr/bin/env python3
"""Execute the disaster recovery drill defined by a manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if __package__ in {None, ""}:  # allow execution via `python tools/run_dr_drill.py`
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

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

    manifest_digest = result.report.notes.get("manifest_sha256")
    if manifest_digest:
        digest_path = evidence_dir / "manifest.sha256"
        manifest_reference = result.report.manifest
        digest_path.write_text(f"{manifest_digest}  {manifest_reference}\n", encoding="utf-8")

    policy = result.report.notes.get("policy") or {}
    rto = result.report.metrics.get("rto_seconds")
    rpo = result.report.metrics.get("rpo_minutes")
    max_rto = policy.get("max_rto_seconds")
    max_rpo = policy.get("max_rpo_minutes")

    passed = True
    if rto is None or rpo is None:
        passed = False
    if max_rto is not None and rto is not None and rto > max_rto:
        passed = False
    if max_rpo is not None and rpo is not None and rpo > max_rpo:
        passed = False

    status = "PASS" if passed else "FAIL"
    rto_display = f"{rto}" if rto is not None else "unknown"
    rpo_display = f"{rpo}" if rpo is not None else "unknown"
    max_rto_display = f"{max_rto}s" if max_rto is not None else "no limit"
    max_rpo_display = f"{max_rpo}m" if max_rpo is not None else "no limit"
    print(
        f"[dr-drill] {status}: "
        f"RTO={rto_display}s (limit={max_rto_display}), "
        f"RPO={rpo_display}m (limit={max_rpo_display})"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
