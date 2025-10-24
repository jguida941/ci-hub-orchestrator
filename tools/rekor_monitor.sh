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

if ! command -v jq >/dev/null 2>&1; then
  >&2 echo "jq not found; install via https://stedolan.github.io/jq/"
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

normalize_digest() {
  local value="${1:-}"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  value="${value#sha256:}"
  printf '%s' "$value"
}

EXPECTED_DIGEST="$(normalize_digest "$DIGEST")"

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
  REKOR_LINES=()
  while IFS= read -r line; do
    REKOR_LINES+=("$line")
  done < "$INDEX_FILE"

  for ((idx=${#REKOR_LINES[@]}-1; idx>=0; idx--)); do
    raw_line="${REKOR_LINES[idx]}"
    [[ -z "$raw_line" ]] && continue
    read -r index stored_digest <<<"$raw_line"
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
      stored_norm="$(normalize_digest "$stored_digest")"
      if [[ "$stored_norm" == "$EXPECTED_DIGEST" ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == false ]]; then
      FOUND_UUID_DIGEST=$(jq -r '
        def decode_payload($val):
          $val
          | select(type=="string")
          | @base64d
          | (try fromjson catch empty);

        def normalize:
          (toascii | ascii_downcase)
          | ltrimstr("sha256:")
          | select(test("^[0-9a-f]{64}$"));

        def gather($entry):
          [
            $entry.spec?.data?.hash?.value,
            $entry.spec?.data?.hash?.sha256,
            $entry.spec?.artifactHash?.value,
            $entry.spec?.artifactHash?.sha256,
            ($entry.spec?.subject?[]?.digest?.sha256),
            (decode_payload($entry.spec?.content?.payload?) | .subject?[]?.digest?.sha256),
            (decode_payload($entry.spec?.content?.envelope?.payload?) | .subject?[]?.digest?.sha256)
          ]
          | map(select(type=="string"))
          | map(normalize);

        def entry_digests($record):
          ($record.body
            | @base64d
            | (try fromjson catch empty))
          | if type=="array" then
              [ .[] | gather(.)[] ]
            else
              gather(.)
            end;

        (
          if type=="array" then
            [ .[] | entry_digests(.)[] ]
          else
            entry_digests(.)
          end
        )
        | map(select(. != null and . != ""))
        | .[0] // empty
      ' "$ENTRY_PATH")
      found_norm="$(normalize_digest "$FOUND_UUID_DIGEST")"
      if [[ -n "$found_norm" && "$found_norm" == "$EXPECTED_DIGEST" ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == true ]]; then
      break
    fi
    FOUND_UUID=""
  done
  unset REKOR_LINES
fi

if [[ -n "$FOUND_UUID" ]]; then
  UUID="$FOUND_UUID"
fi

if [[ -z "$UUID" ]]; then
  MAX_ATTEMPTS=${REKOR_MONITOR_MAX_ATTEMPTS:-10}
  SLEEP_SECONDS=${REKOR_MONITOR_SLEEP_SECONDS:-30}

  for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
    if [[ "$HAS_LOG_URL" -eq 1 ]]; then
      rekor-cli search --sha "$EXPECTED_DIGEST" --log-url "$REKOR_LOG" --format json > "$SEARCH_PATH"
    else
      rekor-cli --rekor_server "$REKOR_LOG" search --sha "$EXPECTED_DIGEST" --format json > "$SEARCH_PATH"
    fi

    UUID=$(jq -r '
      if type=="string" then .
      elif type=="array" then
        (.[0]
          | if type=="string" then . else (.uuid // .UUID // empty) end)
      elif type=="object" then (.uuid // .UUID // empty)
      else empty end
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
