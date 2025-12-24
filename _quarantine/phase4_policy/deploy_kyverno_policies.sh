#!/bin/bash
set -euo pipefail

# Deploy Kyverno policies to production cluster
# This script applies all policies from policies/kyverno/ with validation

POLICY_DIR="policies/kyverno"
NAMESPACE="${KYVERNO_NAMESPACE:-kyverno}"

echo "=== Kyverno Policy Deployment ==="
echo "Namespace: $NAMESPACE"
echo "Policy directory: $POLICY_DIR"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH" >&2
    exit 1
fi

# Check if Kyverno is installed
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "Error: Kyverno namespace '$NAMESPACE' not found. Please install Kyverno first." >&2
    echo "Installation guide: https://kyverno.io/docs/installation/" >&2
    exit 1
fi

# Check if Kyverno CRDs are installed
if ! kubectl get crd clusterpolicies.kyverno.io &> /dev/null; then
    echo "Error: Kyverno CRDs not found. Please install Kyverno first." >&2
    exit 1
fi

# Validate all policies before applying
echo ""
echo "=== Validating policies ==="
for policy in "$POLICY_DIR"/*.yaml; do
    if [[ -f "$policy" ]]; then
        policy_name=$(basename "$policy")
        echo -n "  Validating $policy_name... "

        # Dry-run to validate the policy
        if kubectl apply --dry-run=client -f "$policy" &> /dev/null; then
            echo "✅ Valid"
        else
            echo "❌ Invalid"
            echo "Error: Policy validation failed for $policy_name" >&2
            kubectl apply --dry-run=client -f "$policy" 2>&1 | sed 's/^/    /'
            exit 1
        fi
    fi
done

# Apply all policies
echo ""
echo "=== Applying policies ==="
applied_count=0
for policy in "$POLICY_DIR"/*.yaml; do
    if [[ -f "$policy" ]]; then
        policy_name=$(basename "$policy")
        echo -n "  Applying $policy_name... "

        if kubectl apply -f "$policy"; then
            echo "✅ Applied"
            ((applied_count++))
        else
            echo "❌ Failed"
            echo "Error: Failed to apply $policy_name" >&2
            exit 1
        fi
    fi
done

# Verify policies are active
echo ""
echo "=== Verifying policy status ==="
kubectl get clusterpolicies -n "$NAMESPACE" -o wide

echo ""
echo "=== Summary ==="
echo "✅ Successfully deployed $applied_count Kyverno policies"
echo ""
echo "Policies are now active in Enforce mode. They will:"
echo "  • Verify container image signatures"
echo "  • Require OCI referrers for SBOM/provenance"
echo "  • Block secretKeyRef usage (secretless enforcement)"
echo "  • Block dangerous pull_request_target workflow triggers"
echo ""
echo "To test policies: ./scripts/test_kyverno_policies.py"
echo "To verify enforcement: ./scripts/verify_kyverno_enforcement.sh"