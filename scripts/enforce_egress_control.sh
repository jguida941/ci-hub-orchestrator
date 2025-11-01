#!/usr/bin/env bash
# Production egress enforcement with iptables
# Implements technical network-level egress control
#
# MODES:
#   audit   - Test connectivity, log results (default)
#   enforce - Apply iptables rules to block unauthorized egress
#   verify  - Check if enforcement is active
#
# REQUIREMENTS (for enforce mode):
#   - Root/sudo access for iptables
#   - Linux environment (GitHub Actions ubuntu-latest)
#
# SECURITY NOTE:
#   This provides defense-in-depth but should be combined with:
#   - Kubernetes NetworkPolicy (for container workloads)
#   - Cloud provider network security groups
#   - Service mesh policies (Istio/Linkerd)

set -euo pipefail

MODE="${1:-audit}"
REPORT_FILE="${2:-artifacts/security/egress-enforcement.json}"
EVIDENCE_DIR="$(dirname "$REPORT_FILE")"
mkdir -p "$EVIDENCE_DIR"

# Chain name for our rules
CHAIN_NAME="CI_EGRESS_CONTROL"

log() {
  echo "[egress-enforce] $*" >&2
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "${EVIDENCE_DIR}/egress-enforcement.log"
}

# Required destinations (production allowlist)
declare -A ALLOWED_HOSTS=(
  ["github.com"]="443"
  ["api.github.com"]="443"
  ["ghcr.io"]="443"
  ["registry.npmjs.org"]="443"
  ["pypi.org"]="443"
  ["files.pythonhosted.org"]="443"
  ["rekor.sigstore.dev"]="443"
  ["fulcio.sigstore.dev"]="443"
  ["tuf-repo-cdn.sigstore.dev"]="443"
  ["objects.githubusercontent.com"]="443"
  ["storage.googleapis.com"]="443"  # For gcloud/gsutil
  ["oauth2.googleapis.com"]="443"    # For GCP auth
)

resolve_hosts() {
  # Resolve hostnames to IPs for iptables rules
  local host_ips_file="${EVIDENCE_DIR}/resolved-ips.txt"
  > "$host_ips_file"

  for host in "${!ALLOWED_HOSTS[@]}"; do
    local port="${ALLOWED_HOSTS[$host]}"
    # Resolve all IPs for the host (handles CDNs with multiple IPs)
    if ips=$(dig +short "$host" 2>/dev/null | grep -E '^[0-9.]+$'); then
      for ip in $ips; do
        echo "${ip}:${port}:${host}" >> "$host_ips_file"
        log "Resolved ${host} -> ${ip}:${port}"
      done
    else
      log "WARNING: Failed to resolve ${host}"
    fi
  done
}

apply_iptables_rules() {
  log "Applying iptables egress enforcement rules..."

  # Check if we have sudo/root
  if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    log "ERROR: Need root/sudo access for iptables enforcement"
    return 1
  fi

  # Use sudo if not root
  local IPTABLES="iptables"
  [[ $EUID -ne 0 ]] && IPTABLES="sudo iptables"

  # Create custom chain if it doesn't exist
  if ! $IPTABLES -L "$CHAIN_NAME" -n &>/dev/null; then
    log "Creating iptables chain: $CHAIN_NAME"
    $IPTABLES -N "$CHAIN_NAME"
  fi

  # Clear existing rules in our chain
  $IPTABLES -F "$CHAIN_NAME"

  # Allow loopback
  $IPTABLES -A "$CHAIN_NAME" -o lo -j ACCEPT

  # Allow established connections
  $IPTABLES -A "$CHAIN_NAME" -m state --state ESTABLISHED,RELATED -j ACCEPT

  # Allow DNS (required for hostname resolution)
  $IPTABLES -A "$CHAIN_NAME" -p udp --dport 53 -j ACCEPT
  $IPTABLES -A "$CHAIN_NAME" -p tcp --dport 53 -j ACCEPT

  # Read resolved IPs and add allow rules
  local host_ips_file="${EVIDENCE_DIR}/resolved-ips.txt"
  if [[ -f "$host_ips_file" ]]; then
    while IFS=: read -r ip port host; do
      $IPTABLES -A "$CHAIN_NAME" -p tcp -d "$ip" --dport "$port" -m comment --comment "Allow ${host}" -j ACCEPT
      log "Added rule: Allow ${host} (${ip}:${port})"
    done < "$host_ips_file"
  fi

  # Log and drop everything else
  $IPTABLES -A "$CHAIN_NAME" -m limit --limit 5/min -j LOG --log-prefix "EGRESS-BLOCKED: "
  $IPTABLES -A "$CHAIN_NAME" -j DROP

  # Insert our chain into OUTPUT if not already there
  if ! $IPTABLES -L OUTPUT -n | grep -q "$CHAIN_NAME"; then
    log "Activating egress control chain"
    $IPTABLES -I OUTPUT -j "$CHAIN_NAME"
  fi

  # Save rules for persistence (if available)
  if command -v iptables-save &>/dev/null; then
    $IPTABLES-save > "${EVIDENCE_DIR}/iptables-rules.txt"
    log "Saved iptables rules to ${EVIDENCE_DIR}/iptables-rules.txt"
  fi

  log "Egress enforcement active with iptables"
}

remove_iptables_rules() {
  log "Removing iptables egress enforcement rules..."

  local IPTABLES="iptables"
  [[ $EUID -ne 0 ]] && IPTABLES="sudo iptables"

  # Remove from OUTPUT chain
  while $IPTABLES -L OUTPUT -n | grep -q "$CHAIN_NAME"; do
    $IPTABLES -D OUTPUT -j "$CHAIN_NAME" 2>/dev/null || true
  done

  # Delete our chain
  if $IPTABLES -L "$CHAIN_NAME" -n &>/dev/null 2>&1; then
    $IPTABLES -F "$CHAIN_NAME"
    $IPTABLES -X "$CHAIN_NAME"
    log "Removed egress control chain"
  fi
}

verify_enforcement() {
  log "Verifying egress enforcement status..."

  local IPTABLES="iptables"
  [[ $EUID -ne 0 ]] && command -v sudo &>/dev/null && IPTABLES="sudo iptables"

  local status="inactive"
  local rule_count=0

  # Check if our chain exists and is in OUTPUT
  if $IPTABLES -L OUTPUT -n 2>/dev/null | grep -q "$CHAIN_NAME"; then
    status="active"
    rule_count=$($IPTABLES -L "$CHAIN_NAME" -n 2>/dev/null | grep -c ACCEPT || echo 0)
    log "Enforcement is ACTIVE with ${rule_count} allow rules"

    # Test a forbidden destination
    if timeout 2 bash -c "exec 3<>/dev/tcp/example.com/443" 2>/dev/null; then
      log "WARNING: Forbidden host reachable - enforcement may be bypassed"
      status="bypassed"
    else
      log "Verified: Forbidden hosts are blocked"
    fi
  else
    log "Enforcement is INACTIVE (chain not found in OUTPUT)"
  fi

  # Generate verification report
  cat > "$REPORT_FILE" <<EOF
{
  "mode": "verify",
  "status": "${status}",
  "rule_count": ${rule_count},
  "chain_name": "${CHAIN_NAME}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "evidence": {
    "iptables_rules": "${EVIDENCE_DIR}/iptables-rules.txt",
    "resolved_ips": "${EVIDENCE_DIR}/resolved-ips.txt"
  }
}
EOF

  [[ "$status" == "active" ]] && exit 0 || exit 1
}

test_connectivity() {
  log "Testing egress connectivity..."

  local passed=0
  local failed=0

  # Test allowed hosts
  for host in "${!ALLOWED_HOSTS[@]}"; do
    local port="${ALLOWED_HOSTS[$host]}"
    if timeout 3 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
      log "✓ ${host}:${port} - Allowed and reachable"
      ((passed++))
    else
      log "✗ ${host}:${port} - Allowed but NOT reachable"
      ((failed++))
    fi
  done

  # Test forbidden hosts (should fail if enforcement is active)
  local forbidden_hosts=("example.com:443" "httpbin.org:443" "badssl.com:443")
  for endpoint in "${forbidden_hosts[@]}"; do
    local host="${endpoint%%:*}"
    local port="${endpoint#*:}"
    if timeout 2 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
      if [[ "$MODE" == "enforce" ]]; then
        log "✗ ${host}:${port} - Forbidden but REACHABLE (enforcement failed)"
        ((failed++))
      else
        log "⚠ ${host}:${port} - Forbidden but reachable (audit mode)"
      fi
    else
      log "✓ ${host}:${port} - Forbidden and blocked"
      ((passed++))
    fi
  done

  cat > "$REPORT_FILE" <<EOF
{
  "mode": "${MODE}",
  "passed": ${passed},
  "failed": ${failed},
  "total_tests": $((passed + failed)),
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$([[ $failed -eq 0 ]] && echo "pass" || echo "fail")",
  "allowed_hosts": $(printf '%s\n' "${!ALLOWED_HOSTS[@]}" | jq -R . | jq -s .)
}
EOF

  [[ $failed -eq 0 ]] && exit 0 || exit 1
}

# Main execution
log "Starting egress control - mode: ${MODE}"
log "================================================"

case "$MODE" in
  audit)
    resolve_hosts
    test_connectivity
    log "Audit complete - no enforcement applied"
    ;;

  enforce)
    resolve_hosts
    apply_iptables_rules
    sleep 2  # Let rules settle
    test_connectivity
    log "Enforcement active - unauthorized egress blocked"
    ;;

  verify)
    verify_enforcement
    ;;

  remove)
    remove_iptables_rules
    log "Enforcement removed"
    ;;

  *)
    log "ERROR: Invalid mode: ${MODE}"
    log "Usage: $0 {audit|enforce|verify|remove} [report_file]"
    exit 1
    ;;
esac

log "Evidence saved to: ${REPORT_FILE}"
log "================================================"