#!/usr/bin/env bash
# Allow CI overrides; otherwise detect from uname.
set -euo pipefail

ORAS_VERSION="1.2.0"
COSIGN_VERSION="v2.2.4"
REKOR_VERSION="v1.4.0"
SYFT_VERSION="1.18.0"
GRYPE_VERSION="0.102.0"
CRANE_VERSION="v0.19.2"
SLSA_VERIFIER_VERSION="v2.6.0"

# Allow CI overrides; otherwise detect from uname.
log() {
  echo "[install_tools] $*"
}
if [[ -n "${TOOL_OS:-}" ]]; then
  OS="${TOOL_OS}"
else
  uname_s="$(uname -s 2>/dev/null || echo linux)"
  case "${uname_s}" in
    Linux) OS="linux" ;;
    Darwin) OS="darwin" ;;
    MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
    *)
      log "Unsupported operating system '${uname_s}'"
      exit 1
      ;;
  esac
fi

if [[ -n "${TOOL_ARCH:-}" ]]; then
  ARCH="${TOOL_ARCH}"
else
  uname_m="$(uname -m 2>/dev/null || echo amd64)"
  case "${uname_m}" in
    x86_64|x86-64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    i386|i686) ARCH="386" ;;
    *)
      log "Unsupported architecture '${uname_m}'"
      exit 1
      ;;
  esac
fi

OS="${OS,,}"
ARCH="${ARCH,,}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

download_and_verify() {
  local url=$1
  local destination=$2
  local checksum_url=$3

  curl -fsSL "$url" -o "$destination"
  curl -fsSL "$checksum_url" -o "${destination}.sha256"
  (cd "$(dirname "$destination")" && sha256sum -c "$(basename "${destination}.sha256")")
}

install_oras() {
  local tar="oras_${ORAS_VERSION}_${OS}_${ARCH}.tar.gz"
  local base_url="https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}"
  local url="${base_url}/${tar}"
  local checksum_file="oras_${ORAS_VERSION}_checksums.txt"
  log "Installing oras ${ORAS_VERSION}"
  curl -fsSL "$url" -o "$TMP_DIR/${tar}"
  curl -fsSL "${base_url}/${checksum_file}" -o "$TMP_DIR/${checksum_file}"
  (
    cd "$TMP_DIR"
    grep -F "  ${tar}" "${checksum_file}" > "${tar}.sha256"
    sha256sum -c "${tar}.sha256"
  )
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" oras
  sudo install -m 0755 "$TMP_DIR/oras" /usr/local/bin/oras
  if ! oras version | grep -E "Version:\s+${ORAS_VERSION}(\+|$)" >/dev/null; then
    log "oras version mismatch"
    exit 1
  fi
}

install_cosign() {
  local file="cosign-${OS}-${ARCH}"
  local base_url="https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}"
  local url="${base_url}/${file}"
  log "Installing cosign ${COSIGN_VERSION}"

  # Download the binary
  if ! curl -fsSL "$url" -o "$TMP_DIR/${file}"; then
    log "Failed to download cosign binary from ${url}"
    exit 1
  fi

  # Try to find and verify checksum (optional - don't fail if not found)
  local checksum_source=""
  local checksum_candidates=(
    "cosign_${COSIGN_VERSION}_checksums.txt"
    "cosign_${COSIGN_VERSION#v}_checksums.txt"
    "cosign_checksums.txt"
  )
  for candidate in "${checksum_candidates[@]}"; do
    if curl -fsSL "${base_url}/${candidate}" -o "$TMP_DIR/${candidate}" 2>/dev/null; then
      checksum_source="$TMP_DIR/${candidate}"
      break
    fi
  done

  if [[ -n "$checksum_source" ]]; then
    (
      cd "$TMP_DIR"
      # Extract only the checksum for our specific file, ignoring any SBOM or other entries
      if grep -E "^[a-fA-F0-9]{64}\s+${file}\$" "$(basename "$checksum_source")" > "${file}.sha256" 2>/dev/null; then
        if ! sha256sum -c "${file}.sha256"; then
          log "ERROR: Checksum verification failed for ${file}"
          exit 1
        fi
        log "Checksum verified successfully for ${file}"
      else
        log "ERROR: Checksum not found in manifest for ${file}"
        exit 1
      fi
    )
  else
    log "ERROR: Unable to locate cosign checksum manifest - this is a security risk"
    log "Checksums are required for all downloaded binaries"
    exit 1
  fi

  sudo install -m 0755 "$TMP_DIR/${file}" /usr/local/bin/cosign
  installed_version="$(cosign version --short 2>/dev/null | tr -d '\n')"
  log "Detected cosign version reporting as '${installed_version:-unknown}'"
  # Accept either v-prefixed or bare semantic versions to match upstream output formats.
  expected_normalized="${COSIGN_VERSION#v}"
  installed_normalized="${installed_version#v}"
  if [[ -z "${installed_normalized}" || "${installed_normalized}" != "${expected_normalized}" ]]; then
    log "ERROR: cosign version mismatch - expected ${COSIGN_VERSION} (normalized ${expected_normalized}), found ${installed_version:-unknown}"
    exit 1
  fi
}

install_rekor() {
  local base_url="https://github.com/sigstore/rekor/releases/download/${REKOR_VERSION}"
  local version_plain="${REKOR_VERSION#v}"
  local -a candidates
  if [[ "$OS" == "windows" ]]; then
    candidates=(
      "rekor-cli-${OS}-${ARCH}.exe"
      "rekor-cli-${version_plain}-${OS}-${ARCH}.exe"
      "rekor-cli-${OS}-${ARCH}.zip"
      "rekor-cli_${version_plain}_${OS}_${ARCH}.zip"
      "rekor-cli-${version_plain}-${OS}-${ARCH}.zip"
    )
  else
    candidates=(
      "rekor-cli-${OS}-${ARCH}"
      "rekor-cli-${version_plain}-${OS}-${ARCH}"
      "rekor-cli-${OS}-${ARCH}.tar.gz"
      "rekor-cli-${version_plain}-${OS}-${ARCH}.tar.gz"
      "rekor-cli_${version_plain}_${OS}_${ARCH}.tar.gz"
      "rekor-cli_${OS}_${ARCH}.tar.gz"
    )
  fi
  log "Installing rekor-cli ${REKOR_VERSION}"

  local success=0
  for candidate in "${candidates[@]}"; do
    local url="${base_url}/${candidate}"
    local download_path="${TMP_DIR}/${candidate}"
    local checksum_path="${download_path}.sha256"
    rm -f "$download_path" "$checksum_path"
    if ! curl -fsSL "$url" -o "$download_path"; then
      log "Failed to download rekor-cli asset from ${url}"
      continue
    fi
    if ! curl -fsSL "${url}.sha256" -o "$checksum_path"; then
      log "ERROR: No checksum file found for rekor-cli asset ${candidate}"
      rm -f "$download_path" "$checksum_path"
      continue
    fi
    if ! (cd "$TMP_DIR" && sha256sum -c "$(basename "$checksum_path")"); then
      log "ERROR: rekor-cli checksum verification failed for ${candidate}"
      rm -f "$download_path" "$checksum_path"
      continue
    fi
    rm -f "$checksum_path"
    if [[ "$candidate" == *.tar.gz ]]; then
      local extract_dir
      extract_dir="$(mktemp -d "${TMP_DIR}/rekor-cli-extract.XXXXXX")"
      if ! tar -xzf "$download_path" -C "$extract_dir"; then
        log "ERROR: Failed to extract ${candidate}"
        rm -rf "$extract_dir"
        rm -f "$download_path"
        continue
      fi
      local extracted
      extracted="$(find "$extract_dir" -type f -name 'rekor-cli*' | head -n 1)"
      if [[ -z "$extracted" ]]; then
        log "ERROR: Extracted rekor-cli archive missing binary (${candidate})"
        rm -rf "$extract_dir"
        rm -f "$download_path"
        continue
      fi
      sudo install -m 0755 "$extracted" /usr/local/bin/rekor-cli
      rm -rf "$extract_dir"
      rm -f "$download_path"
    elif [[ "$candidate" == *.zip ]]; then
      if ! command -v unzip >/dev/null 2>&1; then
        log "ERROR: unzip not available to extract ${candidate}"
        rm -f "$download_path"
        continue
      fi
      local extract_dir
      extract_dir="$(mktemp -d "${TMP_DIR}/rekor-cli-extract.XXXXXX")"
      if ! unzip -q "$download_path" -d "$extract_dir"; then
        log "ERROR: Failed to extract ${candidate}"
        rm -rf "$extract_dir"
        rm -f "$download_path"
        continue
      fi
      local extracted
      extracted="$(find "$extract_dir" -type f -name 'rekor-cli*' | head -n 1)"
      if [[ -z "$extracted" ]]; then
        log "ERROR: Extracted rekor-cli archive missing binary (${candidate})"
        rm -rf "$extract_dir"
        rm -f "$download_path"
        continue
      fi
      sudo install -m 0755 "$extracted" /usr/local/bin/rekor-cli
      rm -rf "$extract_dir"
      rm -f "$download_path"
    else
      sudo install -m 0755 "$download_path" /usr/local/bin/rekor-cli
      rm -f "$download_path"
    fi
    success=1
    break
  done

  if [[ "$success" -ne 1 ]]; then
    log "ERROR: Unable to download a supported rekor-cli asset for ${REKOR_VERSION}"
    exit 1
  fi

  # Enforce version match per plan.md supply-chain pinning requirements
  # rekor-cli prints ASCII banner before version info, so capture full output
  VERSION_OUTPUT=$(rekor-cli version 2>&1 || true)
  if ! echo "$VERSION_OUTPUT" | grep -q "${REKOR_VERSION}"; then
    log "rekor-cli version mismatch (expected ${REKOR_VERSION})"
    echo "$VERSION_OUTPUT"
    exit 1
  fi
  log "rekor-cli ${REKOR_VERSION} verified"
}

install_syft() {
  local tar="syft_${SYFT_VERSION}_${OS}_${ARCH}.tar.gz"
  local url="https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/${tar}"
  log "Installing syft ${SYFT_VERSION}"

  # Download tarball
  if ! curl -fsSL "$url" -o "$TMP_DIR/${tar}"; then
    log "Failed to download syft from ${url}"
    exit 1
  fi

  # Download and verify checksum (MANDATORY for security)
  if curl -fsSL "${url}.sha256" -o "$TMP_DIR/${tar}.sha256" 2>/dev/null; then
    (cd "$TMP_DIR" && sha256sum -c "$(basename "${tar}.sha256")") || {
      log "ERROR: syft checksum verification failed"
      exit 1
    }
  else
    log "ERROR: No checksum file found for syft ${SYFT_VERSION}"
    log "Checksums are mandatory for all downloaded binaries"
    exit 1
  fi

  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" syft
  sudo install -m 0755 "$TMP_DIR/syft" /usr/local/bin/syft
  if ! syft version | grep -E "Version:\s+${SYFT_VERSION}" >/dev/null; then
    log "syft version mismatch (expected ${SYFT_VERSION})"
    syft version || true
    exit 1
  fi
}

install_grype() {
  local tar="grype_${GRYPE_VERSION}_${OS}_${ARCH}.tar.gz"
  local url="https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/${tar}"
  log "Installing grype ${GRYPE_VERSION}"

  # Download tarball
  if ! curl -fsSL "$url" -o "$TMP_DIR/${tar}"; then
    log "Failed to download grype from ${url}"
    exit 1
  fi

  # Download and verify checksum (MANDATORY for security)
  if curl -fsSL "${url}.sha256" -o "$TMP_DIR/${tar}.sha256" 2>/dev/null; then
    (cd "$TMP_DIR" && sha256sum -c "$(basename "${tar}.sha256")") || {
      log "ERROR: grype checksum verification failed"
      exit 1
    }
  else
    log "ERROR: No checksum file found for grype ${GRYPE_VERSION}"
    log "Checksums are mandatory for all downloaded binaries"
    exit 1
  fi

  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" grype
  sudo install -m 0755 "$TMP_DIR/grype" /usr/local/bin/grype
  if ! grype version | grep -E "Version:\s+${GRYPE_VERSION}" >/dev/null; then
    log "grype version mismatch (expected ${GRYPE_VERSION})"
    grype version || true
    exit 1
  fi
}

install_crane() {
  local os_component
  case "$OS" in
    linux) os_component="Linux" ;;
    darwin) os_component="Darwin" ;;
    windows) os_component="Windows" ;;
    *)
      log "Unsupported OS for crane: $OS"
      exit 1
      ;;
  esac
  local arch_component
  case "$ARCH" in
    amd64) arch_component="x86_64" ;;
    arm64) arch_component="arm64" ;;
    386) arch_component="386" ;;
    *)
      log "Unsupported architecture for crane: $ARCH"
      exit 1
      ;;
  esac
  local tar="go-containerregistry_${os_component}_${arch_component}.tar.gz"
  local base_url="https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}"
  local url="${base_url}/${tar}"
  local checksum_file="checksums.txt"
  log "Installing crane ${CRANE_VERSION}"
  curl -fsSL "$url" -o "$TMP_DIR/${tar}"
  curl -fsSL "${base_url}/${checksum_file}" -o "$TMP_DIR/${checksum_file}"
  (
    cd "$TMP_DIR"
    grep -F "  ${tar}" "${checksum_file}" > "${tar}.sha256"
    sha256sum -c "${tar}.sha256"
  )
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" crane
  sudo install -m 0755 "$TMP_DIR/crane" /usr/local/bin/crane
  # crane prints either v-prefixed or plain semver; accept both while still enforcing the pin
  CRANE_VERSION_OUTPUT=$(crane version 2>&1 || true)
  if ! echo "$CRANE_VERSION_OUTPUT" | grep -q "${CRANE_VERSION}"; then
    if ! echo "$CRANE_VERSION_OUTPUT" | grep -q "${CRANE_VERSION#v}"; then
      log "crane version mismatch (expected ${CRANE_VERSION})"
      echo "$CRANE_VERSION_OUTPUT"
      exit 1
    fi
  fi
}

install_slsa_verifier() {
  local file="slsa-verifier-${OS}-${ARCH}"
  local base_url="https://github.com/slsa-framework/slsa-verifier/releases/download/${SLSA_VERIFIER_VERSION}"
  local url="${base_url}/${file}"
  log "Installing slsa-verifier ${SLSA_VERIFIER_VERSION}"

  # Download the binary
  if ! curl -fsSL "$url" -o "$TMP_DIR/${file}"; then
    log "Failed to download slsa-verifier binary from ${url}"
    exit 1
  fi

  # Try to download and verify checksum
  if curl -fsSL "${url}.sha256" -o "$TMP_DIR/${file}.sha256" 2>/dev/null; then
    (cd "$TMP_DIR" && sha256sum -c "$(basename "${file}.sha256")") || {
      log "slsa-verifier checksum verification failed"
      exit 1
    }
  else
    log "Warning: No checksum file found for slsa-verifier ${SLSA_VERIFIER_VERSION}, skipping verification"
  fi

  sudo install -m 0755 "$TMP_DIR/${file}" /usr/local/bin/slsa-verifier

  # Verify version
  VERSION_OUTPUT=$(slsa-verifier version 2>&1 || true)
  if ! echo "$VERSION_OUTPUT" | grep -q "${SLSA_VERIFIER_VERSION}"; then
    if ! echo "$VERSION_OUTPUT" | grep -q "${SLSA_VERIFIER_VERSION#v}"; then
      log "slsa-verifier version mismatch (expected ${SLSA_VERIFIER_VERSION})"
      echo "$VERSION_OUTPUT"
      exit 1
    fi
  fi
  log "slsa-verifier ${SLSA_VERIFIER_VERSION} verified"
}

install_oras
install_cosign
install_rekor
install_syft
install_grype
install_crane
install_slsa_verifier
