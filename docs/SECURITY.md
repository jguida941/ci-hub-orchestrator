# Security Overview

- Authentication: GitHub OIDC with issuer/subject allowlists (policies/issuer_subject.rego).
- Authorization: GitHub Rulesets enforce signed commits/tags, CODEOWNERS approvals, required checks.
- Secrets: CI pipelines operate secretless via OIDC; non-OIDC credentials are denied.
- Supply chain: cosign keyless signing, SLSA v1.0 provenance, OCI referrers, Kyverno admission policies.
- Storage: WORM buckets with least-privilege IAM and signed URLs (short TTL).
- Monitoring: Rekor inclusion proofs archived; Kyverno deny-by-default ensures gating.
