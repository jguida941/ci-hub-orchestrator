#!/usr/bin/env bash
set -euo pipefail

ORAS_VERSION=1.2.0
COSIGN_VERSION=v2.2.4
SYFT_VERSION=v1.18.0
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

# Install syft using official installer
curl -fsSL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
  | sudo sh -s -- -b /usr/local/bin "${SYFT_VERSION}"
