#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 5 ]]; then
  >&2 echo "Usage: $0 <image-ref> <image-digest> <spdx-sbom> <cyclonedx-sbom> <provenance> [vex-json]"
  exit 1
fi

IMAGE_REF="$1"
IMAGE_DIGEST="$2"
SPDX_SBOM="$3"
CYCLO_SBOM="$4"
PROVENANCE="$5"
VEX_JSON="${6:-}"

: "${COSIGN_EXPERIMENTAL:=1}"

check_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    >&2 echo "[publish_referrers] Missing $label at $path"
    exit 1
  fi
}

check_file "$SPDX_SBOM" "SPDX SBOM"
check_file "$CYCLO_SBOM" "CycloneDX SBOM"
check_file "$PROVENANCE" "SLSA provenance"

if ! command -v cosign >/dev/null 2>&1; then
  >&2 echo "cosign CLI not found; install via https://github.com/sigstore/cosign"
  exit 1
fi

if ! command -v oras >/dev/null 2>&1; then
  >&2 echo "oras CLI not found; install via https://oras.land/install"
  exit 1
fi

push_referrer() {
  local artifact_path="$1"
  local artifact_type="$2"
  local annotation_name="$3"
  local digest="$4"

  oras push "${IMAGE_REF}@${digest}" \
    --artifact-type "$artifact_type" \
    --annotation "org.opencontainers.ref.name=${annotation_name}" \
    "$artifact_path"
}

echo "[publish_referrers] Uploading SPDX SBOM referrer"
push_referrer "$SPDX_SBOM" "application/spdx+json" "sbom-spdx" "$IMAGE_DIGEST"

echo "[publish_referrers] Uploading CycloneDX SBOM referrer"
push_referrer "$CYCLO_SBOM" "application/vnd.cyclonedx+json" "sbom-cyclonedx" "$IMAGE_DIGEST"

echo "[publish_referrers] Uploading SLSA provenance referrer"
push_referrer "$PROVENANCE" "application/vnd.in-toto+json" "slsa-provenance-v1" "$IMAGE_DIGEST"

if [[ -n "$VEX_JSON" ]]; then
  check_file "$VEX_JSON" "VEX advisory"
  echo "[publish_referrers] Uploading VEX referrer"
  push_referrer "$VEX_JSON" "application/vnd.cyclonedx+json" "vex" "$IMAGE_DIGEST"
fi

echo "[publish_referrers] Signing referrers with cosign (keyless)"
cosign attest --predicate "$PROVENANCE" --type slsa-provenance --keyless "${IMAGE_REF}@${IMAGE_DIGEST}"
cosign attest --predicate "$SPDX_SBOM" --type spdx --keyless "${IMAGE_REF}@${IMAGE_DIGEST}"
cosign attest --predicate "$CYCLO_SBOM" --type cyclonedx --keyless "${IMAGE_REF}@${IMAGE_DIGEST}"

if [[ -n "$VEX_JSON" ]]; then
  cosign attest --predicate "$VEX_JSON" --type vex --keyless "${IMAGE_REF}@${IMAGE_DIGEST}"
fi

echo "[publish_referrers] Referrer publication completed"
