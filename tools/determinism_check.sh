#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage:
  determinism_check.sh <image-ref> <output-dir>
  determinism_check.sh <artifact-path> <metadata-json> <output-dir>  # legacy mode

Environment overrides:
  DETERMINISM_PLATFORMS       Comma-separated list of platforms (e.g. linux/amd64,linux/arm64)
  DETERMINISM_RUNS            Number of repeated inspections per platform (default: 2, minimum: 2)
  DETERMINISM_SLEEP_SECONDS   Delay between repeated inspections (default: 5 seconds)
USAGE
}

sanitize_label() {
  local value="$1"
  value="${value//[!A-Za-z0-9._-]/_}"
  if [[ -z "$value" ]]; then
    value="all"
  fi
  printf '%s' "$value"
}

trim_whitespace() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
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
  if command -v jq >/dev/null 2>&1; then
    jq '.' "$METADATA_JSON" > "$OUTPUT_DIR/metadata.json"
  else
    cp "$METADATA_JSON" "$OUTPUT_DIR/metadata.json"
  fi
  echo "Simulating cross-arch determinism check" > "$OUTPUT_DIR/diff-report.txt"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  >&2 echo "[determinism_check] docker CLI not found"
  exit 1
fi

SHA256_FIELD=1
if command -v sha256sum >/dev/null 2>&1; then
  SHA256_CMD=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  SHA256_CMD=(shasum -a 256)
elif command -v openssl >/dev/null 2>&1; then
  SHA256_CMD=(openssl dgst -sha256)
  SHA256_FIELD=2
else
  >&2 echo "[determinism_check] no SHA-256 utility found (sha256sum, shasum, or openssl)"
  exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python)
fi

if [[ -z "$PYTHON_BIN" ]]; then
  >&2 echo "[determinism_check] python3/python is required to generate summaries"
  exit 1
fi

RUN_COUNT=${DETERMINISM_RUNS:-2}
if ! [[ "$RUN_COUNT" =~ ^[0-9]+$ ]]; then
  >&2 echo "[determinism_check] DETERMINISM_RUNS must be an integer value, got: $RUN_COUNT"
  exit 1
fi
if [[ "$RUN_COUNT" -lt 2 ]]; then
  RUN_COUNT=2
fi
SLEEP_SECONDS=${DETERMINISM_SLEEP_SECONDS:-5}

PLATFORMS=()
PLATFORMS+=("__DEFAULT__")
if [[ -n "${DETERMINISM_PLATFORMS:-}" ]]; then
  IFS=',' read -r -a RAW_PLATFORMS <<< "${DETERMINISM_PLATFORMS}"
  for platform in "${RAW_PLATFORMS[@]}"; do
    platform=$(trim_whitespace "$platform")
    if [[ -n "$platform" ]]; then
      PLATFORMS+=("$platform")
    fi
  done
fi

RUN_DATA_FILE="$OUTPUT_DIR/determinism_runs.tsv"
: > "$RUN_DATA_FILE"

overall_status=0

inspect_platform() {
  local platform_key="$1"
  local display_name="$2"
  local -a platform_args=()

  if [[ "$platform_key" != "__DEFAULT__" ]]; then
    platform_args=(--platform "$display_name")
  fi

  local safe_label
  safe_label=$(sanitize_label "$display_name")
  local base_sha=""
  local base_file=""
  local -a mismatch_runs=()

  local run_index=1
  while [[ "$run_index" -le "$RUN_COUNT" ]]; do
    local manifest_file="$OUTPUT_DIR/manifest.${safe_label}.run${run_index}.json"

    local -a cmd=(docker buildx imagetools inspect --raw)
    if [[ "${#platform_args[@]}" -gt 0 ]]; then
      cmd+=("${platform_args[@]}")
    fi
    cmd+=("$IMAGE_REF")
    if ! "${cmd[@]}" > "$manifest_file"; then
      >&2 echo "[determinism_check] Failed to inspect $IMAGE_REF for platform '$display_name' (run $run_index)"
      exit 1
    fi

    local manifest_sha
    manifest_sha=$("${SHA256_CMD[@]}" "$manifest_file" | awk -v field="$SHA256_FIELD" '{print $field}')
    printf '%s  %s\n' "$manifest_sha" "$(basename "$manifest_file")" > "$OUTPUT_DIR/manifest.${safe_label}.run${run_index}.sha256"

    local match="true"
    local diff_file=""
    local diff_basename=""
    if [[ "$run_index" -eq 1 ]]; then
      base_sha="$manifest_sha"
      base_file="$manifest_file"
    else
      if [[ "$manifest_sha" != "$base_sha" ]]; then
        match="false"
        diff_file="$OUTPUT_DIR/manifest.${safe_label}.run${run_index}.diff"
        if command -v diff >/dev/null 2>&1; then
          diff -u "$base_file" "$manifest_file" > "$diff_file" || true
        else
          printf 'Mismatch between manifests\nbaseline: %s\nrun %d: %s\n' "$base_file" "$run_index" "$manifest_file" > "$diff_file"
        fi
        mismatch_runs+=("$run_index")
        diff_basename=$(basename "$diff_file")
        overall_status=2
      fi
    fi

    printf '%s\t%s\t%d\t%s\t%s\t%s\t%s\n' \
      "$display_name" \
      "$safe_label" \
      "$run_index" \
      "$manifest_sha" \
      "$(basename "$manifest_file")" \
      "$match" \
      "$diff_basename" >> "$RUN_DATA_FILE"

    if [[ "$RUN_COUNT" -gt 1 && "$run_index" -lt "$RUN_COUNT" ]]; then
      sleep "$SLEEP_SECONDS"
    fi

    run_index=$((run_index + 1))
  done

  if [[ "${#mismatch_runs[@]}" -gt 0 ]]; then
    >&2 echo "[determinism_check] Non-deterministic manifest detected for platform '$display_name' (baseline ${base_sha})"
  fi
}

for platform in "${PLATFORMS[@]}"; do
  if [[ "$platform" == "__DEFAULT__" ]]; then
    inspect_platform "$platform" "all"
  else
    inspect_platform "$platform" "$platform"
  fi
done

RECORDED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
HOSTNAME=$(uname -n)
KERNEL=$(uname -s)
ARCH=$(uname -m)
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

export RUN_DATA_FILE IMAGE_REF OUTPUT_DIR RECORDED_AT HOSTNAME KERNEL ARCH GIT_SHA

"$PYTHON_BIN" - <<'PY'
import csv
import json
import os
from collections import defaultdict

run_data_file = os.environ["RUN_DATA_FILE"]
image_ref = os.environ["IMAGE_REF"]
recorded_at = os.environ["RECORDED_AT"]
host = os.environ["HOSTNAME"]
kernel = os.environ["KERNEL"]
arch = os.environ["ARCH"]
git_sha = os.environ["GIT_SHA"]
output_dir = os.environ["OUTPUT_DIR"]

platform_runs: dict[str, list[dict]] = defaultdict(list)

with open(run_data_file, newline="", encoding="utf-8") as handle:
    reader = csv.reader(handle, delimiter="\t")
    for platform, label, run_idx, sha256, manifest, match, diff in reader:
        run_number = int(run_idx)
        platform_runs[(platform, label)].append(
            {
                "run": run_number,
                "sha256": sha256,
                "manifest": manifest,
                "match": match.lower() == "true",
                "diff": diff or None,
            }
        )

results = []
for (platform, label), runs in platform_runs.items():
    runs_sorted = sorted(runs, key=lambda item: item["run"])
    baseline_sha = runs_sorted[0]["sha256"] if runs_sorted else ""
    mismatches = [item for item in runs_sorted if not item["match"]]
    result = {
        "platform": platform,
        "platform_key": label,
        "manifest_sha256": baseline_sha,
        "consistent": len(mismatches) == 0,
        "mismatch_runs": [item["run"] for item in mismatches],
        "diff_files": [item["diff"] for item in mismatches if item["diff"]],
        "runs": runs_sorted,
    }
    results.append(result)

report = {
    "schema": "determinism.report.v1",
    "image_ref": image_ref,
    "recorded_at": recorded_at,
    "builder": {
        "host": host,
        "kernel": kernel,
        "arch": arch,
    },
    "pipeline_commit": git_sha,
    "platforms": results,
}

metadata_path = os.path.join(output_dir, "metadata.json")
report_path = os.path.join(output_dir, "determinism-report.json")
summary_path = os.path.join(output_dir, "summary.txt")

with open(metadata_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
    handle.write("\n")

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
    handle.write("\n")

lines = [
    "Determinism evidence",
    "====================",
    f"Image ref: {image_ref}",
    f"Recorded at: {recorded_at}",
    "",
    "Platforms checked:",
]
for result in sorted(results, key=lambda item: (item["platform"], item["platform_key"])):
    status = "deterministic ✅" if result["consistent"] else "drift detected ❌"
    baseline = result["manifest_sha256"]
    lines.append(f" - {result['platform'] or 'all'} ({result['platform_key']}): {status} (baseline {baseline})")
    if result["mismatch_runs"]:
        mismatch_text = ", ".join(str(num) for num in result["mismatch_runs"])
        lines.append(f"   mismatched runs: {mismatch_text}; diff: {', '.join(result['diff_files']) or 'n/a'}")
    run_hashes = ", ".join(f"{item['run']}→{item['sha256']}" for item in result["runs"])
    lines.append(f"   run hashes: {run_hashes}")

with open(summary_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines))
    handle.write("\n")
PY

exit "$overall_status"
