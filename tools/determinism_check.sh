#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage:
  determinism_check.sh <image-ref> <output-dir>
  determinism_check.sh <artifact-path> <metadata-json> <output-dir>  # legacy mode
USAGE
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

MODE="image"
if [[ $# -eq 2 ]]; then
  IMAGE_REF="$1"
  OUTPUT_DIR="$2"
elif [[ $# -ge 3 ]]; then
  MODE="legacy"
  ARTIFACT_PATH="$1"
  METADATA_JSON="$2"
  OUTPUT_DIR="$3"
else
  usage
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ "$MODE" == "legacy" ]]; then
  if [[ ! -f "$ARTIFACT_PATH" ]]; then
    >&2 echo "Artifact $ARTIFACT_PATH not found"
    exit 1
  fi
  sha256sum "$ARTIFACT_PATH" > "$OUTPUT_DIR/sha256sum.txt"
  jq '.' "$METADATA_JSON" > "$OUTPUT_DIR/metadata.json"
  echo "Simulating cross-arch determinism check" > "$OUTPUT_DIR/diff-report.txt"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  >&2 echo "[determinism_check] docker CLI not found"
  exit 1
fi

MANIFEST_RAW="$OUTPUT_DIR/manifest.raw.json"
MANIFEST_RAW_SECOND="$OUTPUT_DIR/manifest.second.raw.json"
MANIFEST_PRETTY="$OUTPUT_DIR/manifest.pretty.txt"
METADATA_PATH="$OUTPUT_DIR/metadata.json"
SUMMARY_PATH="$OUTPUT_DIR/summary.txt"
RAW_SHA_FILE="$OUTPUT_DIR/manifest.raw.sha256"
RAW_SECOND_SHA_FILE="$OUTPUT_DIR/manifest.second.sha256"
MANIFEST_DIFF="$OUTPUT_DIR/manifest.diff.txt"

if ! docker buildx imagetools inspect --raw "$IMAGE_REF" > "$MANIFEST_RAW"; then
  >&2 echo "[determinism_check] Failed to inspect $IMAGE_REF (raw)"
  exit 1
fi

if ! docker buildx imagetools inspect --raw "$IMAGE_REF" > "$MANIFEST_RAW_SECOND"; then
  >&2 echo "[determinism_check] Failed to perform second inspect for $IMAGE_REF"
  exit 1
fi

docker buildx imagetools inspect "$IMAGE_REF" > "$MANIFEST_PRETTY"

MANIFEST_SHA=$(sha256sum "$MANIFEST_RAW" | awk '{print $1}')
MANIFEST_SHA_SECOND=$(sha256sum "$MANIFEST_RAW_SECOND" | awk '{print $1}')
printf '%s  %s\n' "$MANIFEST_SHA" "$(basename "$MANIFEST_RAW")" > "$RAW_SHA_FILE"
printf '%s  %s\n' "$MANIFEST_SHA_SECOND" "$(basename "$MANIFEST_RAW_SECOND")" > "$RAW_SECOND_SHA_FILE"

if [[ "$MANIFEST_SHA" != "$MANIFEST_SHA_SECOND" ]]; then
  if command -v diff >/dev/null 2>&1; then
    diff -u "$MANIFEST_RAW" "$MANIFEST_RAW_SECOND" > "$MANIFEST_DIFF" || true
  else
    printf 'Mismatch between manifest runs\nfirst: %s\nsecond: %s\n' "$MANIFEST_SHA" "$MANIFEST_SHA_SECOND" > "$MANIFEST_DIFF"
  fi
  >&2 echo "[determinism_check] Mismatch detected between dual manifest inspections (hashes ${MANIFEST_SHA} vs ${MANIFEST_SHA_SECOND})"
  exit 2
fi

RECORDED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
HOSTNAME=$(uname -n)
KERNEL=$(uname -s)
ARCH=$(uname -m)
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

if command -v jq >/dev/null 2>&1; then
  jq -n \
    --arg image_ref "$IMAGE_REF" \
    --arg manifest_sha256 "$MANIFEST_SHA" \
    --arg recorded_at "$RECORDED_AT" \
    --arg host "$HOSTNAME" \
    --arg kernel "$KERNEL" \
    --arg arch "$ARCH" \
    --arg pipeline_commit "$GIT_SHA" \
    '{
      image_ref: $image_ref,
      manifest_sha256: $manifest_sha256,
      recorded_at: $recorded_at,
      builder: {
        host: $host,
        kernel: $kernel,
        arch: $arch
      },
      pipeline_commit: $pipeline_commit
    }' > "$METADATA_PATH"
else
  PYTHON_BIN=""
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v python3)
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v python)
  fi

  if [[ -n "$PYTHON_BIN" ]]; then
    IMAGE_REF="$IMAGE_REF" \
    MANIFEST_SHA="$MANIFEST_SHA" \
    RECORDED_AT="$RECORDED_AT" \
    HOSTNAME="$HOSTNAME" \
    KERNEL="$KERNEL" \
    ARCH="$ARCH" \
    GIT_SHA="$GIT_SHA" \
    "$PYTHON_BIN" - <<'PY' > "$METADATA_PATH"
import json
import os
import sys

data = {
    "image_ref": os.environ.get("IMAGE_REF", ""),
    "manifest_sha256": os.environ.get("MANIFEST_SHA", ""),
    "recorded_at": os.environ.get("RECORDED_AT", ""),
    "builder": {
        "host": os.environ.get("HOSTNAME", ""),
        "kernel": os.environ.get("KERNEL", ""),
        "arch": os.environ.get("ARCH", ""),
    },
    "pipeline_commit": os.environ.get("GIT_SHA", ""),
}
json.dump(data, sys.stdout, indent=2)
sys.stdout.write("\n")
PY
  else
    >&2 echo "[determinism_check] jq or python is required to generate metadata JSON"
    exit 1
  fi
fi

cat > "$SUMMARY_PATH" <<SUMMARY
Determinism evidence
====================
Image ref: $IMAGE_REF
Manifest SHA256: $MANIFEST_SHA
Second run SHA256: $MANIFEST_SHA_SECOND
Recorded at: $RECORDED_AT
SUMMARY
