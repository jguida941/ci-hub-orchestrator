#!/usr/bin/env python3
"""
Convert PIT mutations.xml into Stryker-style and mutmut-style JSON reports.

This lets Mutation Observatory consume Java mutation results without stubbing.
"""
from __future__ import annotations

import argparse
import json
import sys
from defusedxml import ElementTree as ET  # safe XML parsing
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PIT mutations.xml to JSON reports")
    parser.add_argument("--input", required=True, type=Path, help="Path to PIT mutations.xml")
    parser.add_argument("--stryker", required=True, type=Path, help="Path to write Stryker-style JSON")
    parser.add_argument("--mutmut", required=True, type=Path, help="Path to write mutmut-style JSON")
    return parser.parse_args()


def load_mutations(path: Path) -> List[Dict[str, Any]]:
    tree = ET.parse(path)
    root = tree.getroot()
    mutations = []
    for idx, m in enumerate(root.iter("mutation")):
        status = m.attrib.get("status", "").upper()
        mutated_class = (m.findtext("mutatedClass") or "").strip()
        mutated_method = (m.findtext("mutatedMethod") or "").strip()
        line = int(m.findtext("lineNumber") or 0)
        mutator = (m.findtext("mutator") or "").split(".")[-1]
        mutations.append(
            {
                "id": idx,
                "status": status,
                "mutator": mutator,
                "location": {
                    "class": mutated_class,
                    "method": mutated_method,
                    "line": line,
                },
            }
        )
    return mutations


def write_reports(mutants: List[Dict[str, Any]], stryker_path: Path, mutmut_path: Path) -> None:
    total = len(mutants)
    killed = sum(1 for m in mutants if m["status"] == "KILLED")
    survived = sum(1 for m in mutants if m["status"] == "SURVIVED")
    timeout = sum(1 for m in mutants if m["status"] == "TIMED_OUT")
    no_coverage = sum(1 for m in mutants if m["status"] == "NO_COVERAGE")
    mutation_score = (killed / total * 100.0) if total else 0.0

    stryker_payload: Dict[str, Any] = {
        "metrics": {
            "totalMutants": total,
            "killed": killed,
            "survived": survived,
            "timedOut": timeout,
            "noCoverage": no_coverage,
            "ignored": 0,
            "compileErrors": 0,
            "runtimeErrors": 0,
            "mutationScore": mutation_score,
        },
        "mutants": mutants,
    }

    mutmut_payload: Dict[str, Any] = {
        "tool": "pitest",
        "stats": {
            "total_mutants": total,
            "killed": killed,
            "survived": survived,
            "timeout": timeout,
            "no_coverage": no_coverage,
        },
        "mutants": mutants,
    }

    stryker_path.parent.mkdir(parents=True, exist_ok=True)
    mutmut_path.parent.mkdir(parents=True, exist_ok=True)
    stryker_path.write_text(json.dumps(stryker_payload, indent=2), encoding="utf-8")
    mutmut_path.write_text(json.dumps(mutmut_payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"Input PIT report not found: {args.input}", file=sys.stderr)
        return 1
    mutants = load_mutations(args.input)
    write_reports(mutants, args.stryker, args.mutmut)
    print(f"[pitest-to-json] wrote {args.stryker} and {args.mutmut} from {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
