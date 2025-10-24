#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  >&2 echo "Usage: $0 <image-digest> <subject> <output-dir>"
  exit 1
fi

DIGEST="$1"
SUBJECT="$2"
OUTPUT_DIR="$3"
mkdir -p "$OUTPUT_DIR"

REKOR_LOG=${REKOR_LOG:-https://rekor.sigstore.dev}

if ! command -v rekor-cli >/dev/null 2>&1; then
  >&2 echo "rekor-cli not found; install via https://github.com/sigstore/rekor"
  exit 1
fi

HAS_LOG_URL=1
if ! rekor-cli search --help 2>&1 | grep -q -- "--log-url"; then
  HAS_LOG_URL=0
fi

TIMESTAMP=$(date -u '+%Y%m%dT%H%M%SZ')
PROOF_PATH="$OUTPUT_DIR/rekor-proof-${TIMESTAMP}.json"
SEARCH_PATH="$OUTPUT_DIR/rekor-search-${TIMESTAMP}.json"
INDEX_FILE="$OUTPUT_DIR/rekor-indices.txt"
EXPECTED_DIGEST="${DIGEST#sha256:}"

# Copy indices from workspace if present
if [[ -f "artifacts/evidence/rekor-indices.txt" ]]; then
  mkdir -p "$OUTPUT_DIR"
  if [[ "artifacts/evidence/rekor-indices.txt" != "$INDEX_FILE" ]]; then
    cp "artifacts/evidence/rekor-indices.txt" "$INDEX_FILE"
  fi
fi

FOUND_UUID=""
UUID=""

if [[ -s "$INDEX_FILE" ]]; then
  mapfile -t REVERSED_INDICES < <(tac "$INDEX_FILE")
  for raw_line in "${REVERSED_INDICES[@]}"; do
    [[ -z "$raw_line" ]] && continue
    IFS=' ' read -r index stored_digest <<<"$raw_line"
    index="${index//[[:space:]]/}"
    stored_digest="${stored_digest//[[:space:]]/}"
    [[ -z "$index" ]] && continue
    ENTRY_PATH="$OUTPUT_DIR/rekor-entry-${index}.json"
    if [[ "$HAS_LOG_URL" -eq 1 ]]; then
      if ! rekor-cli log-entry get --log-index "$index" --log-url "$REKOR_LOG" --format json > "$ENTRY_PATH"; then
        >&2 echo "[rekor_monitor] Failed to fetch log entry $index via --log-url; retrying cache fallback"
        continue
      fi
    else
      if ! rekor-cli --rekor_server "$REKOR_LOG" log-entry get --log-index "$index" --format json > "$ENTRY_PATH"; then
        >&2 echo "[rekor_monitor] Failed to fetch log entry $index via --rekor_server; retrying cache fallback"
        continue
      fi
    fi
    echo "Stored Rekor log entry $index at $ENTRY_PATH"
    FOUND_UUID=$(jq -r 'keys[0] // empty' "$ENTRY_PATH")
    if [[ -z "$FOUND_UUID" ]]; then
      continue
    fi
    MATCHED=false
    if [[ -n "$stored_digest" ]]; then
      stored_no_prefix="${stored_digest#sha256:}"
      if [[ "$stored_digest" == "$DIGEST" || "$stored_no_prefix" == "$EXPECTED_DIGEST" ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == false ]]; then
      FOUND_UUID_DIGEST=$(jq -r '
        def records:
          if type=="array" then .[] else .[] end;
        def decode_body($record):
          $record.body | @base64d | fromjson;
        def candidate_payloads($entry):
          [
            $entry,
            $entry.spec?.data?,
            $entry.spec?.content?,
            $entry.spec?.content?.payload?,
            ($entry.spec?.content?.payload? | select(type=="string") | @base64d | fromjson),
            ($entry.spec?.content?.envelope?.payload? | select(type=="string") | @base64d | fromjson)
          ];
        def first_sha($entry):
          (candidate_payloads($entry)
            | map(
                if type=="object" then
                  if (.digest?.sha256?) then .digest.sha256
                  elif (.sha256?) then .sha256
                  elif (.value? | type=="string" and (.value | test("^[0-9a-fA-F]{64}$"))) then .value
                  else empty end
                else empty end
              )
            | map(select(.!=null and .!=""))
            | .[0]
          ) // empty;
        [
          records
          | decode_body(.)
          | [
              .spec?.data?.hash?.value,
              .spec?.data?.hash?.sha256,
              .spec?.artifactHash?.sha256,
              .spec?.artifactHash?.value,
              (.spec?.subject?[]?.digest?.sha256),
              (.spec?.content?.payload? | select(type=="string") | @base64d | fromjson | .subject[]?.digest.sha256),
              (.spec?.content?.envelope?.payload? | select(type=="string") | @base64d | fromjson | .subject[]?.digest.sha256),
              first_sha(.)
            ]
            | map(select(.!=null and .!=""))
            | .[0]
        ]
        | map(select(.!=null and .!=""))
        | .[0] // empty
      ' "$ENTRY_PATH" | head -n1)
      digest_no_prefix="${FOUND_UUID_DIGEST#sha256:}"
      if [[ -n "$FOUND_UUID_DIGEST" && ( "$FOUND_UUID_DIGEST" == "$DIGEST" || "$digest_no_prefix" == "$EXPECTED_DIGEST" ) ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == true ]]; then
      break
    fi
    FOUND_UUID=""
  done
  unset REVERSED_INDICES
fi

if [[ -n "$FOUND_UUID" ]]; then
  UUID="$FOUND_UUID"
fi

if [[ -z "$UUID" ]]; then
  MAX_ATTEMPTS=${REKOR_MONITOR_MAX_ATTEMPTS:-10}
  SLEEP_SECONDS=${REKOR_MONITOR_SLEEP_SECONDS:-30}

  for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
    if [[ "$HAS_LOG_URL" -eq 1 ]]; then
      rekor-cli search --sha "$DIGEST" --log-url "$REKOR_LOG" --format json > "$SEARCH_PATH"
    else
      rekor-cli --rekor_server "$REKOR_LOG" search --sha "$DIGEST" --format json > "$SEARCH_PATH"
    fi

    UUID=$(jq -r '
      if type == "array" then
        (.[0].uuid // empty)
      elif type == "object" then
        (.uuid // empty)
      else
        empty
      end
    ' "$SEARCH_PATH")

    if [[ -n "$UUID" ]]; then
      break
    fi

    if (( attempt < MAX_ATTEMPTS )); then
      >&2 echo "[rekor_monitor] No Rekor entries found for digest $DIGEST (attempt ${attempt}/${MAX_ATTEMPTS}); retrying in ${SLEEP_SECONDS}s"
      sleep "$SLEEP_SECONDS"
    fi
  done

  if [[ -z "$UUID" ]]; then
    >&2 echo "[rekor_monitor] No Rekor entries found for digest $DIGEST after ${MAX_ATTEMPTS} attempts"
    exit 1
  fi
fi

if [[ "$HAS_LOG_URL" -eq 1 ]]; then
  rekor-cli verify --uuid "$UUID" --log-url "$REKOR_LOG" --format json > "$PROOF_PATH"
else
  rekor-cli --rekor_server "$REKOR_LOG" verify --uuid "$UUID" --format json > "$PROOF_PATH"
fi

echo "Stored Rekor inclusion proof at $PROOF_PATH"

jq -n \
  --arg subject "$SUBJECT" \
  --arg digest "$DIGEST" \
  --arg proof_path "$PROOF_PATH" \
  --arg timestamp "$TIMESTAMP" \
  '{"subject":$subject,"digest":$digest,"proof_path":$proof_path,"timestamp":$timestamp}' \
  > "$OUTPUT_DIR/rekor-proof-index-${TIMESTAMP}.json"
