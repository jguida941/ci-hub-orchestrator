#!/usr/bin/env bash
set -euo pipefail

ORAS_VERSION=1.2.0
COSIGN_VERSION=v2.2.4
SYFT_VERSION=v1.18.0
REKOR_VERSION=v1.3.1
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Install oras
curl -fsSLo "$TMP_DIR/oras.tar.gz" "https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_amd64.tar.gz"
tar -xzf "$TMP_DIR/oras.tar.gz" -C "$TMP_DIR" oras
chmod +x "$TMP_DIR/oras"
sudo mv "$TMP_DIR/oras" /usr/local/bin/oras

# Install cosign
curl -fsSLo "$TMP_DIR/cosign" "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
chmod +x "$TMP_DIR/cosign"
sudo mv "$TMP_DIR/cosign" /usr/local/bin/cosign

# Install rekor-cli
curl -fsSLo "$TMP_DIR/rekor.tar.gz" "https://github.com/sigstore/rekor/releases/download/${REKOR_VERSION}/rekor-cli-linux-amd64.tar.gz"
tar -xzf "$TMP_DIR/rekor.tar.gz" -C "$TMP_DIR"
REKOR_BIN=""
if [[ -f "$TMP_DIR/rekor-cli-linux-amd64" ]]; then
  REKOR_BIN="$TMP_DIR/rekor-cli-linux-amd64"
elif [[ -f "$TMP_DIR/rekor-cli" ]]; then
  REKOR_BIN="$TMP_DIR/rekor-cli"
else
  echo "rekor CLI binary not found in archive" >&2
  exit 1
fi
chmod +x "$REKOR_BIN"
sudo mv "$REKOR_BIN" /usr/local/bin/rekor-cli

# Install syft using official installer
curl -fsSL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
  | sudo sh -s -- -b /usr/local/bin "${SYFT_VERSION}"
