#!/usr/bin/env python3
"""Select a single DSSE envelope or decode its statement for downstream tooling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools import provenance_io


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a specific DSSE provenance envelope from the canonical JSON file."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the canonical provenance file (JSON array or JSONL).",
    )
    parser.add_argument("--destination", required=True, type=Path, help="Output file path.")
    parser.add_argument(
        "--digest",
        help="Optional sha256 digest to select by subject (format: sha256:<hex>).",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Fallback index to export if --digest is not supplied (default: 0).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for the exported JSON (default: 2).",
    )
    parser.add_argument(
        "--mode",
        choices=("envelope", "statement", "predicate"),
        default="envelope",
        help=(
            "Write the raw envelope, decoded statement, or just the predicate payload "
            "(default: envelope)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"source provenance file not found: {args.source}")
    records = provenance_io.load_records(args.source)
    if not records:
        raise SystemExit("provenance file is empty")
    try:
        envelope = provenance_io.select_envelope(records, args.digest, args.index)
    except provenance_io.ProvenanceParseError as exc:
        raise SystemExit(str(exc)) from exc
    output_payload = envelope
    if args.mode in {"statement", "predicate"}:
        statement = (
            envelope
            if "payload" not in envelope
            else provenance_io.decode_statement(envelope)
        )
        if not isinstance(statement, dict):
            raise SystemExit("decoded statement is not a JSON object")
        if args.mode == "statement":
            output_payload = statement
        else:
            predicate = statement.get("predicate")
            if not isinstance(predicate, dict):
                raise SystemExit("provenance predicate missing or not an object")
            output_payload = predicate

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(
        json.dumps(output_payload, indent=args.indent) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
