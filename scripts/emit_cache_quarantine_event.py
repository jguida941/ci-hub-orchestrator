#!/usr/bin/env python3
"""Emit cache quarantine telemetry events."""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone


def emit_quarantine_event(quarantine_dir: pathlib.Path, output: pathlib.Path) -> int:
    """Generate a cache quarantine event from quarantine directory contents.

    Args:
        quarantine_dir: Directory containing quarantined cache files
        output: Path to write the quarantine event JSON

    Returns:
        0 on success, 1 on failure
    """
    if not quarantine_dir.exists():
        # No quarantine directory means no files were quarantined
        event = {
            "event_type": "cache_quarantine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quarantined_count": 0,
            "files": [],
            "status": "clean",
        }
    else:
        try:
            quarantined_files = list(quarantine_dir.rglob("*"))
            # Filter out directories, only count files
            quarantined_files = [f for f in quarantined_files if f.is_file()]
        except (OSError, PermissionError) as exc:
            print(f"[cache_quarantine] Warning: Error accessing quarantine directory: {exc}")
            quarantined_files = []

        event = {
            "event_type": "cache_quarantine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quarantined_count": len(quarantined_files),
            "files": [str(f.relative_to(quarantine_dir)) for f in quarantined_files],
            "status": "quarantined" if quarantined_files else "clean",
        }

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            json.dump(event, f, indent=2)
            f.write("\n")

        print(f"[cache_quarantine] Emitted event: {event['status']} ({event['quarantined_count']} files)")
        return 0
    except (OSError, IOError) as exc:
        print(f"[cache_quarantine] Failed to write event to {output}: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Emit cache quarantine telemetry events")
    parser.add_argument(
        "--quarantine-dir",
        type=pathlib.Path,
        required=True,
        help="Directory containing quarantined cache files",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        help="Output path for quarantine event JSON",
    )
    args = parser.parse_args(argv)

    return emit_quarantine_event(args.quarantine_dir, args.output)


if __name__ == "__main__":
    raise SystemExit(main())