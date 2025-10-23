#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import jsonschema

SCHEMA = json.loads(Path("schema/pipeline_run.v1.2.json").read_text())


def validate_ndjson(path: Path) -> int:
    errors = 0
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[schema-check] {path}:{lineno} invalid JSON: {exc}")
                errors += 1
                continue
            try:
                jsonschema.validate(payload, SCHEMA)
            except jsonschema.ValidationError as exc:
                print(f"[schema-check] {path}:{lineno} validation error: {exc.message}")
                errors += 1
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    total_errors = 0
    for ndjson_path in args.paths:
        if not ndjson_path.exists():
            print(f"[schema-check] {ndjson_path} missing")
            total_errors += 1
            continue
        total_errors += validate_ndjson(ndjson_path)

    if total_errors:
        print(f"[schema-check] failed with {total_errors} error(s)")
    else:
        print("[schema-check] all NDJSON files valid")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
