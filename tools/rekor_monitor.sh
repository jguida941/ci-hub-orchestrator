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

ensure_rekor_cli() {
  if command -v rekor-cli >/dev/null 2>&1; then
    return 0
  fi
  local version="${REKOR_CLI_VERSION:-v1.3.1}"
  local os
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64 | amd64) arch="amd64" ;;
    arm64 | aarch64) arch="arm64" ;;
    *) arch="amd64" ;;
  esac
  local filename="rekor-cli-${os}-${arch}"
  local url="https://github.com/sigstore/rekor/releases/download/${version}/${filename}"
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/rekor-monitor"
  local dest="${cache_dir}/rekor-cli-${version}-${os}-${arch}"
  mkdir -p "$cache_dir"
  if [[ ! -x "$dest" ]]; then
    >&2 echo "[rekor_monitor] rekor-cli not found; downloading ${url}"
    if ! curl -fsSL "$url" -o "$dest"; then
      >&2 echo "[rekor_monitor] Failed to download rekor-cli from ${url}"
      rm -f "$dest"
      return 1
    fi
    chmod +x "$dest"
  fi
  ln -sf "$dest" "${cache_dir}/rekor-cli"
  PATH="${cache_dir}:$PATH"
  export PATH
  if command -v rekor-cli >/dev/null 2>&1; then
    return 0
  fi
  >&2 echo "[rekor_monitor] Unable to initialize rekor-cli binary"
  return 1
}

if ! ensure_rekor_cli; then
  >&2 echo "rekor-cli not available; install via https://github.com/sigstore/rekor"
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  >&2 echo "jq not found; install via https://stedolan.github.io/jq/"
  exit 1
fi

HAS_LOG_URL=1
if ! rekor-cli search --help 2>&1 | grep -q -- "--log-url"; then
  HAS_LOG_URL=0
fi

LOG_ENTRY_CMD=()
if rekor-cli log-entry --help >/dev/null 2>&1; then
  LOG_ENTRY_CMD=(log-entry get)
elif rekor-cli logentry --help >/dev/null 2>&1; then
  LOG_ENTRY_CMD=(logentry get)
elif rekor-cli get --help >/dev/null 2>&1; then
  LOG_ENTRY_CMD=(get)
else
  >&2 echo "rekor-cli missing log-entry/logentry/get commands; please update rekor-cli"
  exit 1
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

is_valid_uuid() {
  local candidate="${1:-}"
  if [[ "$candidate" =~ ^[[:xdigit:]]{64}$ || "$candidate" =~ ^[[:xdigit:]]{80}$ ]]; then
    return 0
  fi
  return 1
}

rekor_log_entry_get() {
  local selector="$1"
  local value="$2"
  local dest="$3"
  local -a cmd=(rekor-cli)
  if [[ "$HAS_LOG_URL" -eq 1 ]]; then
    cmd+=(--log-url "$REKOR_LOG")
  else
    cmd+=(--rekor_server "$REKOR_LOG")
  fi
  cmd+=("${LOG_ENTRY_CMD[@]}")
  cmd+=("$selector" "$value" --format json)
  if ! "${cmd[@]}" > "$dest"; then
    rm -f "$dest"
    return 1
  fi
  return 0
}

REKOR_JQ_HELPERS=$(cat <<'JQ'
def is_uuid:
  (type == "string") and ((test("^[0-9a-fA-F]{64}$")) or (test("^[0-9a-fA-F]{80}$")));
def decode_json:
  if (type == "string") and (test("^\\s*[\\[{]")) then
    (try (fromjson | decode_json) catch .)
  else
    .
  end;
def entry_items:
  def gather($value):
    ($value | decode_json) as $decoded
    | if $decoded == null then []
      elif ($decoded | type) == "object" then
        ([$decoded | keys_unsorted[] | select(is_uuid)]) as $uuid_keys
        | if ($uuid_keys | length) > 0 then
            [ $uuid_keys[] | { key: ., value: $decoded[.] } ]
          else
            [ { key: null, value: $decoded } ]
          end
      elif ($decoded | type) == "array" then
        [ $decoded[] | gather(.)[] ]
      else
        []
      end;
  gather(.);
def pick_uuid($entry):
  if ($entry | type) != "object" then empty
  else
    [
      $entry.uuid,
      $entry.UUID,
      $entry.uuids?[0],
      $entry.UUIDs?[0],
      $entry.results?[0],
      ($entry.logEntry | select(type=="object") | .uuid),
      ($entry.attestation | select(type=="object") | .uuid)
    ]
    | map(select(is_uuid))
    | .[0]
  end;
def take_uuid($value; $allow_raw):
  if $value == null then empty
  elif $value | type == "string" then
    if $allow_raw and ($value | is_uuid) then $value else empty end
  elif $value | type == "object" then
    (
      pick_uuid($value)
    )
    // (
      [ $value[]? | take_uuid(.; false) ]
      | map(select(. != ""))
      | .[0]
    )
  elif $value | type == "array" then
    [ $value[]? | take_uuid(.; $allow_raw) ]
    | map(select(. != ""))
    | .[0]
  else
    empty
  end;
def pick_log_index($entry):
  [
    $entry.logIndex,
    $entry.LogIndex,
    $entry.logEntry?.logIndex,
    $entry.verification?.inclusionProof?.logIndex
  ]
  | map(select(. != null))
  | .[0];
def cached_entry_log_index:
  (entry_items | .[0]?.value) as $entry
  | (pick_log_index($entry) // empty);
JQ
)

REKOR_SEARCH_SUMMARY_JQ=$(cat <<'JQ'
def pick_log_id($entry):
  [
    $entry.logID,
    $entry.logId,
    $entry.logEntry?.logID
  ]
  | map(select(type=="string" and length > 0))
  | .[0];

def pick_integrated_time($entry):
  [
    $entry.integratedTime,
    $entry.logEntry?.integratedTime,
    $entry.verification?.inclusionProof?.integratedTime
  ]
  | map(select(. != null))
  | .[0];

def pick_inclusion_state($entry):
  if $entry.verification?.inclusionProof or $entry.inclusionProof then "proof" else "none" end;

def summarize($item):
  ($item.value // {}) as $entry
  | {
      uuid: (pick_uuid($entry) // ($item.key // "unknown")),
      log_index: (pick_log_index($entry) // "unknown"),
      log_id: (pick_log_id($entry) // "unknown"),
      integrated_time: (pick_integrated_time($entry) // "unknown"),
      inclusion: pick_inclusion_state($entry)
    }
  | "[rekor_monitor] entry uuid=\(.uuid) logIndex=\(.log_index) logID=\(.log_id) integrated=\(.integrated_time) inclusion=\(.inclusion)";

(entry_items) as $items
| if ($items | length) == 0 then
    "[rekor_monitor] Search returned 0 entries"
  else
    (
      "[rekor_monitor] Search returned " + (($items | length) | tostring) + " entries",
      ($items[] | summarize(.))
    )
  end
JQ
)

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
MATCHED_INDEX=""

if [[ -s "$INDEX_FILE" ]]; then
  if command -v mapfile >/dev/null 2>&1; then
    mapfile -t REKOR_LINES < "$INDEX_FILE"
  else
    REKOR_LINES=()
    while IFS= read -r line; do
      REKOR_LINES+=("$line")
    done < "$INDEX_FILE"
  fi

  for ((idx=${#REKOR_LINES[@]}-1; idx>=0; idx--)); do
    raw_line="${REKOR_LINES[idx]}"
    raw_line="${raw_line%%#*}"
    [[ -z "$raw_line" ]] && continue
    set -- $raw_line
    index="${1:-}"
    stored_digest="${2:-}"
    index="${index//[[:space:]]/}"
    stored_digest="${stored_digest//[[:space:]]/}"
    [[ -z "$index" ]] && continue
    ENTRY_PATH="$OUTPUT_DIR/rekor-entry-${index}.json"
    if ! rekor_log_entry_get --log-index "$index" "$ENTRY_PATH"; then
      if [[ "$HAS_LOG_URL" -eq 1 ]]; then
        >&2 echo "[rekor_monitor] Failed to fetch log entry $index via --log-url; skipping cached index"
      else
        >&2 echo "[rekor_monitor] Failed to fetch log entry $index via --rekor_server; skipping cached index"
      fi
      continue
    fi
    echo "Stored Rekor log entry $index at $ENTRY_PATH"
    candidate_uuid=$(jq -r "${REKOR_JQ_HELPERS}"'
      (entry_items | .[0]?) as $item
      | if $item == null then empty
        else (
          [
            ($item.key // ""),
            (pick_uuid($item.value) // "")
          ]
          | map(select(is_uuid))
          | .[0]
        )
        end
      // empty
    ' "$ENTRY_PATH")
    if [[ -n "$candidate_uuid" ]] && ! is_valid_uuid "$candidate_uuid"; then
      candidate_uuid=""
    fi
    MATCHED=false
    if [[ -n "$stored_digest" ]]; then
      stored_norm="$(normalize_digest "$stored_digest")"
      if [[ "$stored_norm" == "$EXPECTED_DIGEST" ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == false ]]; then
      FOUND_UUID_DIGEST=$(jq -r "${REKOR_JQ_HELPERS}"'
        def decode_payload($v):
          $v | select(type=="string") | @base64d | (try fromjson catch empty);

        def normalize:
          ascii_downcase
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
          | map(normalize)
          | map(select(. != ""));

        (entry_items | .[0]?.value) as $entry
        | if $entry == null then empty
          else
            (
              [
                $entry.body,
                ($entry.logEntry | select(type=="object") | .body)
              ]
              | map(select(type=="string"))
              | .[0]
            ) as $raw_body
            | if $raw_body == null then empty
              else
                ($raw_body | @base64d | (try fromjson catch empty)) as $decoded
                | if $decoded == null then empty
                  else (
                    (if $decoded | type == "array" then [$decoded[]] else [$decoded] end)
                    | reduce .[] as $item ([]; . + gather($item))
                    | (.[0] // empty)
                  )
                end
            end
        end
      ' "$ENTRY_PATH")
      found_norm="$(normalize_digest "$FOUND_UUID_DIGEST")"
      if [[ -n "$found_norm" && "$found_norm" == "$EXPECTED_DIGEST" ]]; then
        MATCHED=true
      fi
    fi
    if [[ "$MATCHED" == true ]]; then
      FOUND_UUID="$candidate_uuid"
      MATCHED_INDEX="$index"
      break
    fi
    FOUND_UUID=""
  done
  unset REKOR_LINES
fi

if [[ -n "$FOUND_UUID" ]]; then
  if is_valid_uuid "$FOUND_UUID"; then
    UUID="$FOUND_UUID"
  else
    >&2 echo "[rekor_monitor] Cached entry for index ${MATCHED_INDEX:-?} returned invalid UUID '$FOUND_UUID'; falling back to search"
    UUID=""
  fi
fi

if [[ -z "$UUID" ]]; then
  MAX_ATTEMPTS=${REKOR_MONITOR_MAX_ATTEMPTS:-10}
  SLEEP_SECONDS=${REKOR_MONITOR_SLEEP_SECONDS:-30}

  >&2 echo "[rekor_monitor] MAX_ATTEMPTS: ${MAX_ATTEMPTS}"
  >&2 echo "[rekor_monitor] SLEEP_SECONDS: ${SLEEP_SECONDS}" 

  for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
    >&2 echo "[rekor_monitor] Attempt ${attempt}/${MAX_ATTEMPTS}: Searching for digest ${EXPECTED_DIGEST}" 
    if [[ "$HAS_LOG_URL" -eq 1 ]]; then
      rekor-cli search --sha "$EXPECTED_DIGEST" --log-url "$REKOR_LOG" --format json > "$SEARCH_PATH" || true
    else
      rekor-cli --rekor_server "$REKOR_LOG" search --sha "$EXPECTED_DIGEST" --format json > "$SEARCH_PATH" || true
    fi
    if [[ "${REKOR_MONITOR_DEBUG:-0}" == "1" ]]; then
      >&2 echo "[rekor_monitor] Search command finished; raw response saved to ${SEARCH_PATH}"
      >&2 cat "${SEARCH_PATH}"
    else
      if ! jq -r "${REKOR_JQ_HELPERS}
${REKOR_SEARCH_SUMMARY_JQ}
" "$SEARCH_PATH" >&2; then
        >&2 echo "[rekor_monitor] Search complete; unable to summarize response (see ${SEARCH_PATH})"
      fi
    fi

    UUID=$(jq -r "${REKOR_JQ_HELPERS}"'
      (take_uuid(.; true) // empty)
    ' "$SEARCH_PATH")
    >&2 echo "[rekor_monitor] Parsed UUID: ${UUID}" 
    if [[ -n "$UUID" ]] && ! is_valid_uuid "$UUID"; then
      UUID=""
    fi

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

if [[ -n "$UUID" ]]; then
  if ! is_valid_uuid "$UUID"; then
    >&2 echo "[rekor_monitor] Ignoring invalid UUID value '$UUID'; using log index fallback"
    UUID=""
  fi
fi

if [[ -n "$UUID" ]]; then
  if [[ "$HAS_LOG_URL" -eq 1 ]]; then
    rekor-cli verify --uuid "$UUID" --log-url "$REKOR_LOG" --format json > "$PROOF_PATH"
  else
    rekor-cli --rekor_server "$REKOR_LOG" verify --uuid "$UUID" --format json > "$PROOF_PATH"
  fi
elif [[ -n "$MATCHED_INDEX" ]]; then
  if [[ "$HAS_LOG_URL" -eq 1 ]]; then
    rekor-cli verify --log-index "$MATCHED_INDEX" --log-url "$REKOR_LOG" --format json > "$PROOF_PATH"
  else
    rekor-cli --rekor_server "$REKOR_LOG" verify --log-index "$MATCHED_INDEX" --format json > "$PROOF_PATH"
  fi
else
  >&2 echo "[rekor_monitor] Unable to determine Rekor UUID or log index for digest $DIGEST"
  exit 1
fi

if [[ -n "$INDEX_FILE" ]]; then
  tmp_entry=$(mktemp)
  fetch_ok=0
  if [[ -n "$UUID" ]] && rekor_log_entry_get --uuid "$UUID" "$tmp_entry"; then
    fetch_ok=1
  elif [[ -n "$MATCHED_INDEX" ]] && rekor_log_entry_get --log-index "$MATCHED_INDEX" "$tmp_entry"; then
    fetch_ok=1
  fi
  if [[ $fetch_ok -eq 1 ]]; then
    log_index=$(jq -r "${REKOR_JQ_HELPERS}"'
      (cached_entry_log_index // empty)
    ' "$tmp_entry")
    if [[ -n "$log_index" ]]; then
      mkdir -p "$(dirname "$INDEX_FILE")"
      if ! { [[ -f "$INDEX_FILE" ]] && grep -q "^${log_index} " "$INDEX_FILE"; }; then
        printf '%s %s\n' "$log_index" "$DIGEST" >> "$INDEX_FILE"
      fi
    fi
  fi
  rm -f "$tmp_entry"
fi

echo "Stored Rekor inclusion proof at $PROOF_PATH"

jq -n \
  --arg subject "$SUBJECT" \
  --arg digest "$DIGEST" \
  --arg proof_path "$PROOF_PATH" \
  --arg timestamp "$TIMESTAMP" \
  '{"subject":$subject,"digest":$digest,"proof_path":$proof_path,"timestamp":$timestamp}' \
  > "$OUTPUT_DIR/rekor-proof-index-${TIMESTAMP}.json"
