#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def derive_current_time(manifest_path: Path) -> str:
    data = _load_manifest(manifest_path)
    captured = data.get("backup", {}).get("captured_at")
    if captured is None:
        raise SystemExit("manifest backup.captured_at missing")
    try:
        dt = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"invalid backup.captured_at value: {captured}") from exc
    dt = dt.astimezone(timezone.utc) + timedelta(hours=1)
    return dt.isoformat().replace("+00:00", "Z")


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"manifest not found: {path}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in manifest {path}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive deterministic current time for DR drill workflow."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/dr/manifest.json"),
        help="Path to the DR manifest JSON file (default: data/dr/manifest.json).",
    )
    args = parser.parse_args()
    current_time = derive_current_time(args.manifest)
    print(current_time)


if __name__ == "__main__":
    main()
