#!/usr/bin/env bash
# Cross-time determinism validation
# Implements 24-hour delayed rebuild to verify reproducibility
#
# This validates that builds are deterministic across:
# - Time (24+ hours apart)
# - Environment (different runners)
# - Dependencies (pinned versions)
#
# REQUIREMENTS:
# - SOURCE_DATE_EPOCH environment variable
# - Deterministic build toolchain
# - Pinned dependencies

set -euo pipefail

MODE="${1:-validate}"  # validate|schedule|compare
ORIGINAL_BUILD="${2:-}"
DELAY_HOURS="${3:-24}"
EVIDENCE_DIR="${4:-artifacts/determinism}"

mkdir -p "$EVIDENCE_DIR"

log() {
  echo "[determinism] $*" >&2
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "${EVIDENCE_DIR}/determinism.log"
}

# Schedule a delayed rebuild
schedule_delayed_rebuild() {
  local original_ref="$1"
  local schedule_file="${EVIDENCE_DIR}/scheduled-rebuild.json"

  local rebuild_time=$(date -u -d "+${DELAY_HOURS} hours" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
                       date -u -v+${DELAY_HOURS}H +%Y-%m-%dT%H:%M:%SZ)

  cat > "$schedule_file" <<EOF
{
  "original_ref": "${original_ref}",
  "original_build_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scheduled_rebuild_time": "${rebuild_time}",
  "delay_hours": ${DELAY_HOURS},
  "source_date_epoch": "${SOURCE_DATE_EPOCH:-}",
  "workflow": "${GITHUB_WORKFLOW:-unknown}",
  "run_id": "${GITHUB_RUN_ID:-unknown}"
}
EOF

  log "Scheduled rebuild for: $rebuild_time"
  log "Schedule saved to: $schedule_file"

  # Create GitHub Actions workflow dispatch event (if in CI)
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    local workflow_file=".github/workflows/cross-time-determinism.yml"

    # Verify workflow exists
    if [[ ! -f "$workflow_file" ]]; then
      log "ERROR: Cross-time determinism workflow not found at $workflow_file"
      exit 1
    fi

    # Schedule via GitHub API
    curl -X POST \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/cross-time-determinism.yml/dispatches" \
      -d "{
        \"ref\": \"${GITHUB_REF}\",
        \"inputs\": {
          \"original_ref\": \"${original_ref}\",
          \"original_run_id\": \"${GITHUB_RUN_ID}\",
          \"delay_hours\": \"${DELAY_HOURS}\"
        }
      }"

    log "Workflow dispatch created for delayed validation"

    # Save dispatch metadata for verification
    mkdir -p artifacts
    echo "{\"run_id\": \"${GITHUB_RUN_ID}\", \"scheduled_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"delay_hours\": \"${DELAY_HOURS}\"}" > artifacts/determinism-schedule.json
  fi
}

# Create validation workflow if it doesn't exist - DEPRECATED
create_validation_workflow() {
  # This function is deprecated - workflow already exists at .github/workflows/cross-time-determinism.yml
  log "ERROR: create_validation_workflow should not be called - workflow already exists"
  exit 1
}

# Compare two builds for determinism
compare_builds() {
  local original_dir="$1"
  local rebuilt_dir="${2:-build/}"
  local report_file="${EVIDENCE_DIR}/determinism-report.json"

  log "Comparing builds for determinism..."
  log "Original: $original_dir"
  log "Rebuilt: $rebuilt_dir"

  local passed=0
  local failed=0
  local differences=""

  # Compare each artifact
  find "$original_dir" -type f -name "*.tar.gz" -o -name "*.whl" -o -name "*.jar" | while read -r orig_file; do
    local rel_path="${orig_file#$original_dir/}"
    local new_file="${rebuilt_dir}/${rel_path}"

    if [[ ! -f "$new_file" ]]; then
      log "✗ Missing in rebuild: $rel_path"
      ((failed++))
      differences="${differences}\nMissing: ${rel_path}"
      continue
    fi

    # Compare SHA256 hashes
    local orig_hash=$(sha256sum "$orig_file" | cut -d' ' -f1)
    local new_hash=$(sha256sum "$new_file" | cut -d' ' -f1)

    if [[ "$orig_hash" == "$new_hash" ]]; then
      log "✓ Deterministic: $rel_path"
      ((passed++))
    else
      log "✗ Non-deterministic: $rel_path"
      log "  Original: $orig_hash"
      log "  Rebuilt:  $new_hash"
      ((failed++))

      # Perform detailed diff
      local diff_file="${EVIDENCE_DIR}/diff-${rel_path//\//-}.txt"
      mkdir -p "$(dirname "$diff_file")"

      # Extract and compare for archives
      if [[ "$rel_path" == *.tar.gz ]]; then
        local orig_extract="/tmp/orig-$$"
        local new_extract="/tmp/new-$$"
        mkdir -p "$orig_extract" "$new_extract"

        tar xzf "$orig_file" -C "$orig_extract" 2>/dev/null || true
        tar xzf "$new_file" -C "$new_extract" 2>/dev/null || true

        diff -r "$orig_extract" "$new_extract" > "$diff_file" 2>&1 || true

        rm -rf "$orig_extract" "$new_extract"
      else
        diff "$orig_file" "$new_file" > "$diff_file" 2>&1 || true
      fi

      differences="${differences}\nDifferent: ${rel_path} (see ${diff_file})"
    fi
  done

  # Check for extra files in rebuild
  find "$rebuilt_dir" -type f -name "*.tar.gz" -o -name "*.whl" -o -name "*.jar" | while read -r new_file; do
    local rel_path="${new_file#$rebuilt_dir/}"
    local orig_file="${original_dir}/${rel_path}"

    if [[ ! -f "$orig_file" ]]; then
      log "✗ Extra in rebuild: $rel_path"
      ((failed++))
      differences="${differences}\nExtra: ${rel_path}"
    fi
  done

  # Generate report
  local status="fail"
  [[ $failed -eq 0 ]] && status="pass"

  cat > "$report_file" <<EOF
{
  "validation_type": "cross-time-determinism",
  "delay_hours": ${DELAY_HOURS},
  "status": "${status}",
  "passed": ${passed},
  "failed": ${failed},
  "total": $((passed + failed)),
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_date_epoch": "${SOURCE_DATE_EPOCH:-not_set}",
  "original_build": {
    "ref": "${GITHUB_REF:-unknown}",
    "run_id": "${GITHUB_RUN_ID:-unknown}",
    "sha": "${GITHUB_SHA:-unknown}"
  },
  "environment": {
    "TZ": "${TZ:-}",
    "LC_ALL": "${LC_ALL:-}",
    "LANG": "${LANG:-}"
  },
  "differences": "$(echo -e "$differences" | jq -R -s '.')"
}
EOF

  log "Report generated: $report_file"

  # Fail if non-deterministic
  if [[ $failed -gt 0 ]]; then
    log "ERROR: Build is non-deterministic!"
    log "Failed artifacts: $failed"
    log "See report: $report_file"
    exit 1
  else
    log "SUCCESS: Build is deterministic!"
    log "All $passed artifacts matched"
  fi
}

# Validate current build for determinism readiness
validate_determinism_readiness() {
  local checks_passed=0
  local checks_failed=0
  local readiness_file="${EVIDENCE_DIR}/determinism-readiness.json"

  log "Validating determinism readiness..."

  # Check SOURCE_DATE_EPOCH
  if [[ -n "${SOURCE_DATE_EPOCH:-}" ]]; then
    log "✓ SOURCE_DATE_EPOCH is set: $SOURCE_DATE_EPOCH"
    ((checks_passed++))
  else
    log "✗ SOURCE_DATE_EPOCH is not set"
    ((checks_failed++))
  fi

  # Check timezone
  if [[ "${TZ:-}" == "UTC" ]]; then
    log "✓ TZ is set to UTC"
    ((checks_passed++))
  else
    log "✗ TZ is not set to UTC (current: ${TZ:-not_set})"
    ((checks_failed++))
  fi

  # Check locale
  if [[ "${LC_ALL:-}" == "C" ]]; then
    log "✓ LC_ALL is set to C"
    ((checks_passed++))
  else
    log "✗ LC_ALL is not set to C (current: ${LC_ALL:-not_set})"
    ((checks_failed++))
  fi

  # Check for unpinned dependencies
  if [[ -f "requirements.txt" ]]; then
    if grep -qE '(>=|>|<|<=|~=|\*)' requirements.txt; then
      log "✗ Unpinned dependencies found in requirements.txt"
      ((checks_failed++))
    else
      log "✓ All Python dependencies are pinned"
      ((checks_passed++))
    fi
  fi

  if [[ -f "package-lock.json" ]]; then
    log "✓ package-lock.json exists (NPM dependencies locked)"
    ((checks_passed++))
  elif [[ -f "package.json" ]]; then
    log "✗ package.json exists but no package-lock.json"
    ((checks_failed++))
  fi

  # Generate readiness report
  cat > "$readiness_file" <<EOF
{
  "ready": $([ $checks_failed -eq 0 ] && echo "true" || echo "false"),
  "checks_passed": ${checks_passed},
  "checks_failed": ${checks_failed},
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": {
    "SOURCE_DATE_EPOCH": "${SOURCE_DATE_EPOCH:-not_set}",
    "TZ": "${TZ:-not_set}",
    "LC_ALL": "${LC_ALL:-not_set}",
    "LANG": "${LANG:-not_set}"
  }
}
EOF

  log "Readiness report: $readiness_file"

  if [[ $checks_failed -gt 0 ]]; then
    log "WARNING: Not ready for deterministic builds"
    log "Failed checks: $checks_failed"
    return 1
  else
    log "Ready for deterministic builds"
    return 0
  fi
}

# Main execution
case "$MODE" in
  validate)
    validate_determinism_readiness
    ;;

  schedule)
    if [[ -z "$ORIGINAL_BUILD" ]]; then
      log "ERROR: Original build reference required for scheduling"
      exit 1
    fi
    schedule_delayed_rebuild "$ORIGINAL_BUILD"
    ;;

  compare)
    if [[ -z "$ORIGINAL_BUILD" ]]; then
      log "ERROR: Original build directory required for comparison"
      exit 1
    fi
    compare_builds "$ORIGINAL_BUILD"
    ;;

  *)
    log "ERROR: Invalid mode: $MODE"
    log "Usage: $0 {validate|schedule|compare} [original_build] [delay_hours] [evidence_dir]"
    exit 1
    ;;
esac

log "Determinism validation complete"