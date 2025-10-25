# Supply Chain Enforcement

This directory collects artifacts for the `supply-chain-enforce/` implementation:

- `kyverno/` contains admission control policies enforcing digest allowlists, provenance, and SBOM referrers. `verify-images.yaml` ships a ready-to-apply ClusterPolicy for `ghcr.io/jguida941/ci-intel-app` that verifies the Sigstore keyless signature (`release.yml`), Rekor inclusion, and the SLSA+SPDX+CycloneDX referrers published by `tools/publish_referrers.sh`.
- `../policies/*.rego` provides OPA evaluators used in CI/CD gates.
- `tools/publish_referrers.sh` publishes CycloneDX/SPDX SBOMs and SLSA provenance as OCI 1.1 referrers and signs them with cosign.
- `tools/rekor_monitor.sh` captures Rekor inclusion proofs for Evidence Bundles.

The release workflow in `.github/workflows/release.yml` demonstrates how these components integrate during tag pushes.
