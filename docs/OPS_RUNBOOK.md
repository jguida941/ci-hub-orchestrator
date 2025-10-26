# Operations Runbook

## Apply Kyverno Supply-Chain Policy

### Prerequisites

- Kubernetes cluster (v1.26+) with Kyverno (v1.10+) installed and webhooks healthy: `kubectl get pods -n kyverno`.

- Cluster admins granted `ClusterPolicy` write access.

- GitHub Actions release workflow publishing signed images, SBOM/VEX/provenance referrers, and Rekor proofs (see `.github/workflows/release.yml` + `tools/publish_referrers.sh`).

- `supply-chain-enforce/kyverno/verify-images.yaml` synced to the desired branch.

### Deployment Steps

1. Confirm the target namespaces (`dev`, `staging`, `prod` by default) exist or update the manifest to match your environments.

2. Point `kubectl` to the prod control plane and dry‑run the policy:

   ```bash
   kubectl apply -f supply-chain-enforce/kyverno/verify-images.yaml --server-side --dry-run=server
   ```

3. Apply for real (records change in managed git repo or change-management ticket):

   ```bash
   kubectl apply -f supply-chain-enforce/kyverno/verify-images.yaml --server-side --force-conflicts
   ```

4. Verify status:

   ```bash
   kubectl get clusterpolicy verify-ci-intel-supply-chain -o yaml
   kyverno apply supply-chain-enforce/kyverno/verify-images.yaml --resource test/manifests/ci-intel-app.yaml
   ```

   The Kyverno CLI test ensures signed images plus SLSA/SPDX/CycloneDX referrers from the release workflow satisfy the policy.

### Observability & Evidence

- Release jobs upload Rekor inclusion proofs in `artifacts/evidence/rekor-proof-*.json`; reference them when auditing Kyverno decisions.

- GitOps promotion PRs must include links to the SBOM/VEX/provenance artifacts so operators can prove compliance before flipping traffic.

- Use `kubectl get events -A | grep kyverno` to spot denies; the offending workload’s `image:` will reference a tag without required attestations.

### Rollback / Disable

1. Document why the policy must be relaxed (e.g., emergency hotfix) and get product/security approval.

2. Either patch the policy to add a temporary namespace allowlist:

   ```bash
   kubectl patch clusterpolicy verify-ci-intel-supply-chain \
     --type merge \
     -p '{"spec":{"rules":[{"name":"verify-ci-intel-signature-and-attestations","match":{"any":[{"resources":{"namespaces":["dev","staging","prod","hotfix"]}}]}}]}}'
   ```

   or delete the policy entirely as a last resort:

   ```bash
   kubectl delete clusterpolicy verify-ci-intel-supply-chain
   ```

3. Capture the change in the ops log/runbook with timestamps, git SHAs, and planned re‑enable time. CI must remain blocked on supply-chain policies before resuming normal deploys.

### Post-Deployment Checklist

- Trigger the release workflow once to ensure new digests still satisfy the policy.

- Watch Kyverno metrics (`kyverno_policy_status{policy="verify-ci-intel-supply-chain"}`) for at least one deploy cycle.

- Update this runbook if namespaces, registries, or attestation requirements change.
