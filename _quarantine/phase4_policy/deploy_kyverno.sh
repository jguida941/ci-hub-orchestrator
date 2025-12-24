#!/usr/bin/env bash
# Deploy Kyverno controllers and apply repository policies in Enforce mode.
# Requires kubectl credentials for the target cluster.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_VERSION="v1.12.5"
DEFAULT_INSTALL_URL="https://github.com/kyverno/kyverno/releases/download/${DEFAULT_VERSION}/install.yaml"
DEFAULT_INSTALL_MANIFEST="${REPO_ROOT}/deploy/kyverno/install.yaml"
# By default prefer the remote Kyverno manifest; set KYVERNO_USE_LOCAL_MANIFEST=true to force the vendored file.
USE_LOCAL_MANIFEST="${KYVERNO_USE_LOCAL_MANIFEST:-false}"
DEFAULT_KUSTOMIZE_DIR="${REPO_ROOT}/deploy/kyverno"
DEFAULT_POLICY_DIR="${REPO_ROOT}/policies/kyverno"

KUBE_CONTEXT="${KUBECTL_CONTEXT:-}"
KYVERNO_NAMESPACE="kyverno"
INSTALL_SOURCE=""
WAIT_TIMEOUT=240
WAIT_FOR_READY=true
SKIP_INSTALL=false
SKIP_POLICIES=false
KUSTOMIZE_DIR="$DEFAULT_KUSTOMIZE_DIR"
POLICY_DIR="$DEFAULT_POLICY_DIR"

usage() {
  cat <<'USAGE'
Usage: scripts/deploy_kyverno.sh [options]

Options:
  --context <name>         kube-context to operate against (otherwise read KUBECTL_CONTEXT)
  --namespace <name>       Namespace hosting Kyverno controllers (default: kyverno)
  --install-url <url>      Kyverno install manifest URL (overrides --version)
  --version <vX.Y.Z>       Kyverno release version to install (default: v1.12.5)
  --kustomize-dir <path>   Path to policy kustomization (default: deploy/kyverno)
  --policy-dir <path>      Path to raw policy YAML (default: policies/kyverno) for sanity checks
  --skip-install           Do not apply the Kyverno controller manifest
  --skip-policies          Skip policy rollout (install controllers only)
  --wait-timeout <sec>     Seconds to wait for controller readiness (default: 240)
  --no-wait                Do not wait for Kyverno deployments to become Ready
  -h, --help               Show this message

Examples:
  scripts/deploy_kyverno.sh --context kind-kyverno-ci
  scripts/deploy_kyverno.sh --context prod --skip-install
  scripts/deploy_kyverno.sh --context prod --install-url https://mirror.example.com/kyverno.yaml
USAGE
}

log() {
  echo "[deploy-kyverno] $*" >&2
}

render_kustomize() {
  if command -v kubectl >/dev/null 2>&1 && kubectl kustomize --help >/dev/null 2>&1; then
    kubectl kustomize "$KUSTOMIZE_DIR"
  elif command -v kustomize >/dev/null 2>&1; then
    kustomize build "$KUSTOMIZE_DIR"
  else
    echo "Neither 'kubectl kustomize' nor 'kustomize' binary found in PATH" >&2
    return 1
  fi
}

check_enforce_mode() {
  local manifest_file="$1"
  local invalid
  invalid=$(grep -nE 'validationFailureAction:[[:space:]]*(Audit|AuditChangeRequest|Warn|DryRun|None)' "$manifest_file" || true)
  if [[ -n "$invalid" ]]; then
    echo "Detected non-Enforce validationFailureAction values:" >&2
    echo "$invalid" >&2
    return 1
  fi
  if ! grep -qE 'validationFailureAction:[[:space:]]*Enforce' "$manifest_file"; then
    echo "Rendered policies do not contain validationFailureAction: Enforce" >&2
    return 1
  fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --context)
      KUBE_CONTEXT="${2-}"
      shift 2
      ;;
    --namespace)
      KYVERNO_NAMESPACE="${2-}"
      shift 2
      ;;
    --install-url)
      INSTALL_SOURCE="${2-}"
      shift 2
      ;;
    --version)
      VERSION="${2-}"
      INSTALL_SOURCE="https://github.com/kyverno/kyverno/releases/download/${VERSION}/install.yaml"
      shift 2
      ;;
    --kustomize-dir)
      KUSTOMIZE_DIR="$(cd "${2-}" && pwd)"
      shift 2
      ;;
    --policy-dir)
      POLICY_DIR="$(cd "${2-}" && pwd)"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=true
      shift
      ;;
    --skip-policies)
      SKIP_POLICIES=true
      shift
      ;;
    --wait-timeout)
      WAIT_TIMEOUT="${2-}"
      shift 2
      ;;
    --no-wait)
      WAIT_FOR_READY=false
      shift
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

if [[ -z "$KUBE_CONTEXT" ]]; then
  echo "KUBECTL_CONTEXT environment variable or --context flag is required" >&2
  exit 1
fi

if [[ -z "$INSTALL_SOURCE" ]]; then
  if [[ "$USE_LOCAL_MANIFEST" == "true" && -s "$DEFAULT_INSTALL_MANIFEST" ]]; then
    INSTALL_SOURCE="$DEFAULT_INSTALL_MANIFEST"
  else
    INSTALL_SOURCE="$DEFAULT_INSTALL_URL"
  fi
fi

if [[ ! -d "$POLICY_DIR" ]]; then
  echo "Policy directory not found: $POLICY_DIR" >&2
  exit 1
fi

if [[ ! -d "$KUSTOMIZE_DIR" ]]; then
  echo "Kustomize directory not found: $KUSTOMIZE_DIR" >&2
  exit 1
fi

KUBECTL_BIN="${KUBECTL_BIN:-kubectl}"
if ! command -v "$KUBECTL_BIN" >/dev/null 2>&1; then
  echo "kubectl binary not found (checked ${KUBECTL_BIN})" >&2
  exit 1
fi

kubectl_cmd() {
  "$KUBECTL_BIN" --context "$KUBE_CONTEXT" "$@"
}

log "Using kube-context ${KUBE_CONTEXT}"

if ! kubectl_cmd auth can-i apply clusterpolicies.kyverno.io >/dev/null 2>&1; then
  log "Warning: current identity may not be able to apply ClusterPolicies (auth can-i failed)"
fi

if [[ "$SKIP_INSTALL" == false ]]; then
  if [[ "$INSTALL_SOURCE" =~ ^https?:// ]]; then
    log "Installing Kyverno controllers from ${INSTALL_SOURCE}"
  else
    if [[ ! -f "$INSTALL_SOURCE" ]]; then
      echo "Kyverno manifest not found at ${INSTALL_SOURCE}" >&2
      exit 1
    fi
    log "Installing Kyverno controllers from local manifest ${INSTALL_SOURCE}"
  fi
  kubectl_cmd apply -f "$INSTALL_SOURCE"

  if $WAIT_FOR_READY; then
    log "Waiting up to ${WAIT_TIMEOUT}s for Kyverno deployments in namespace ${KYVERNO_NAMESPACE}"
    mapfile -t deployments < <(kubectl_cmd -n "$KYVERNO_NAMESPACE" get deploy -o name 2>/dev/null || true)
    if [[ ${#deployments[@]} -eq 0 ]]; then
      log "No deployments detected in namespace ${KYVERNO_NAMESPACE}; skipping readiness wait"
    else
      for deploy in "${deployments[@]}"; do
        kubectl_cmd -n "$KYVERNO_NAMESPACE" rollout status "$deploy" --timeout="${WAIT_TIMEOUT}s"
      done
    fi
  fi
else
  log "Skipping Kyverno controller installation (--skip-install)"
fi

if [[ "$SKIP_POLICIES" == true ]]; then
  log "Skipping policy rollout (--skip-policies)"
  exit 0
fi

if [[ ! -f "${POLICY_DIR}/verify-images.yaml" ]]; then
  log "Warning: ${POLICY_DIR} does not appear to contain repository policies; continuing"
fi

POLICY_MANIFEST="$(mktemp)"
trap 'rm -f "$POLICY_MANIFEST"' EXIT

log "Rendering policy kustomization from ${KUSTOMIZE_DIR}"
if ! render_kustomize >"$POLICY_MANIFEST"; then
  echo "Failed to render kustomize output from ${KUSTOMIZE_DIR}" >&2
  exit 1
fi

log "Ensuring policies remain in validationFailureAction=Enforce"
check_enforce_mode "$POLICY_MANIFEST"

log "Performing server-side dry run for policy bundle"
kubectl_cmd apply --dry-run=server -f "$POLICY_MANIFEST" >/dev/null

log "Applying policy bundle"
kubectl_cmd apply -f "$POLICY_MANIFEST"

log "Kyverno deployment complete."
