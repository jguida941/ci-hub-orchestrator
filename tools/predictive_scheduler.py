#!/usr/bin/env python3
"""Simple predictive scheduler that recommends runner sizes for CI jobs."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

SCHEMA_VERSION = "predictive_scheduler.v1"


@dataclass
class JobSample:
    job: str
    duration_ms: int
    queue_ms: int
    tests_total: int
    cache_hit: bool
    changed_files: int
    runner_type: str
    runner_size: str


def load_samples(path: Path) -> list[JobSample]:
    samples: list[JobSample] = []
    if not path.exists():
        raise SystemExit(f"[scheduler] telemetry file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"[scheduler] {path}:{lineno} invalid JSON: {exc}") from exc
            try:
                job = str(payload["job"])
                duration_ms = int(payload["duration_ms"])
                queue_ms = int(payload.get("queue_ms", 0))
                tests_total = int(payload.get("tests_total", 0))
                changed_files = int(payload.get("changed_files", 0))
                cache_hit = bool(payload.get("cache_hit", False))
                runner_type = str(payload.get("runner_type", "hosted"))
                runner_size = str(payload.get("runner_size", "medium"))
            except (KeyError, ValueError, TypeError) as exc:
                raise SystemExit(f"[scheduler] {path}:{lineno} missing fields: {exc}") from exc
            numeric_fields = {
                "duration_ms": duration_ms,
                "queue_ms": queue_ms,
                "tests_total": tests_total,
                "changed_files": changed_files,
            }
            for field, value in numeric_fields.items():
                if value < 0:
                    raise SystemExit(f"[scheduler] {path}:{lineno} negative {field}: {value}")
            samples.append(
                JobSample(
                    job=job,
                    duration_ms=duration_ms,
                    queue_ms=queue_ms,
                    tests_total=tests_total,
                    cache_hit=cache_hit,
                    changed_files=changed_files,
                    runner_type=runner_type,
                    runner_size=runner_size,
                )
            )
    if not samples:
        raise SystemExit(f"[scheduler] telemetry file {path} contained no rows")
    return samples


def summarize(job: str, samples: Sequence[JobSample]) -> dict[str, Any]:
    job_samples = [s for s in samples if s.job == job]
    if not job_samples:
        raise SystemExit(f"[scheduler] no samples found for job '{job}'")
    durations = [s.duration_ms for s in job_samples]
    avg = statistics.fmean(durations)
    p95 = percentile(durations, 0.95)
    cache_hit_rate = sum(1 for s in job_samples if s.cache_hit) / len(job_samples)
    avg_changed = statistics.fmean([s.changed_files for s in job_samples])
    avg_tests = statistics.fmean([s.tests_total for s in job_samples])
    runner_counts = defaultdict(int)
    for s in job_samples:
        runner_counts[s.runner_size] += 1
    most_common_runner = max(runner_counts, key=lambda key: runner_counts[key])
    recommendation = recommend_runner(avg, p95, avg_tests, avg_changed)
    return {
        "schema": SCHEMA_VERSION,
        "job": job,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(job_samples),
        "stats": {
            "avg_duration_ms": round(avg, 2),
            "p95_duration_ms": p95,
            "avg_tests_total": round(avg_tests, 2),
            "avg_changed_files": round(avg_changed, 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "most_common_runner": most_common_runner,
        },
        "recommendation": recommendation,
    }


def recommend_runner(
    avg_duration_ms: float,
    p95_duration_ms: float,
    avg_tests_total: float,
    avg_changed_files: float,
) -> dict[str, Any]:
    buckets = [
        ("small", 4 * 60 * 1000),
        ("medium", 8 * 60 * 1000),
        ("large", 12 * 60 * 1000),
    ]
    runner_size = "xl"
    for size, threshold in buckets:
        if p95_duration_ms <= threshold:
            runner_size = size
            break

    sharding_hint = avg_tests_total > 2000 or avg_duration_ms > 10 * 60 * 1000
    cold_start_risk = avg_changed_files > 40
    notes: list[str] = []
    if sharding_hint:
        notes.append("Split test matrix or parallelize suites")
    if cold_start_risk:
        notes.append("High file churn detected; pre-warm caches or run selective builds")

    return {
        "runner_size": runner_size,
        "expected_p95_minutes": round(p95_duration_ms / 60000, 2),
        "shard_recommended": bool(sharding_hint),
        "notes": notes,
    }


def percentile(values: Sequence[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return float(ordered[int(k)])
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return float(d0 + d1)


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_markdown(report: dict[str, Any], path: Path) -> None:
    stats = report["stats"]
    rec = report["recommendation"]
    lines = [
        "# Predictive Scheduler",
        "",
        f"- Job: `{report['job']}`",
        f"- Samples: {report['sample_size']}",
        f"- Recommended runner: **{rec['runner_size']}** (p95 ≈ {rec['expected_p95_minutes']} min)",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Avg duration (ms) | {stats['avg_duration_ms']} |",
        f"| P95 duration (ms) | {stats['p95_duration_ms']} |",
        f"| Avg tests | {stats['avg_tests_total']} |",
        f"| Avg changed files | {stats['avg_changed_files']} |",
        f"| Cache hit rate | {stats['cache_hit_rate']} |",
        "",
    ]
    notes: Iterable[str] = rec.get("notes") or []
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend runner sizes using telemetry.")
    parser.add_argument("--telemetry", required=True, type=Path, help="NDJSON telemetry file")
    parser.add_argument("--job", required=True, help="Job to generate recommendations for")
    parser.add_argument("--output", type=Path, required=True, help="JSON report path")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown summary path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    samples = load_samples(args.telemetry)
    report = summarize(args.job, samples)
    write_report(report, args.output)
    if args.markdown:
        write_markdown(report, args.markdown)
    print(f"[scheduler] generated recommendation for job '{args.job}' (n={report['sample_size']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
