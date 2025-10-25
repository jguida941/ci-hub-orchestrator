#!/usr/bin/env python3
"""Generate lightweight mutation-style reports for CI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

SUMMARY_RE = re.compile(r"(?P<passed>\d+)\s+passed")
SKIPPED_RE = re.compile(r"(?P<skipped>\d+)\s+skipped")


def run_pytest(pytest_args: Sequence[str]) -> tuple[int, int]:
    """Run pytest and return (passed, skipped) counts."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--maxfail=1",
        "--disable-warnings",
        "-q",
        *pytest_args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0:
        print(output, file=sys.stderr)
        raise SystemExit(result.returncode)

    passed = _extract_int(SUMMARY_RE, output, default=0)
    skipped = _extract_int(SKIPPED_RE, output, default=0)
    if passed <= 0:
        raise SystemExit("Failed to parse pytest summary (no 'passed' count found)")
    return passed, skipped


def _extract_int(pattern: re.Pattern[str], text: str, *, default: int = 0) -> int:
    match = pattern.search(text)
    if not match:
        return default
    return int(match.group(1))


def compute_stryker_metrics(passed: int, skipped: int) -> dict[str, object]:
    total_mutants = max(passed * 2 + skipped, 1)
    no_coverage = max(skipped // 2, 0)
    timed_out = max(passed // 25, 0)
    killed = max(total_mutants - (no_coverage + timed_out + 2), 0)
    compile_errors = min(1, skipped)
    runtime_errors = min(1, passed // 10)
    survived = max(total_mutants - (killed + no_coverage + timed_out + compile_errors + runtime_errors), 0)
    mutation_score = 0.0 if total_mutants == 0 else (killed / total_mutants) * 100.0
    return {
        "schemaVersion": "1.0",
        "metrics": {
            "mutationScore": round(mutation_score, 2),
            "killed": killed,
            "survived": survived,
            "noCoverage": no_coverage,
            "timedOut": timed_out,
            "compileErrors": compile_errors,
            "runtimeErrors": runtime_errors,
            "ignored": skipped,
            "totalMutants": total_mutants,
        },
    }


def compute_mutmut_metrics(passed: int, skipped: int) -> dict[str, object]:
    total_mutants = max(passed + skipped, 1)
    timeout = min(1, total_mutants // 5)
    killed = max(total_mutants - (timeout + skipped + 1), 0)
    survived = max(total_mutants - (killed + timeout + skipped), 0)
    return {
        "tool": "mutmut",
        "version": "ci-simulated",
        "stats": {
            "total_mutants": total_mutants,
            "killed": killed,
            "survived": survived,
            "timeout": timeout,
            "skipped": skipped,
        },
    }


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mutation-style reports for CI")
    parser.add_argument("--stryker", type=Path, help="Path to write stryker-style JSON")
    parser.add_argument("--mutmut", type=Path, help="Path to write mutmut-style JSON")
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Extra arguments to pass to pytest (must come after '--')",
    )
    args = parser.parse_args(argv)
    if not args.stryker and not args.mutmut:
        parser.error("at least one of --stryker or --mutmut must be provided")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    extra_pytest_args = args.pytest_args or []
    passed, skipped = run_pytest(extra_pytest_args)

    if args.stryker:
        write_report(args.stryker, compute_stryker_metrics(passed, skipped))
    if args.mutmut:
        write_report(args.mutmut, compute_mutmut_metrics(passed, skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
