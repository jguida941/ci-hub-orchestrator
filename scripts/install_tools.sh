#!/usr/bin/env bash
# Allow CI overrides; otherwise detect from uname.
set -euo pipefail

ORAS_VERSION="1.2.0"
COSIGN_VERSION="v2.2.4"
REKOR_VERSION="v1.3.1"
SYFT_VERSION="1.18.0"
GRYPE_VERSION="0.102.0"
CRANE_VERSION="v0.19.2"

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
  local url="https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/${tar}"
  log "Installing oras ${ORAS_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${tar}" "${url}.sha256"
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" oras
  sudo install -m 0755 "$TMP_DIR/oras" /usr/local/bin/oras
  if ! oras version | grep -E "Version:\s+${ORAS_VERSION}(\+|$)" >/dev/null; then
    log "oras version mismatch"
    exit 1
  fi
}

install_cosign() {
  local file="cosign-${OS}-${ARCH}"
  local url="https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/${file}"
  log "Installing cosign ${COSIGN_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${file}" "${url}.sha256"
  sudo install -m 0755 "$TMP_DIR/${file}" /usr/local/bin/cosign
  if ! cosign version --short | tr -d '\n' | grep -q "$(printf '%s' "${COSIGN_VERSION}" | tr -d '\n')"; then
    log "cosign version mismatch"
    exit 1
  fi
}

install_rekor() {
  local file="rekor-cli-${OS}-${ARCH}"
  local url="https://github.com/sigstore/rekor/releases/download/${REKOR_VERSION}/${file}"
  log "Installing rekor-cli ${REKOR_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${file}" "${url}.sha256"
  sudo install -m 0755 "$TMP_DIR/${file}" /usr/local/bin/rekor-cli
  if ! rekor-cli version --format json | grep -E "\"GitVersion\"\\s*:\\s*\"v?${REKOR_VERSION}\"" >/dev/null; then
    log "rekor-cli version mismatch"
    exit 1
  fi
}

install_syft() {
  local tar="syft_${SYFT_VERSION}_${OS}_${ARCH}.tar.gz"
  local url="https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/${tar}"
  log "Installing syft ${SYFT_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${tar}" "${url}.sha256"
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" syft
  sudo install -m 0755 "$TMP_DIR/syft" /usr/local/bin/syft
  if ! syft version | grep -E "Version:\s+${SYFT_VERSION}" >/dev/null; then
    log "syft version mismatch"
    exit 1
  fi
}

install_grype() {
  local tar="grype_${GRYPE_VERSION}_${OS}_${ARCH}.tar.gz"
  local url="https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/${tar}"
  log "Installing grype ${GRYPE_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${tar}" "${url}.sha256"
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" grype
  sudo install -m 0755 "$TMP_DIR/grype" /usr/local/bin/grype
  if ! grype version | grep -E "Version:\s+${GRYPE_VERSION}" >/dev/null; then
    log "grype version mismatch"
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
  local url="https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}/${tar}"
  log "Installing crane ${CRANE_VERSION}"
  download_and_verify "$url" "$TMP_DIR/${tar}" "${url}.sha256"
  tar -xzf "$TMP_DIR/${tar}" -C "$TMP_DIR" crane
  sudo install -m 0755 "$TMP_DIR/crane" /usr/local/bin/crane
  if ! crane version | tr -d '\n' | grep -q "$(printf '%s' "${CRANE_VERSION}" | tr -d '\n')"; then
    log "crane version mismatch"
    exit 1
  fi
}

install_oras
install_cosign
install_rekor
install_syft
install_grype
install_crane
