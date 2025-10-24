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
: "${COSIGN_YES:=true}"
export COSIGN_EXPERIMENTAL
export COSIGN_YES

REKOR_INDEX_FILE=${REKOR_INDEX_FILE:-artifacts/evidence/rekor-indices.txt}

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

COSIGN_VERSION_STR=$(cosign version 2>/dev/null || true)
if [[ -n "$COSIGN_VERSION_STR" ]]; then
  echo "[publish_referrers] Using cosign version:"
  printf '%s\n' "$COSIGN_VERSION_STR"
fi

if ! command -v oras >/dev/null 2>&1; then
  >&2 echo "oras CLI not found; install via https://oras.land/install"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  >&2 echo "jq CLI not found; install via https://stedolan.github.io/jq/"
  exit 1
fi

log_token_expiry() {
  local token="$1"
  if [[ -z "$token" ]]; then
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[publish_referrers] python3 not available; skipping OIDC token expiry check"
    return 0
  fi
  python3 - <<'PY' "$token"
import base64
import json
import sys
import time

token = sys.argv[1]
parts = token.split(".")
if len(parts) < 2:
    print("[publish_referrers] OIDC token missing payload segment")
    sys.exit(0)

segment = parts[1]
padding = "=" * (-len(segment) % 4)
try:
    payload = json.loads(base64.urlsafe_b64decode(segment + padding).decode("utf-8"))
except Exception as exc:
    print(f"[publish_referrers] Failed to decode OIDC token payload: {exc}")
    sys.exit(0)

exp = payload.get("exp")
if isinstance(exp, int):
    remaining = exp - int(time.time())
    print(f"[publish_referrers] OIDC token expires in {remaining}s (unix exp={exp})")
else:
    print("[publish_referrers] OIDC token missing numeric exp claim")
PY
}

fetch_oidc_token() {
  if [[ -n "${COSIGN_IDENTITY_TOKEN:-}" ]]; then
    printf '%s' "${COSIGN_IDENTITY_TOKEN}"
    return 0
  fi
  if [[ -n "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" && -n "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]]; then
    local audience="${COSIGN_OIDC_AUDIENCE:-sigstore}"
    local url="${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=${audience}"
    local response
    if ! response=$(curl -sf -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" "$url"); then
      >&2 echo "[publish_referrers] Failed to fetch GitHub OIDC token"
      return 1
    fi
    local token
    token=$(printf '%s' "$response" | jq -r '.value // empty')
    if [[ -z "$token" ]]; then
      >&2 echo "[publish_referrers] Empty OIDC token fetched from GitHub"
      return 1
    fi
    printf '%s' "$token"
    log_token_expiry "$token" >&2
    return 0
  fi
  return 1
}

append_rekor_index_file() {
  local file="$1"
  local digest="$2"
  local index
  index=$(awk '/tlog entry created with index:/ {print $NF}' "$file" | grep -E '^[0-9]+$' | tail -n1 || true)
  if [[ -n "$index" ]]; then
    mkdir -p "$(dirname "$REKOR_INDEX_FILE")"
    if [[ -n "$digest" ]]; then
      printf '%s %s\n' "$index" "$digest" >> "$REKOR_INDEX_FILE"
    else
      printf '%s\n' "$index" >> "$REKOR_INDEX_FILE"
    fi
  fi
}

run_cosign_attest() {
  local tmp_file
  tmp_file=$(mktemp)
  local status
  local subject="${@: -1}"
  local subject_digest=""
  if [[ "$subject" == *@* ]]; then
    subject_digest="${subject##*@}"
  fi
  if [[ -z "$subject_digest" && -n "$IMAGE_DIGEST" ]]; then
    subject_digest="$IMAGE_DIGEST"
  fi
  set +e
  cosign "$@" 2>&1 | tee "$tmp_file"
  status=${PIPESTATUS[0]}
  set -e
  append_rekor_index_file "$tmp_file" "$subject_digest"
  rm -f "$tmp_file"
  return "$status"
}

attest_provenance() {
  local subject="$1"
  local predicate="$2"
  local types=()

  local detected_type
  detected_type=$(jq -r '.predicateType // empty' "$predicate" 2>/dev/null || true)

  if [[ -n "${COSIGN_PROVENANCE_TYPES:-}" ]]; then
    local raw_types="${COSIGN_PROVENANCE_TYPES}"
    local old_ifs="$IFS"
    IFS=',' read -r -a types <<< "$raw_types"
    IFS="$old_ifs"
  else
    types=(
      "https://slsa.dev/provenance/v1"
      "https://slsa.dev/provenance/v1.0"
      "https://slsa.dev/provenance/v0.2"
      "slsaprovenance@v1"
      "slsaprovenance"
      "slsa-provenance"
    )
  fi

  local tried=()
  if [[ -n "$detected_type" ]]; then
    local unique_types=("$detected_type")
    for type in "${types[@]}"; do
      local duplicate=false
      for existing in "${unique_types[@]}"; do
        if [[ "$type" == "$existing" ]]; then
          duplicate=true
          break
        fi
      done
      if [[ "$duplicate" == false ]]; then
        unique_types+=("$type")
      fi
    done
    types=("${unique_types[@]}")
  fi
  for type in "${types[@]}"; do
    if [[ -z "$type" ]]; then
      continue
    fi
    tried+=("$type")
    echo "[publish_referrers] Signing provenance with cosign type '${type}'"
    local args=(attest --predicate "$predicate" --type "$type" --yes)
    local oidc_token=""
    if oidc_token=$(fetch_oidc_token); then
      echo "[publish_referrers] Using GitHub OIDC token for cosign (length ${#oidc_token})"
      log_token_expiry "$oidc_token"
      export SIGSTORE_ID_TOKEN="$oidc_token"
      local display_args=("${args[@]}")
      display_args+=("--identity-token" "<redacted>")
      echo "[publish_referrers] cosign command: cosign ${display_args[*]} $subject"
      args+=("--identity-token" "$oidc_token")
    else
      >&2 echo "[publish_referrers] Proceeding without explicit identity token (fallback to device flow)"
      echo "[publish_referrers] cosign command: cosign ${args[*]} $subject"
    fi
    if run_cosign_attest "${args[@]}" "$subject"; then
      return 0
    fi
    >&2 echo "[publish_referrers] cosign attest failed for type '${type}'"
  done

  >&2 echo "[publish_referrers] Unable to sign provenance; tried types: ${tried[*]}"
  return 1
}

sign_with_token() {
  local predicate_path="$1"
  local predicate_type="$2"
  local subject="$3"
  local args=(attest --predicate "$predicate_path" --type "$predicate_type" --yes)
  local oidc_token=""
  if oidc_token=$(fetch_oidc_token); then
    echo "[publish_referrers] Using GitHub OIDC token for cosign (length ${#oidc_token})"
    log_token_expiry "$oidc_token"
    export SIGSTORE_ID_TOKEN="$oidc_token"
    local display_args=("${args[@]}")
    display_args+=("--identity-token" "<redacted>")
    echo "[publish_referrers] cosign command: cosign ${display_args[*]} $subject"
    args+=("--identity-token" "$oidc_token")
  else
    >&2 echo "[publish_referrers] Proceeding without explicit identity token for type '${predicate_type}'"
    echo "[publish_referrers] cosign command: cosign ${args[*]} $subject"
  fi
  run_cosign_attest "${args[@]}" "$subject"
}

push_referrer() {
  local artifact_path="$1"
  local artifact_type="$2"
  local annotation_name="$3"
  local digest="$4"

  local attach_output
  if ! attach_output=$(oras attach \
    --artifact-type "$artifact_type" \
    --annotation "org.opencontainers.ref.name=${annotation_name}" \
    "${IMAGE_REF}@${digest}" \
    "$artifact_path"); then
    >&2 echo "[publish_referrers] Failed to attach ${annotation_name} (${artifact_type}) to ${IMAGE_REF}@${digest}"
    exit 1
  fi

  printf '%s\n' "$attach_output"

  local attached_digest
  attached_digest=$(printf '%s\n' "$attach_output" | awk '/Digest:/ {print $2}' | tail -n1)
  if [[ -z "$attached_digest" ]]; then
    >&2 echo "[publish_referrers] Unable to parse attached referrer digest for ${annotation_name}"
    exit 1
  fi

  local attempts=0
  local max_attempts=10
  local found=0
  local discover_output
  local tmp_json
  tmp_json=$(mktemp)

  while [[ $attempts -lt $max_attempts ]]; do
    if ! discover_output=$(oras discover --output json --artifact-type "$artifact_type" "${IMAGE_REF}@${digest}"); then
      >&2 echo "[publish_referrers] oras discover failed (attempt $((attempts + 1))) for ${annotation_name}"
      discover_output=""
    fi

    if [[ -n "$discover_output" ]]; then
      printf '%s\n' "$discover_output" > "$tmp_json"
      if jq -e --arg digest "$attached_digest" \
        '
          [
            (.referrers // [])[]?.digest,
            (.manifests // [])[]?.digest
          ] | map(select(. == $digest)) | length > 0
        ' "$tmp_json" >/dev/null; then
        found=1
        break
      fi
    fi
    >&2 echo "[publish_referrers] Referrer ${annotation_name} not yet visible, retrying... ($((attempts + 1))/${max_attempts})"
    attempts=$((attempts + 1))
    sleep 3
  done

  if [[ $found -ne 1 ]]; then
    if [[ -s "$tmp_json" ]]; then
      >&2 echo "[publish_referrers] Latest discovery response:"
      >&2 cat "$tmp_json"
    fi
    rm -f "$tmp_json"
    >&2 echo "[publish_referrers] Failed to verify referrer ${annotation_name} (digest ${attached_digest}) of type ${artifact_type}"
    exit 1
  fi
  rm -f "$tmp_json"
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

echo "[publish_referrers] Signing referrers with cosign (OIDC)"
attest_provenance "${IMAGE_REF}@${IMAGE_DIGEST}" "$PROVENANCE"
sign_with_token "$SPDX_SBOM" "spdx" "${IMAGE_REF}@${IMAGE_DIGEST}"
sign_with_token "$CYCLO_SBOM" "cyclonedx" "${IMAGE_REF}@${IMAGE_DIGEST}"

if [[ -n "$VEX_JSON" ]]; then
  sign_with_token "$VEX_JSON" "vex" "${IMAGE_REF}@${IMAGE_DIGEST}"
fi

echo "[publish_referrers] Referrer publication completed"
