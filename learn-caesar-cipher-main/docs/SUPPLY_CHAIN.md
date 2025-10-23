# Supply Chain Controls

## Signing & Provenance
- Builds use keyless cosign signing and emit SLSA v1.0 provenance.
- `tools/publish_referrers.sh` uploads CycloneDX/SPDX SBOMs and provenance as OCI 1.1 referrers and signs them.

## Rekor Monitoring
- `tools/rekor_monitor.sh` captures inclusion proofs for each release digest.
- Proofs are added to Evidence Bundles for auditability.

## Admission Policies
- `supply-chain-enforce/kyverno/verify-images.yaml` enforces digest allowlists, provenance, and SBOM referrers with deny-by-default.
- OPA policies (`policies/*.rego`) run in CI and admission to ensure issuer/subject allowlists and VEX coverage.

## Referrer Presence Gate
- Release workflow verifies required referrers (SPDX, CycloneDX, SLSA) via OPA before promotion.

## Base Image SLO
- Builds fail when base images introduce critical CVEs without VEX "not affected" evidence.
