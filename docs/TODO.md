# Implementation TODOs

This project now has real scripts and policies, but several items still need environment-specific values or production integrations:

- `.github/workflows/release.yml`
  - Provide a real Dockerfile and build context for the application.
  - Set `REGISTRY_USERNAME`/`REGISTRY_PASSWORD` secrets; adjust `REGISTRY`/`IMAGE_NAME` if not using GHCR.
  - Provide a command to fetch the generated SLSA provenance JSON path (currently assumes `artifacts/slsa-provenance.json`).
  - Replace temporary installs with pinned versions and cache where appropriate.
  - Populate `fixtures/supply_chain/vex_exemptions.json` (or wire it to your vulnerability management system) so the generated VEX statements reflect real approvals from your org.

- `tools/publish_referrers.sh`
  - Confirm oras and cosign versions; adjust to your registries (GHCR, ECR, ACR, etc.).
  - Extend to also upload VEX JSON if available.

- `tools/rekor_monitor.sh`
  - Supply real Rekor log URL if using a private instance.
  - Connect to alerting (Slack, PagerDuty) after proof capture.

- Rego policies (`policies/*.rego`)
  - Tune `allowed_issuer_regex`, `allowed_subject_regex`, CVSS/EPSS thresholds.
  - Add additional policy rules (digest allowlists, SBOM completeness) as needed.

- `schema/registry.json`
  - Keep ownership + compatibility metadata current when new schema versions ship.

- `config/runner-isolation.yaml`
  - Connect to the real Firecracker/gVisor orchestration layer, populate Vault role IDs,
    and pipe runner queue metrics into Prometheus alerts.

- Canary evidence (`scripts/capture_canary_decision.py`)
  - Replace the sample SQL with your production Prometheus/SQL query and point
    `--metrics-uri` at the live Grafana/Looker dashboard once it’s available.

- Determinism + DR scripts (`tools/determinism_check.sh`, `data-quality-and-dr/dr_recall.sh`)
  - Extend new cross-arch/time manifest checks into full rebuild parity runs and finish DR recall automation.

- dbt tests (`models/tests/data_quality.yml`)
  - Adjust model names, freshness thresholds, and null-rate limits to match your warehouse.

- `docs/SUPPLY_CHAIN.md`, `docs/SECURITY.md`, `docs/DR_RUNBOOK.md`
  - Fill in actual registry names, bucket names, IAM roles, and SOC2/ISO control mappings.

No tooling in this repo requires paid services beyond the infrastructure you already operate. Sigstore (cosign/Fulcio/Rekor) and GitHub Actions are free at the OSS tier; oras, Syft, and OPA are open-source. You only incur costs from your chosen container registry, compute for builds, and storage—same as any deployment.
