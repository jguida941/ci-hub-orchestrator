#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.kyverno_policy_checker import evaluate_resource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run static admission checks against sample resources.")
    parser.add_argument(
        "--policies",
        type=Path,
        default=Path("policies/kyverno"),
        help="Directory containing Kyverno policy manifests.",
    )
    parser.add_argument(
        "--resources",
        type=Path,
        default=Path("fixtures/kyverno"),
        help="Directory with workload examples to evaluate.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policies_dir = args.policies
    resources_dir = args.resources

    if not policies_dir.exists():
        print(f"[kyverno-test] policy directory missing: {policies_dir}", file=sys.stderr)
        return 2
    if not resources_dir.exists():
        print(f"[kyverno-test] resource directory missing: {resources_dir}", file=sys.stderr)
        return 2

    overall_pass = True
    for resource_path in sorted(resources_dir.glob("*.yaml")):
        try:
            results = evaluate_resource(policies_dir, resource_path)
        except Exception as exc:  # pragma: no cover - surfaced in CI
            print(f"[kyverno-test] ERROR {resource_path.name}: {exc}", file=sys.stderr)
            overall_pass = False
            continue
        for result in results:
            resource_stem = getattr(getattr(result, "resource", None), "stem", None)
            check_name = getattr(result, "check", None) or resource_stem or result.__class__.__name__
            if getattr(result, "passed", False):
                print(f"[kyverno-test] PASS {resource_path.name} :: {check_name}")
            else:
                overall_pass = False
                failures = tuple(getattr(result, "failures", ()))
                for failure in failures:
                    print(f"[kyverno-test] FAIL {resource_path.name}: {failure}", file=sys.stderr)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
