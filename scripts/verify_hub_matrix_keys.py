#!/usr/bin/env python3
"""
Verify that all matrix.<key> references in hub-run-all.yml are emitted by the
embedded matrix builder.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "hub-run-all.yml"

MATRIX_REF_RE = re.compile(r"\bmatrix\.([A-Za-z_][A-Za-z0-9_]*)\b")
ENTRY_LITERAL_KEY_RE = re.compile(r'\n\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*')
ENTRY_ASSIGN_RE = re.compile(r'\bentry\[\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*\]')
FOR_KEY_TUPLE_RE = re.compile(r"for key in\s*\(\s*(.*?)\s*\)\s*:", re.S)
QUOTED_KEY_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"')


def main() -> int:
    if not WF.exists():
        print(f"ERROR: {WF} not found", file=sys.stderr)
        return 2

    text = WF.read_text(encoding="utf-8")

    referenced = set(MATRIX_REF_RE.findall(text))

    emitted = set(ENTRY_LITERAL_KEY_RE.findall(text))
    emitted.update(ENTRY_ASSIGN_RE.findall(text))

    for match in FOR_KEY_TUPLE_RE.finditer(text):
        emitted.update(QUOTED_KEY_RE.findall(match.group(1)))

    # Baseline keys always present in the entry literal
    emitted.update({"name", "owner", "language", "config_basename"})

    missing = sorted(referenced - emitted)
    unused = sorted(emitted - referenced)

    if missing:
        print("ERROR: matrix keys referenced but not emitted by builder:")
        for key in missing:
            print(f"  - {key}")
        return 1

    print("OK: all referenced matrix keys are emitted by the builder.")

    if unused:
        print("\nWARN: builder emits keys not referenced as matrix.<key> in this workflow:")
        for key in unused:
            print(f"  - {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
