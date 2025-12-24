# ADR-0001: Supply-Chain Trust Boundary & Evidence Bundle
Status: Accepted
Date: 2025-11-02
Owners: Platform team

## Context
The hub asserts SLSA-aligned guarantees (pinned GitHub Actions, cosign/Rekor signing, SBOM/VEX referrers, determinism harness) and publishes an evidence bundle. These controls are described in `README.md`, `plan.md`, and `docs/status/honest-status.md`, but were not captured as an explicit decision with scope and expectations.

## Decision
- CI must run on SHA-pinned actions with least-privilege permissions and OIDC-only credentials.
- Release workflows emit SBOM (SPDX/CycloneDX), VEX, SLSA provenance, signatures, and Rekor proofs; artifacts are gathered into an evidence bundle that is signed and stored under `artifacts/evidence/`.
- OCI referrers (SBOM/VEX/provenance) must exist for promoted digests before deploy. Rekor inclusion proof is required.
- Tooling downloads are checksum-verified; caches are signed and quarantined on mismatch.

## Consequences
- Promotion gates depend on cosign/rekor availability; outages block releases until attestations can be verified.
- Evidence bundle paths and required artifacts must stay stable; schema/tests for evidence inputs must be maintained.
- Any new workflow/tooling must integrate with the pinned-action + checksum posture or document an exception with a follow-up issue.

## References
- README.md (Security boundaries & claims)
- plan.md (Phase 1 outcomes, gap tracker)
- docs/status/honest-status.md
- tools/build_vuln_input/, tools/rekor_monitor.sh, tools/verify_rekor_proof.py
