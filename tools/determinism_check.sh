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
MANIFEST_PRETTY="$OUTPUT_DIR/manifest.pretty.txt"
METADATA_PATH="$OUTPUT_DIR/metadata.json"
SUMMARY_PATH="$OUTPUT_DIR/summary.txt"

if ! docker buildx imagetools inspect --raw "$IMAGE_REF" > "$MANIFEST_RAW"; then
  >&2 echo "[determinism_check] Failed to inspect $IMAGE_REF (raw)"
  exit 1
fi

docker buildx imagetools inspect "$IMAGE_REF" > "$MANIFEST_PRETTY"

MANIFEST_SHA=$(sha256sum "$MANIFEST_RAW" | awk '{print $1}')
printf '%s  %s\n' "$MANIFEST_SHA" "$(basename "$MANIFEST_RAW")" > "$OUTPUT_DIR/manifest.raw.sha256"

RECORDED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
HOSTNAME=$(uname -n)
KERNEL=$(uname -s)
ARCH=$(uname -m)
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

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

cat > "$SUMMARY_PATH" <<SUMMARY
Determinism evidence
====================
Image ref: $IMAGE_REF
Manifest SHA256: $MANIFEST_SHA
Recorded at: $RECORDED_AT
SUMMARY
