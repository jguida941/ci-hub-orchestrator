# Policy Bundle

This directory houses the enforcement packs consumed by the CI Intelligence Hub.

- `*.rego` — OPA policies invoked by the policy-gates workflow.
- `kyverno/` — Cluster policies enforced server-side to guarantee admission control.
- `tests/` — Unit tests for the Rego bundles (Kyverno policies rely on integration tests).

## Kyverno policies

| File | Purpose |
| --- | --- |
| `kyverno/verify-images.yaml` | Deny workloads unless container images are signed via Cosign keyless (GitHub OIDC issuer + Rekor). |
| `kyverno/require-referrers.yaml` | Require OCI referrer annotations for SBOM + provenance artifacts on Pods and Pod templates. |
| `kyverno/secretless.yaml` | Block Pods/controllers that attempt to consume `secretKeyRef` env vars or secret-backed volumes unless explicitly labeled for an exception. |

Static fixtures under `fixtures/kyverno/` provide green/red workloads for CI. The `scripts/test_kyverno_policies.py` helper exercises these policies and the pytest suite (`tools/tests/test_kyverno_policy_checker.py`) treats the red fixtures as the “documented failing path”.
