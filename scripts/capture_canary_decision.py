#!/usr/bin/env python3
"""Capture canary promote/rollback evidence for the release workflow."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict


VALID_DECISIONS = {"promote", "rollback", "hold"}


def _read_query(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.is_file():
        raise SystemExit(f"canary query file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _parse_iso8601(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise SystemExit(f"invalid ISO-8601 timestamp: {value}") from exc


def _format(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_window(duration_minutes: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=duration_minutes)
    return _format(start), _format(end)


def build_decision_payload(args: argparse.Namespace) -> Dict[str, Any]:
    decision = args.decision.lower()
    if decision not in VALID_DECISIONS:
        raise SystemExit(f"decision must be one of {sorted(VALID_DECISIONS)}, got {args.decision!r}")

    if args.window_start and args.window_end:
        start_dt = _parse_iso8601(args.window_start)
        end_dt = _parse_iso8601(args.window_end)
        if start_dt >= end_dt:
            raise SystemExit("--window-start must be before --window-end")
        window_start = _format(start_dt)
        window_end = _format(end_dt)
    elif args.window_start or args.window_end:
        raise SystemExit("both --window-start and --window-end must be provided together")
    else:
        window_start, window_end = _default_window(args.window_minutes)

    query = _read_query(args.query_file)

    payload: Dict[str, Any] = {
        "decision": decision,
        "recorded_at": _format(datetime.now(timezone.utc)),
        "window": {
            "start": window_start,
            "end": window_end,
        },
    }
    if query:
        payload["query"] = query
    if args.metrics_uri:
        payload["metrics_uri"] = args.metrics_uri
    if args.notes:
        payload["notes"] = args.notes
    return payload


def write_outputs(payload: Dict[str, Any], output: Path, ndjson: Path | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if ndjson:
        ndjson.parent.mkdir(parents=True, exist_ok=True)
        with ndjson.open("a", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture canary decision evidence")
    parser.add_argument("--decision", required=True, help="promote, rollback, or hold")
    parser.add_argument("--query-file", type=Path, help="SQL/text file containing the canary query")
    parser.add_argument("--window-start", help="ISO-8601 start timestamp (UTC)")
    parser.add_argument("--window-end", help="ISO-8601 end timestamp (UTC)")
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=10,
        help="Default window duration when start/end not specified (minutes, default: 10)",
    )
    parser.add_argument("--metrics-uri", help="URI to canary metrics dashboard or artifact")
    parser.add_argument("--notes", help="Optional notes explaining the decision")
    parser.add_argument("--output", required=True, type=Path, help="JSON output path")
    parser.add_argument("--ndjson", type=Path, help="Optional NDJSON output path")
    args = parser.parse_args()
    if args.window_minutes <= 0:
        parser.error("--window-minutes must be positive")
    return args


def main() -> int:
    args = parse_args()
    payload = build_decision_payload(args)
    write_outputs(payload, args.output, args.ndjson)
    print(f"[canary-decision] recorded {payload['decision']} decision -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
