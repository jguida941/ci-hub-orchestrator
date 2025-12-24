# Supply Chain Controls

## Signing & Provenance

- Builds use keyless cosign signing and emit SLSA v1.0 provenance. Tooling installs are pinned and checksum-verified via `scripts/install_tools.sh` (oras 1.2.0, cosign v2.2.4, rekor-cli v1.4.0, syft 1.18.0, grype 0.102.0, crane v0.19.2).

- `tools/publish_referrers.sh` uploads CycloneDX/SPDX SBOMs and provenance as OCI 1.1 referrers and signs them.

## Rekor Monitoring

- `tools/rekor_monitor.sh` captures inclusion proofs for each release digest.

- Proofs are added to Evidence Bundles for auditability.

## Admission Policies

- `supply-chain-enforce/kyverno/verify-images.yaml` enforces digest allowlists, provenance, and SBOM referrers with deny-by-default.

- OPA policies (`policies/*.rego`) run in CI and admission to ensure issuer/subject allowlists and VEX coverage.

- `tools/build_issuer_subject_input.py` verifies the cosign signature for each release image and materializes the issuer/subject payload consumed by `policies/issuer_subject.rego`.

## Referrer Presence Gate

- Release workflow attaches SPDX, CycloneDX, VEX, and SLSA provenance as OCI 1.1 referrers and asserts their presence with `oras discover --format json`.

## SBOM + VEX Policy Feed

- `build-sign-publish` now generates a CycloneDX VEX document via `tools/generate_vex.py`, sourced from `fixtures/supply_chain/vex_exemptions.json`, and stores it with the SBOM artifacts so it can be published as an OCI referrer.

- `policy-gates` downloads the CycloneDX SBOM, scans it with Grype, and runs `tools/build_vuln_input.py` to emit `policy-inputs/vulnerabilities.json`. Any VEX file found in the SBOM bundle (for example `app.vex.json`) is ingested automatically so documented `not_affected` findings satisfy `policies/sbom_vex.rego`.

## Determinism Evidence

- After publishing the image, the release workflow runs `tools/determinism_check.sh` against the immutable digest to capture the raw OCI manifest, a SHA256 over that manifest, and environment metadata. The resulting files live under `artifacts/evidence/determinism/` and prove what was pushed without relying on mutable tags.

## Base Image SLO

## Verification checklist

- `crane digest ghcr.io/<owner>/<image>:<tag>` ⇒ digest matches the release evidence (`tag-digest.txt`).
- `docker buildx imagetools inspect <digest>` ⇒ output contains `linux/amd64` and `linux/arm64` (`manifest.txt`).
- `cosign verify --certificate-oidc-issuer-regexp 'https://token.actions.githubusercontent.com' <digest>` then `cosign download signature|certificate|chain <digest>` ⇒ `artifacts/evidence/cosign-signature.sig`, `cosign-cert.pem`, and `cosign-cert-chain.pem` exist and are non-empty.
- `cosign verify-attestation --type slsaprovenance <digest>` ⇒ attestation subject digest matches the image.
- `oras discover --format json <digest>` ⇒ descriptors/manifests include `application/spdx+json`, `application/vnd.cyclonedx+json`, and `application/vnd.in-toto+json` (`referrers.json`).
- `rekor-cli get --log-index <index>` ⇒ log entry includes the image digest and matches `rekor-entry-*.json`.

- Builds fail when base images introduce critical CVEs without VEX "not affected" evidence.
