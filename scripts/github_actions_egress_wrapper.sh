#!/usr/bin/env bash
# Egress control for GitHub-hosted runners using HTTP/HTTPS proxy approach
# This works without sudo by intercepting network calls at the application layer
#
# Usage: ./github_actions_egress_wrapper.sh <command to run>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVIDENCE_DIR="${GITHUB_WORKSPACE:-$(pwd)}/artifacts/security"
mkdir -p "$EVIDENCE_DIR"

log() {
  echo "[egress-wrapper] $*" >&2
}

# Allowed destinations (from plan.md egress allowlist)
ALLOWED_DOMAINS=(
  "github.com"
  "api.github.com"
  "ghcr.io"
  "registry.npmjs.org"
  "pypi.org"
  "files.pythonhosted.org"
  "rekor.sigstore.dev"
  "fulcio.sigstore.dev"
  "tuf-repo-cdn.sigstore.dev"
  "objects.githubusercontent.com"
  "storage.googleapis.com"
)

# Create egress monitoring wrapper
create_proxy_pac() {
  local pac_file="$EVIDENCE_DIR/proxy.pac"

  cat > "$pac_file" <<'EOF'
function FindProxyForURL(url, host) {
  // Allowed domains - must match plan.md egress allowlist
  var allowed = [
    "github.com",
    "api.github.com",
    "ghcr.io",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "rekor.sigstore.dev",
    "fulcio.sigstore.dev",
    "tuf-repo-cdn.sigstore.dev",
    "objects.githubusercontent.com",
    "storage.googleapis.com"
  ];

  // Check if host matches allowed list
  for (var i = 0; i < allowed.length; i++) {
    if (host == allowed[i] || host.endsWith("." + allowed[i])) {
      return "DIRECT";  // Allow
    }
  }

  // Log denied access
  alert("BLOCKED: " + host);
  return "PROXY 127.0.0.1:9999";  // Block (proxy doesn't exist)
}
EOF

  echo "file://$pac_file"
}

# Monitor network access
monitor_egress() {
  local command="$*"
  local log_file="$EVIDENCE_DIR/egress-attempts.log"

  log "Starting egress-monitored command: $command"
  log "Allowed domains: ${ALLOWED_DOMAINS[*]}"

  # Set proxy environment variables to detect egress
  # Most tools (curl, wget, pip, npm) respect these
  export HTTP_PROXY="http://localhost:9999"
  export HTTPS_PROXY="http://localhost:9999"
  export http_proxy="http://localhost:9999"
  export https_proxy="http://localhost:9999"

  # Add exception for allowed domains via NO_PROXY
  export NO_PROXY="$(IFS=,; echo "${ALLOWED_DOMAINS[*]}")"
  export no_proxy="$NO_PROXY"

  log "NO_PROXY set to: $NO_PROXY"

  # Run command with monitoring
  if eval "$command" 2>&1 | tee -a "$log_file"; then
    log "Command completed successfully"
    analyze_egress_attempts
    return 0
  else
    local exit_code=$?
    log "Command failed with exit code $exit_code"
    analyze_egress_attempts
    return $exit_code
  fi
}

# Analyze egress attempts from logs
analyze_egress_attempts() {
  local log_file="$EVIDENCE_DIR/egress-attempts.log"
  local report_file="$EVIDENCE_DIR/egress-report.json"

  if [[ ! -f "$log_file" ]]; then
    log "No egress log found"
    return 0
  fi

  # Check for proxy errors (attempts to blocked destinations)
  local blocked_count=0
  if grep -q "proxy.*refused\|Could not resolve proxy\|Failed to connect to.*9999" "$log_file" 2>/dev/null; then
    blocked_count=$(grep -c "proxy.*refused\|Could not resolve proxy\|Failed to connect to.*9999" "$log_file" 2>/dev/null || echo 0)
    log "WARNING: Detected $blocked_count attempts to blocked destinations"
  fi

  # Generate report
  cat > "$report_file" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "enforcement": "proxy-based",
  "allowed_domains": $(printf '%s\n' "${ALLOWED_DOMAINS[@]}" | jq -R . | jq -s .),
  "blocked_attempts": $blocked_count,
  "log_file": "$log_file"
}
EOF

  if [[ $blocked_count -gt 0 ]]; then
    log "ERROR: Build attempted to access unauthorized network destinations"
    log "See $log_file for details"
    echo "::error::Egress policy violation - $blocked_count blocked attempts"
    return 1
  fi

  log "✅ No unauthorized egress detected"
  return 0
}

# Main execution
if [[ $# -eq 0 ]]; then
  log "ERROR: No command specified"
  echo "Usage: $0 <command to run>"
  exit 1
fi

monitor_egress "$@"
