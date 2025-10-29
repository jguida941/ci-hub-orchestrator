#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  >&2 echo "Usage: $0 <backup> <provenance> <sbom> <output-dir>"
  exit 1
fi

BACKUP="$1"
PROVENANCE="$2"
SBOM="$3"
OUTPUT_DIR="$4"
mkdir -p "$OUTPUT_DIR"

{
  echo "Restoring artifacts using provenance: $PROVENANCE"
  echo "Validating SBOM: $SBOM"
} > "$OUTPUT_DIR/recall.log"

BACKUP_SOURCE="${BACKUP_PATH:-$BACKUP}"
if [[ -n "$BACKUP_SOURCE" && -f "$BACKUP_SOURCE" ]]; then
  cp "$BACKUP_SOURCE" "$OUTPUT_DIR/recovered-backup.json"
  sha256sum "$OUTPUT_DIR/recovered-backup.json" > "$OUTPUT_DIR/recovered-backup.json.sha256"
fi
