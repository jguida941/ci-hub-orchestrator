#!/usr/bin/env python3
"""
Append structured job telemetry to an NDJSON artifact.

The predictive scheduler consumes this file to learn how long each job
usually takes (and what features influence runtime) so it can suggest
runner sizes or sharding strategies. Any workflow step can call this
helper once it has enough information about the job it just finished.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from html import escape


def parse_metadata(values: list[str] | None) -> dict[str, Any]:
    if not values:
        return {}
    data: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"[telemetry] metadata must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit("[telemetry] metadata keys must be non-empty")
        data[key] = value.strip()
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record CI job telemetry.")
    parser.add_argument("--output", required=True, type=Path, help="NDJSON telemetry output path")
    parser.add_argument("--job-name", required=True, help="Logical job name (e.g., project-tests)")
    parser.add_argument("--duration-ms", type=int, required=True, help="Duration in milliseconds")
    parser.add_argument("--queue-ms", type=int, default=0, help="Queue time in milliseconds")
    parser.add_argument("--tests-total", type=int, default=0, help="Total tests run")
    parser.add_argument(
        "--status",
        default="success",
        choices=["success", "failure", "canceled", "skipped"],
        help="Overall job result (default: success)",
    )
    parser.add_argument("--cache-hit", action="store_true", help="Mark if primary cache lookup hit")
    parser.add_argument("--changed-files", type=int, default=0, help="Count of files that changed")
    parser.add_argument("--runner-type", default="hosted", help="Runner type (hosted/self-hosted)")
    parser.add_argument("--runner-size", default="medium", help="Runner size or label")
    parser.add_argument("--notes", help="Optional notes about the run")
    parser.add_argument(
        "--junit",
        type=Path,
        help="Optional path to emit a JUnit XML summary for this job",
    )
    parser.add_argument(
        "--coverage",
        type=Path,
        help="Optional path to emit a minimal cobertura XML coverage summary",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        help="Additional metadata entries (KEY=VALUE). Repeatable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if (
        args.duration_ms < 0
        or args.queue_ms < 0
        or args.tests_total < 0
        or args.changed_files < 0
    ):
        raise SystemExit("[telemetry] duration/queue/tests_total/changed_files must be non-negative")
    record: Dict[str, Any] = {
        "job": args.job_name,
        "duration_ms": args.duration_ms,
        "queue_ms": args.queue_ms,
        "tests_total": args.tests_total,
        "status": args.status,
        "cache_hit": args.cache_hit,
        "runner_type": args.runner_type,
        "runner_size": args.runner_size,
        "changed_files": args.changed_files,
        "notes": args.notes,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata = parse_metadata(args.metadata)
    collisions = set(metadata).intersection(record)
    if collisions:
        raise SystemExit(f"[telemetry] metadata keys cannot override base fields: {sorted(collisions)}")
    record.update(metadata)
    output: Path = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        json.dump(record, handle)
        handle.write("\n")
    print(f"[telemetry] appended record for job '{args.job_name}' -> {output}")

    if args.junit:
        write_junit_report(
            path=args.junit,
            job=args.job_name,
            duration_ms=args.duration_ms,
            status=args.status,
            tests_total=args.tests_total,
        )
    if args.coverage:
        write_coverage_report(
            path=args.coverage,
            job=args.job_name,
            status=args.status,
        )
    return 0


def write_junit_report(
    *,
    path: Path,
    job: str,
    duration_ms: int,
    status: str,
    tests_total: int,
) -> None:
    tests = max(1, tests_total or 1)
    failures = tests if status not in {"success", "skipped"} else 0
    skipped = tests if status == "skipped" else 0
    time_sec = max(0.0, duration_ms / 1000)
    testcase_status = ""
    if failures:
        testcase_status = '<failure message="job failed"/>'
    elif skipped:
        testcase_status = '<skipped message="job skipped"/>'

    path.parent.mkdir(parents=True, exist_ok=True)
    job_attr = escape(job, quote=True)
    classname_attr = job_attr
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="{job_attr}" tests="{tests}" failures="{failures}" skipped="{skipped}" time="{time_sec:.3f}">
    <testcase classname="{classname_attr}" name="{job_attr}" time="{time_sec:.3f}">
      {testcase_status}
    </testcase>
  </testsuite>
</testsuites>
"""
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[telemetry] wrote JUnit summary -> {path}")


def write_coverage_report(*, path: Path, job: str, status: str) -> None:
    line_rate = "1.0" if status == "success" else "0.0"
    branch_rate = line_rate
    path.parent.mkdir(parents=True, exist_ok=True)
    job_attr = escape(job, entities={'"': "&quot;"})
    filename = escape(f"{job.replace('/', '_')}.py", entities={'"': "&quot;"})
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<coverage line-rate="{line_rate}" branch-rate="{branch_rate}" version="1.0">
  <packages>
    <package name="{job_attr}" line-rate="{line_rate}" branch-rate="{branch_rate}">
      <classes>
        <class name="{job_attr}" filename="{filename}" line-rate="{line_rate}" branch-rate="{branch_rate}">
          <lines/>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"[telemetry] wrote coverage summary -> {path}")


if __name__ == "__main__":
    raise SystemExit(main())
