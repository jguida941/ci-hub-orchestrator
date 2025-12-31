# Kyverno Policies for Kubernetes Admission Control

The CI/CD Hub includes **optional** Kyverno policies for organizations deploying to Kubernetes. These policies extend the hub's security posture from build-time (GitHub Actions) to deploy-time (K8s admission control).

---

## Quick Start

### 1. Install Kyverno in Your Cluster

```bash
kubectl create -f https://github.com/kyverno/kyverno/releases/download/v1.11.4/install.yaml
```

### 2. Apply Policies

```bash
# Apply all policies in Audit mode (warnings only)
kubectl apply -f policies/kyverno/

# Or apply specific policies
kubectl apply -f policies/kyverno/block-pull-request-target.yaml
```

### 3. Check Policy Status

```bash
kubectl get clusterpolicies
```

---

## Available Policies

| Policy | Purpose | Default Mode | Severity |
|--------|---------|--------------|----------|
| `block-pull-request-target` | Block dangerous GHA trigger in ConfigMaps | Enforce | High |
| `require-referrers` | Require SBOM/provenance annotations | Audit | Medium |
| `secretless` | Block secrets as env vars, enforce OIDC | Audit | Medium |
| `verify-images` | Verify Cosign keyless signatures | Audit | High |

---

## Policy Details

### block-pull-request-target

**Purpose:** Prevents ConfigMaps containing GitHub Actions workflows from using the dangerous `pull_request_target` trigger.

**Why it matters:** The `pull_request_target` trigger runs with repository secrets and write access, enabling attackers to steal secrets via malicious PRs.

**Default:** `Enforce` (blocking) - Critical security control.

```yaml
# Blocks any workflow-* ConfigMap containing pull_request_target
spec:
  validationFailureAction: Enforce
  rules:
    - name: check-workflow-triggers
      match:
        resources:
          kinds: [ConfigMap]
          names: ["workflow-*"]
```

### require-referrers

**Purpose:** Ensures container images have SBOM and provenance attestations attached.

**Why it matters:** Supply chain security requires knowing what's in your images and how they were built.

**Default:** `Audit` (warning) - Allows adoption without breaking deployments.

### secretless

**Purpose:** Blocks pods from using secrets as environment variables.

**Why it matters:** Secrets in env vars are easily logged, leaked, and harder to rotate. Use mounted secrets or external secret managers instead.

**Default:** `Audit` (warning) - Allows exceptions during migration.

**Opt-out:** Add label `allow-secret-env: "true"` to pods that need exceptions.

### verify-images

**Purpose:** Requires container images to be signed with Cosign keyless signatures.

**Why it matters:** Ensures only trusted images from your CI/CD pipeline can be deployed.

**Default:** `Audit` (warning) - Requires customization before enforcement.

**Customization required:**
- Replace `YOUR_ORG` with your GitHub org
- Update image registry pattern

---

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `Audit` | Log warnings only | Initial rollout, testing |
| `Enforce` | Block non-compliant resources | Production enforcement |

### Upgrading to Enforce

1. Apply in Audit mode first
2. Review policy violations: `kubectl get policyreports -A`
3. Fix violations or add exceptions
4. Update policy: `validationFailureAction: Enforce`
5. Re-apply: `kubectl apply -f policies/kyverno/`

---

## Customization

### Using Templates

Copy templates and customize for your organization:

```bash
cp templates/kyverno/verify-images-template.yaml policies/kyverno/verify-images.yaml
```

Edit placeholders:
- `YOUR_ORG` - Your GitHub organization
- `your-registry.io` - Your container registry
- Namespace exclusions

### Adding Namespace Exceptions

```yaml
spec:
  rules:
    - name: example
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - monitoring
                - your-exception-namespace
```

### Adding Label-Based Exceptions

```yaml
spec:
  rules:
    - name: example
      exclude:
        any:
          - resources:
              selector:
                matchLabels:
                  skip-policy: "true"
```

---

## Validation Without a Cluster

Use the Kyverno CLI to validate policies locally:

```bash
# Install Kyverno CLI
brew install kyverno  # macOS
# Or download from releases

# Validate policy syntax
kyverno validate policies/kyverno/block-pull-request-target.yaml

# Test policy against a resource
kyverno apply policies/kyverno/secretless.yaml -r test-pod.yaml
```

The hub includes a validation workflow (`.github/workflows/kyverno-validate.yml`) that runs on policy file changes.

---

## Integration with CI/CD Hub

### Build-Time vs Deploy-Time

| Stage | Tool | Coverage |
|-------|------|----------|
| Build | Trivy, Semgrep, OWASP DC | Vulnerabilities in code/deps |
| Build | Cosign (via GHA) | Image signing |
| Deploy | Kyverno | Admission control |

### Recommended Pipeline

```
Code Push → Hub CI (testing, scanning) → Build Image → Sign with Cosign → Push to Registry
                                                                              ↓
                                                         Kyverno verifies signature at deploy time
```

---

## Troubleshooting

### Policy Not Applying

```bash
# Check policy status
kubectl get clusterpolicies block-pull-request-target -o yaml

# Check for admission webhook errors
kubectl logs -n kyverno -l app.kubernetes.io/component=admission-controller
```

### Too Many Violations

Start with `Audit` mode and fix issues before moving to `Enforce`.

### Policy Reports

```bash
# View policy violations
kubectl get policyreports -A

# Detailed report for a namespace
kubectl describe policyreport -n your-namespace
```

---

## Related Documentation

- [ADR-0012: Kyverno Policies](../adr/0012-kyverno-policies.md) - Decision rationale
- [Kyverno Documentation](https://kyverno.io/docs/) - Official docs
- [GitHub Actions Security: pull_request_target](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/) - The vulnerability `block-pull-request-target` prevents
- [Cosign Keyless Signing](https://docs.sigstore.dev/cosign/signing/overview/) - For `verify-images` policy
