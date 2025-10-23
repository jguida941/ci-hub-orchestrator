#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  >&2 echo "Usage: $0 <provenance> <sbom> <output-dir>"
  exit 1
fi

PROVENANCE="$1"
SBOM="$2"
OUTPUT_DIR="$3"
mkdir -p "$OUTPUT_DIR"

echo "Simulating artifact recall using $PROVENANCE and $SBOM" > "$OUTPUT_DIR/recall.log"
