#!/usr/bin/env bash
# Sign the complete evidence bundle with cosign
# Creates a tamper-proof attestation of all evidence artifacts
#
# This provides:
# - Chain of custody for audit evidence
# - Non-repudiation of CI/CD decisions
# - Integrity verification for compliance
# - Bundle digest for immutable reference

set -euo pipefail

EVIDENCE_DIR="${1:-artifacts/evidence}"
OUTPUT_DIR="${2:-artifacts/signed-evidence}"
BUNDLE_NAME="${3:-evidence-bundle-$(date +%Y%m%d-%H%M%S)}"

mkdir -p "$OUTPUT_DIR"

log() {
  echo "[evidence-sign] $*" >&2
}

# Check for required tools
for tool in cosign tar sha256sum jq; do
  if ! command -v "$tool" &>/dev/null; then
    log "ERROR: $tool is required but not installed"
    exit 1
  fi
done

# Create manifest of all evidence files
create_manifest() {
  local manifest_file="$OUTPUT_DIR/evidence-manifest.json"
  log "Creating evidence manifest..."

  {
    echo '{"version": "1.0", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'", "files": ['

    local first=true
    find "$EVIDENCE_DIR" -type f | sort | while read -r file; do
      if [[ "$first" != "true" ]]; then
        echo ","
      fi
      first=false

      local rel_path="${file#$EVIDENCE_DIR/}"
      local sha256=$(sha256sum "$file" | cut -d' ' -f1)
      local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)

      printf '  {"path": "%s", "sha256": "%s", "size": %d}' \
        "$rel_path" "$sha256" "$size"
    done

    echo ""
    echo ']}'
  } | jq '.' > "$manifest_file"

  log "Manifest created: $manifest_file"
}

# Create tarball of all evidence
create_bundle() {
  local bundle_file="$OUTPUT_DIR/${BUNDLE_NAME}.tar.gz"
  log "Creating evidence bundle tarball..."

  # Include manifest in the bundle
  cp "$OUTPUT_DIR/evidence-manifest.json" "$EVIDENCE_DIR/"

  # Create reproducible tarball (sorted, no timestamps)
  tar czf "$bundle_file" \
    --sort=name \
    --mtime='@0' \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -C "$(dirname "$EVIDENCE_DIR")" \
    "$(basename "$EVIDENCE_DIR")"

  # Calculate bundle digest
  local bundle_sha256=$(sha256sum "$bundle_file" | cut -d' ' -f1)
  echo "$bundle_sha256" > "$OUTPUT_DIR/${BUNDLE_NAME}.sha256"

  log "Bundle created: $bundle_file"
  log "Bundle SHA256: $bundle_sha256"

  echo "$bundle_file"
}

# Sign the bundle with cosign
sign_bundle() {
  local bundle_file="$1"
  local sig_file="${bundle_file}.sig"
  local cert_file="${bundle_file}.crt"

  log "Signing evidence bundle with cosign..."

  # Sign the bundle (keyless with GitHub OIDC)
  cosign sign-blob \
    --yes \
    --oidc-provider github \
    --oidc-issuer https://token.actions.githubusercontent.com \
    --bundle "${sig_file}" \
    "$bundle_file"

  # Extract certificate for verification
  if [[ -f "${sig_file}" ]]; then
    jq -r '.cert' "${sig_file}" | base64 -d > "$cert_file"
    log "Signature bundle: ${sig_file}"
    log "Certificate: ${cert_file}"
  fi

  # Upload to Rekor transparency log
  local rekor_bundle="${bundle_file}.rekor"
  if cosign upload blob --file "$bundle_file" --signature "${sig_file}" > "$rekor_bundle" 2>&1; then
    log "Uploaded to Rekor: $(grep -o 'tlog entry created with index: [0-9]*' "$rekor_bundle" || echo 'see file')"
  fi
}

# Create attestation for the bundle
create_attestation() {
  local bundle_file="$1"
  local bundle_sha256=$(cat "${bundle_file%.tar.gz}.sha256")
  local attestation_file="$OUTPUT_DIR/evidence-attestation.json"

  log "Creating in-toto attestation..."

  # Create in-toto attestation
  cat > "$attestation_file" <<EOF
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v1",
  "subject": [{
    "name": "${BUNDLE_NAME}",
    "digest": {
      "sha256": "${bundle_sha256}"
    }
  }],
  "predicate": {
    "buildDefinition": {
      "buildType": "https://github.com/ci-cd-hub/evidence-bundle/v1",
      "externalParameters": {
        "workflow": "${GITHUB_WORKFLOW:-unknown}",
        "repository": "${GITHUB_REPOSITORY:-unknown}",
        "ref": "${GITHUB_REF:-unknown}"
      }
    },
    "runDetails": {
      "builder": {
        "id": "https://github.com/actions/runner"
      },
      "metadata": {
        "invocationId": "${GITHUB_RUN_ID:-unknown}-${GITHUB_RUN_ATTEMPT:-1}",
        "startedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      }
    },
    "evidence": {
      "manifest": "evidence-manifest.json",
      "files": $(jq '.files | length' "$OUTPUT_DIR/evidence-manifest.json"),
      "totalSize": $(jq '.files | map(.size) | add' "$OUTPUT_DIR/evidence-manifest.json")
    }
  }
}
EOF

  # Sign the attestation
  cosign attest-blob \
    --yes \
    --oidc-provider github \
    --oidc-issuer https://token.actions.githubusercontent.com \
    --type "https://slsa.dev/provenance/v1" \
    --predicate "$attestation_file" \
    "$bundle_file" > "${attestation_file}.sig"

  log "Attestation created: $attestation_file"
}

# Verify the signed bundle (for testing)
verify_bundle() {
  local bundle_file="$1"
  local sig_file="${bundle_file}.sig"

  log "Verifying signed bundle..."

  # Verify with cosign
  if cosign verify-blob \
    --bundle "${sig_file}" \
    --certificate-identity-regexp "https://github.com/${GITHUB_REPOSITORY:-.*}/.*" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    "$bundle_file"; then
    log "✅ Bundle signature verified successfully"
  else
    log "❌ Bundle signature verification failed"
    return 1
  fi
}

# Generate verification instructions
generate_verification_instructions() {
  local bundle_file="$1"
  local instructions_file="$OUTPUT_DIR/VERIFICATION.md"

  cat > "$instructions_file" <<EOF
# Evidence Bundle Verification Instructions

## Bundle Details
- File: \`${BUNDLE_NAME}.tar.gz\`
- SHA256: \`$(cat "${bundle_file%.tar.gz}.sha256")\`
- Signed: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Verification Steps

1. **Verify bundle signature:**
\`\`\`bash
cosign verify-blob \\
  --bundle "${BUNDLE_NAME}.tar.gz.sig" \\
  --certificate-identity-regexp "https://github.com/${GITHUB_REPOSITORY}/.*" \\
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \\
  "${BUNDLE_NAME}.tar.gz"
\`\`\`

2. **Verify bundle integrity:**
\`\`\`bash
echo "$(cat "${bundle_file%.tar.gz}.sha256")  ${BUNDLE_NAME}.tar.gz" | sha256sum -c
\`\`\`

3. **Extract and verify contents:**
\`\`\`bash
tar xzf "${BUNDLE_NAME}.tar.gz"
cd evidence/
sha256sum -c evidence-manifest.json
\`\`\`

4. **Query Rekor for transparency proof:**
\`\`\`bash
rekor-cli search --sha256 $(cat "${bundle_file%.tar.gz}.sha256")
\`\`\`

## Bundle Contents
$(jq -r '.files[] | "- " + .path' "$OUTPUT_DIR/evidence-manifest.json")

## Attestation
The bundle includes a SLSA provenance attestation that can be verified:
\`\`\`bash
cosign verify-attestation \\
  --type https://slsa.dev/provenance/v1 \\
  --certificate-identity-regexp "https://github.com/${GITHUB_REPOSITORY}/.*" \\
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \\
  "${BUNDLE_NAME}.tar.gz"
\`\`\`
EOF

  log "Verification instructions: $instructions_file"
}

# Main execution
main() {
  log "Starting evidence bundle signing"
  log "Evidence directory: $EVIDENCE_DIR"
  log "Output directory: $OUTPUT_DIR"

  if [[ ! -d "$EVIDENCE_DIR" ]]; then
    log "ERROR: Evidence directory not found: $EVIDENCE_DIR"
    exit 1
  fi

  # Check if running in GitHub Actions for OIDC
  if [[ -z "${GITHUB_ACTIONS:-}" ]]; then
    log "WARNING: Not running in GitHub Actions - keyless signing may fail"
    log "Set COSIGN_EXPERIMENTAL=1 for local testing with other providers"
  fi

  # Create manifest of all evidence
  create_manifest

  # Create tarball bundle
  BUNDLE_FILE=$(create_bundle)

  # Sign the bundle
  sign_bundle "$BUNDLE_FILE"

  # Create attestation
  create_attestation "$BUNDLE_FILE"

  # Verify the signature immediately after signing
  if [[ "${VERIFY_AFTER_SIGN:-true}" == "true" ]]; then
    log "Verifying signature immediately after signing..."
    if ! verify_bundle "$BUNDLE_FILE"; then
      log "ERROR: Signature verification failed immediately after signing"
      log "This indicates a critical issue with the signing process"
      exit 1
    fi
    log "✅ Signature verified successfully"
  fi

  # Generate verification instructions
  generate_verification_instructions "$BUNDLE_FILE"

  log "================================================"
  log "Evidence bundle signed successfully!"
  log "Bundle: $BUNDLE_FILE"
  log "SHA256: $(cat "${BUNDLE_FILE%.tar.gz}.sha256")"
  log "Signature: ${BUNDLE_FILE}.sig"
  log "================================================"
}

# Run main function
main "$@"