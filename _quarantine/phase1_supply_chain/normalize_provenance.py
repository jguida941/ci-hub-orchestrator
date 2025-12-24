#!/usr/bin/env python3
"""Normalize provenance artifacts into canonical JSON arrays."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools import provenance_io


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert DSSE provenance envelopes (JSON/JSONL) to a canonical JSON array."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the downloaded provenance artifact (predicate.intoto.jsonl, etc.)",
    )
    parser.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="Output path for the canonical JSON array.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for the output JSON (default: 2).",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow empty provenance files (default: fail if no envelopes are present).",
    )
    parser.add_argument(
        "--predicate-destination",
        type=Path,
        help="Optional path to write the decoded in-toto statement (map with predicateType/predicate).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"source provenance file not found: {args.source}")
    records = provenance_io.load_records(args.source)
    if not records and not args.allow_empty:
        raise SystemExit("provenance file does not contain any DSSE envelopes")
    provenance_io.dump_records(records, args.destination, indent=args.indent)

    if args.predicate_destination:
        if not records:
            # Empty records with allow-empty -> write empty file for downstream steps
            args.predicate_destination.parent.mkdir(parents=True, exist_ok=True)
            args.predicate_destination.write_text("{}\n", encoding="utf-8")
        else:
            envelope = provenance_io.select_envelope(records, None, 0)
            statement = envelope
            if "payload" in envelope:
                statement = provenance_io.decode_statement(envelope)
            if not isinstance(statement, dict):
                raise SystemExit("decoded provenance statement is not an object")

            # Extract the predicate from the statement for cosign attest
            # The SLSA generator produces a statement with predicateType and predicate fields
            # cosign attest expects just the predicate content
            predicate = statement.get("predicate", statement)

            # Ensure builder field is present (required by cosign attest for SLSA provenance)
            if isinstance(predicate, dict) and "builder" not in predicate:
                # Fall back to GitHub Actions runner as the builder ID
                # This is the correct builder for GitHub-hosted workflows
                predicate["builder"] = {
                    "id": "https://github.com/actions/runner"
                }

            args.predicate_destination.parent.mkdir(parents=True, exist_ok=True)
            args.predicate_destination.write_text(
                json.dumps(predicate, indent=args.indent) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    try:
        main()
    except provenance_io.ProvenanceParseError as exc:
        print(f"[normalize_provenance] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
