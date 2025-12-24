#!/usr/bin/env bash
# Spin up a disposable kind cluster, deploy Kyverno policies, capture evidence, and optionally tear everything down.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CLUSTER_NAME="kyverno-ci"
KEEP_CLUSTER=false
KYVERNO_DEPLOY_FLAGS_VALUE=""
KYVERNO_VERIFY_FLAGS_VALUE=""
KYVERNO_EVIDENCE_DIR_VALUE=""

usage() {
  cat <<'USAGE'
Usage: scripts/run_kyverno_kind.sh [options]

Options:
  --cluster-name <name>     Name for the kind cluster (default: kyverno-ci)
  --keep-cluster            Do not delete the kind cluster after running verification
  --deploy-flags <flags>    Extra flags to pass to make kyverno/deploy (quoted string)
  --verify-flags <flags>    Extra flags to pass to make kyverno/verify (quoted string)
  --evidence-dir <path>     Override KYVERNO_EVIDENCE_DIR (default: artifacts/evidence/kyverno)
  -h, --help                Show this help message

Examples:
  scripts/run_kyverno_kind.sh
  scripts/run_kyverno_kind.sh --keep-cluster --deploy-flags "--skip-install"
USAGE
}

log() {
  echo "[kyverno-kind] $*" >&2
}

cluster_exists() {
  kind get clusters 2>/dev/null | grep -Fxq "${CLUSTER_NAME}"
}

delete_cluster() {
  log "Deleting kind cluster '${CLUSTER_NAME}'"
  kind delete cluster --name "${CLUSTER_NAME}" >/dev/null
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-name)
      CLUSTER_NAME="${2-}"
      shift 2
      ;;
    --keep-cluster)
      KEEP_CLUSTER=true
      shift
      ;;
    --deploy-flags)
      KYVERNO_DEPLOY_FLAGS_VALUE="${2-}"
      shift 2
      ;;
    --verify-flags)
      KYVERNO_VERIFY_FLAGS_VALUE="${2-}"
      shift 2
      ;;
    --evidence-dir)
      KYVERNO_EVIDENCE_DIR_VALUE="${2-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v kind >/dev/null 2>&1; then
  echo "kind binary not found in PATH. Install from https://kind.sigs.k8s.io/docs/user/quick-start/" >&2
  exit 1
fi

if ! command -v make >/dev/null 2>&1; then
  echo "make binary not found in PATH." >&2
  exit 1
fi

CREATED_CLUSTER=false

if cluster_exists; then
  log "Re-using existing kind cluster '${CLUSTER_NAME}'"
else
  log "Creating kind cluster '${CLUSTER_NAME}'"
  kind create cluster --name "${CLUSTER_NAME}"
  CREATED_CLUSTER=true
fi

KUBECTL_CONTEXT="kind-${CLUSTER_NAME}"
export KUBECTL_CONTEXT
log "Using kube-context ${KUBECTL_CONTEXT}"

if [[ -n "$KYVERNO_DEPLOY_FLAGS_VALUE" ]]; then
  export KYVERNO_DEPLOY_FLAGS="${KYVERNO_DEPLOY_FLAGS_VALUE}"
fi
if [[ -n "$KYVERNO_VERIFY_FLAGS_VALUE" ]]; then
  export KYVERNO_VERIFY_FLAGS="${KYVERNO_VERIFY_FLAGS_VALUE}"
fi
if [[ -n "$KYVERNO_EVIDENCE_DIR_VALUE" ]]; then
  export KYVERNO_EVIDENCE_DIR="${KYVERNO_EVIDENCE_DIR_VALUE}"
fi

cleanup() {
  if [[ "$KEEP_CLUSTER" == true ]]; then
    log "Keeping kind cluster '${CLUSTER_NAME}' (requested)"
    return
  fi
  if [[ "$CREATED_CLUSTER" == true ]]; then
    delete_cluster
  else
    log "Skipping cluster deletion (cluster existed before script execution)"
  fi
}

trap cleanup EXIT

log "Running make kyverno/deploy"
make -C "${REPO_ROOT}" kyverno/deploy

log "Running make kyverno/verify"
make -C "${REPO_ROOT}" kyverno/verify

log "Kyverno deploy and verify steps completed successfully"
