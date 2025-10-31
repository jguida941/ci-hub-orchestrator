# Security Overview

- Authentication: GitHub OIDC with issuer/subject allowlists (policies/issuer_subject.rego).

- Authorization: GitHub Rulesets enforce signed commits/tags, CODEOWNERS approvals, required checks.

- Secrets: CI pipelines operate secretless via OIDC; non-OIDC credentials are denied.

- Supply chain: cosign keyless signing with certificate/chain capture, tagged digest locks via crane, SLSA v1.0 provenance, OCI referrers validated with `oras discover`, Rekor transparency (`rekor-cli get` + `tools/verify_rekor_proof.py`), and Kyverno admission policies.

- Storage: WORM buckets with least-privilege IAM and signed URLs (short TTL).

- Monitoring: Rekor inclusion proofs archived; Kyverno deny-by-default ensures gating.
