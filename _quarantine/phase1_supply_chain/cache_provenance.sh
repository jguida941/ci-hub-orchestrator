#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  cache_provenance.sh [--stage <name>] [--cache-dir <path>] [--output <dir>]

Generates hash-based provenance (aggregate SHA256 + optional BLAKE3) for the
primary build cache and writes JSON/NDJSON records to the evidence bundle.
Defaults to the pip cache directory.
USAGE
}

STAGE="default"
CACHE_DIR="$(python3 -m pip cache dir 2>/dev/null || echo "")"
OUTPUT_DIR="artifacts/evidence/cache"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage)
      STAGE="$2"
      shift 2
      ;;
    --cache-dir)
      CACHE_DIR="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$CACHE_DIR" || ! -d "$CACHE_DIR" ]]; then
  echo "[cache-provenance] cache directory not found: $CACHE_DIR" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
JSON_FILE="$OUTPUT_DIR/cache-${STAGE}-provenance.json"
NDJSON_FILE="$OUTPUT_DIR/cache-${STAGE}-provenance.ndjson"

export CACHE_DIR
export STAGE
export TIMESTAMP

PYTHON_OUTPUT=$(python3 - <<'PY'
import json
import os
from pathlib import Path
import hashlib

try:
    import blake3
except ImportError:
    blake3 = None

cache_dir = Path(os.environ["CACHE_DIR"]).resolve()
stage = os.environ["STAGE"]
timestamp = os.environ["TIMESTAMP"]

sha_agg = hashlib.sha256()
blake_agg = blake3.blake3() if blake3 else None
file_count = 0
total_bytes = 0

for path in sorted(cache_dir.rglob("*")):
    if not path.is_file():
        continue
    file_count += 1
    rel = path.relative_to(cache_dir).as_posix()
    size = path.stat().st_size
    total_bytes += size
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            sha.update(chunk)
            if blake_agg:
                blake_agg.update(chunk)
    sha_hex = sha.hexdigest()
    sha_agg.update(rel.encode("utf-8"))
    sha_agg.update(sha_hex.encode("utf-8"))
    sha_agg.update(str(size).encode("utf-8"))

payload = {
    "stage": stage,
    "recorded_at": timestamp,
    "cache_dir": str(cache_dir),
    "file_count": file_count,
    "total_bytes": total_bytes,
    "sha256_manifest": sha_agg.hexdigest(),
}
if blake_agg:
    payload["blake3_manifest"] = blake_agg.hexdigest()

print(json.dumps(payload))
print(
    f"[cache-provenance] stage: {stage} file_count={file_count} bytes={total_bytes} "
    f"sha256_manifest={payload['sha256_manifest']}"
)
PY
)

PROVENANCE_JSON="$(echo "$PYTHON_OUTPUT" | head -n1)"
PROVENANCE_MSG="$(echo "$PYTHON_OUTPUT" | tail -n1)"

echo "$PROVENANCE_JSON" > "$JSON_FILE"
echo "$PROVENANCE_JSON" >> "$NDJSON_FILE"
echo "$PROVENANCE_MSG"
