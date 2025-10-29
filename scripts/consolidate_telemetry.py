#!/usr/bin/env python3
"""Combine telemetry NDJSON fragments into a single file."""

from __future__ import annotations

import sys
from pathlib import Path


def consolidate_telemetry(input_dir: Path, output_name: str) -> None:
    sanitized_name = Path(output_name).name
    if sanitized_name != output_name or sanitized_name in (".", ".."):
        raise ValueError(f"output_name must be a filename, not a path: {output_name!r}")
    telemetry_dir = input_dir
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    output = telemetry_dir / sanitized_name

    parts = sorted(
        path
        for path in telemetry_dir.glob("*.ndjson")
        if path.is_file() and path.name != output_name
    )
    if not parts:
        if output.exists():
            output.unlink()
        return

    with output.open("w", encoding="utf-8") as handle:
        for path in parts:
            with path.open("r", encoding="utf-8") as source:
                for line in source:
                    line = line.rstrip("\n")
                    if line:
                        handle.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    input_dir = Path(args[0]) if args else Path("artifacts/telemetry")
    output_name = args[1] if len(args) > 1 else "jobs.ndjson"
    consolidate_telemetry(input_dir, output_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
