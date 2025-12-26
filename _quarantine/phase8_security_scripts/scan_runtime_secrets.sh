#!/usr/bin/env bash
# Scan live job environment and processes for leaked secrets
# Enforces secretless runtime posture per STATUS.md:31,84

set -euo pipefail

FINDINGS=0
REPORT_FILE="${1:-artifacts/security/runtime-secrets.json}"

mkdir -p "$(dirname "$REPORT_FILE")"

log() {
  echo "[runtime-secrets] $*" >&2
}

# High-risk patterns that should never appear in environment variables
HIGH_RISK_PATTERNS=(
  "BEGIN.*PRIVATE KEY"
  "AWS_SECRET_ACCESS_KEY"
  "GITHUB_TOKEN"
  "GH_TOKEN"
  "ANTHROPIC_API_KEY"
  "OPENAI_API_KEY"
  "api[_-]?key.*[=:].*[A-Za-z0-9]{20,}"
  "secret[_-]?key.*[=:].*[A-Za-z0-9]{20,}"
  "password.*[=:].*[A-Za-z0-9]{8,}"
  "token.*[=:].*[A-Za-z0-9]{20,}"
)

# Allowlist for expected CI tokens (GitHub Actions OIDC, etc.)
ALLOWED_ENV_VARS=(
  "GITHUB_TOKEN"
  "ACTIONS_ID_TOKEN_REQUEST_TOKEN"
  "ACTIONS_RUNTIME_TOKEN"
)

check_environment() {
  log "Scanning current process environment"

  while IFS='=' read -r key value; do
    # Skip empty keys
    [[ -z "$key" ]] && continue

    # Skip allowlisted vars
    local allowed=0
    for allowed_var in "${ALLOWED_ENV_VARS[@]}"; do
      if [[ "$key" == "$allowed_var" ]]; then
        allowed=1
        break
      fi
    done
    [[ $allowed -eq 1 ]] && continue

    # Check against high-risk patterns
    for pattern in "${HIGH_RISK_PATTERNS[@]}"; do
      if echo "$value" | grep -qiE "$pattern"; then
        log "FINDING: High-risk secret pattern in environment variable '$key'"
        FINDINGS=$((FINDINGS + 1))
        # Redact the value in output
        echo "{\"type\":\"env\",\"variable\":\"$key\",\"pattern\":\"$pattern\",\"redacted\":true}" >> "$REPORT_FILE.tmp"
      fi
    done
  done < <(env)
}

check_process_environ() {
  log "Scanning /proc/*/environ for leaked secrets"

  # Only check processes we have permission to read
  for proc_dir in /proc/[0-9]*; do
    [[ ! -r "$proc_dir/environ" ]] && continue

    local pid="${proc_dir##*/}"
    local cmdline=""
    if [[ -r "$proc_dir/cmdline" ]]; then
      cmdline=$(tr '\0' ' ' < "$proc_dir/cmdline" 2>/dev/null || echo "unknown")
    fi

    while IFS='=' read -r -d $'\0' key value; do
      [[ -z "$key" ]] && continue

      # Skip allowlisted vars
      local allowed=0
      for allowed_var in "${ALLOWED_ENV_VARS[@]}"; do
        if [[ "$key" == "$allowed_var" ]]; then
          allowed=1
          break
        fi
      done
      [[ $allowed -eq 1 ]] && continue

      # Check against high-risk patterns
      for pattern in "${HIGH_RISK_PATTERNS[@]}"; do
        if echo "$value" | grep -qiE "$pattern"; then
          log "FINDING: High-risk secret pattern in process $pid environment variable '$key'"
          FINDINGS=$((FINDINGS + 1))
          echo "{\"type\":\"proc_environ\",\"pid\":$pid,\"cmdline\":\"${cmdline}\",\"variable\":\"$key\",\"pattern\":\"$pattern\",\"redacted\":true}" >> "$REPORT_FILE.tmp"
        fi
      done
    done < "$proc_dir/environ" 2>/dev/null || continue
  done
}

# Initialize report
echo "[]" > "$REPORT_FILE"

# Run checks
check_environment
check_process_environ

# Consolidate findings
if [[ -f "$REPORT_FILE.tmp" ]]; then
  jq -s '.' "$REPORT_FILE.tmp" > "$REPORT_FILE"
  rm -f "$REPORT_FILE.tmp"
fi

# Report results
if [[ $FINDINGS -gt 0 ]]; then
  log "ERROR: Found $FINDINGS high-risk secret(s) in runtime environment"
  log "Report: $REPORT_FILE"
  exit 1
else
  log "No high-risk secrets detected in runtime environment"
  echo "{\"findings\":0,\"status\":\"clean\",\"scanned_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" | jq '.' > "$REPORT_FILE"
  exit 0
fi
