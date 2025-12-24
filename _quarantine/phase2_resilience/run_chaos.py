#!/usr/bin/env python3
"""Simulate chaos experiments and produce JSON/NDJSON evidence."""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class ChaosEvent:
    fault: str
    target: str
    seed: int
    rate: float
    started_at: str
    ended_at: str
    outcome: str
    retries: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chaos experiments (simulated).")
    parser.add_argument("--config", required=True, type=Path, help="Chaos config JSON")
    parser.add_argument("--output", required=True, type=Path, help="JSON report output")
    parser.add_argument("--ndjson", required=True, type=Path, help="NDJSON events output")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def run_experiments(config: dict[str, Any]) -> list[ChaosEvent]:
    experiments = []
    for entry in config.get("experiments", []):
        seed = entry.get("seed", random.randint(1, 999999))  # noqa: S311  # nosec B311 - chaos seeds are for simulation only
        random.seed(seed)
        duration = random.uniform(5, 20)  # noqa: S311  # nosec B311 - bounded simulation timing
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        time.sleep(0.01)  # simulate work
        ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        retries = random.randint(0, 2)  # noqa: S311  # nosec B311 - non-cryptographic retry count
        experiments.append(
            ChaosEvent(
                fault=entry.get("fault", "kill_pod"),
                target=entry.get("target", "worker"),
                seed=seed,
                rate=entry.get("rate", 0.01),
                started_at=started,
                ended_at=ended,
                outcome=random.choice(["recovered", "degraded"]),  # noqa: S311  # nosec B311 - simulated outcome selection
                retries=retries,
            )
        )
    return experiments


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    events = run_experiments(config)

    report = {
        "schema": "chaos_report.v1",
        "run_id": config.get("run_id", ""),
        "experiments": [asdict(ev) for ev in events],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")

    args.ndjson.parent.mkdir(parents=True, exist_ok=True)
    with args.ndjson.open("w") as handle:
        for event in events:
            handle.write(json.dumps(asdict(event)) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
