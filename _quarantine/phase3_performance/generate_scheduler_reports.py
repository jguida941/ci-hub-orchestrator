#!/usr/bin/env python3
"""Generate predictive scheduler reports for every job present in telemetry."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.predictive_scheduler import (  # noqa: E402
    JobSample,
    load_samples,
    summarize,
    write_markdown,
    write_report,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", required=True, type=Path, help="Telemetry NDJSON file")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write reports into")
    return parser.parse_args()


def _slug(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in value)
    return cleaned or "job"


def _jobs_from_samples(samples: Iterable[JobSample]) -> list[str]:
    return sorted({sample.job for sample in samples if sample.job})


def main() -> int:
    args = _parse_args()
    samples = load_samples(args.telemetry)
    jobs = _jobs_from_samples(samples)
    if not jobs:
        raise SystemExit("[scheduler] telemetry file contains no job identifiers")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    for job in jobs:
        report = summarize(job, samples)
        slug = _slug(job)
        report_path = args.output_dir / f"{slug}.json"
        markdown_path = args.output_dir / f"{slug}.md"
        write_report(report, report_path)
        write_markdown(report, markdown_path)
        reports.append(report)

    batch = {
        "schema": "predictive_scheduler.batch.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jobs": reports,
    }
    (args.output_dir / "recommendations.json").write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")

    summary_lines = ["# Predictive Scheduler Summary", ""]
    for report in reports:
        rec = report["recommendation"]["runner_size"]
        summary_lines.append(f"- {report['job']}: {rec}")
    summary_lines.append("")
    (args.output_dir / "recommendations.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"[scheduler] generated reports for {len(reports)} job(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
