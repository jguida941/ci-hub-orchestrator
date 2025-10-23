#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  >&2 echo "Usage: $0 <artifact-path> <metadata-json> <output-dir>"
  exit 1
fi

ARTIFACT_PATH="$1"
METADATA_JSON="$2"
OUTPUT_DIR="$3"

if [[ ! -f "$ARTIFACT_PATH" ]]; then
  >&2 echo "Artifact $ARTIFACT_PATH not found"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

sha256sum "$ARTIFACT_PATH" > "$OUTPUT_DIR/sha256sum.txt"

jq '.' "$METADATA_JSON" > "$OUTPUT_DIR/metadata.json"

echo "Simulating cross-arch determinism check" > "$OUTPUT_DIR/diff-report.txt"
