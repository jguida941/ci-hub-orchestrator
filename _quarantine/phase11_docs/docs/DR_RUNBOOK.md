# Disaster Recovery Runbook

## Objectives

- **RPO:** ≤ 60 seconds

- **RTO:** ≤ 300 seconds

## Artifact Storage Controls

- Enable WORM (Write Once Read Many) with retention locks on artifact/log buckets.

- Configure cross-region replication to secondary region.

- Restrict access via least-privilege IAM roles and short-lived signed URLs.

## Recall Drill Procedure

1. Retrieve latest SLSA provenance and SBOM referrers for the release.

2. Execute `data-quality-and-dr/dr_recall.sh` with provenance + SBOM; capture output.

3. Rebuild release artifacts using pinned toolchain/environment hash.

4. Compare digests and BUILD_ID values; record diff report in Evidence Bundle.

5. File postmortem if differences detected.

## Ingesting Drill Evidence

- Run the ingest helper after each scheduled drill to push NDJSON into BigQuery:

  ```bash
  python ingest/chaos_dr_ingest.py \
    --project <gcp-project> \
    --dataset ci_intel \
    --dr-ndjson artifacts/evidence/dr/events.ndjson \
    --dr-run-id "$(date -u +dr-%Y%m%dT%H%M%SZ)"
  ```

- Add `--chaos-ndjson artifacts/evidence/chaos/events.ndjson` when a chaos trial and DR drill run together.

- Use `--dry-run` first in lower environments; production runs must retain job logs with the generated `load_id`.

## Monitoring

- Rekor inclusion proofs verified post-release.

- Rekor monitor job stores proofs under `artifacts/evidence/` for audit.

## Automation gate outputs

- `tools/run_dr_drill.py` enforces manifest policy limits. It exits non-zero when observed RPO/RTO breach `policies.{max_rpo_minutes,max_rto_seconds}` and prints a `[dr-drill] PASS: RTO=… RPO=…` summary on success.
- Each drill writes `artifacts/evidence/dr/manifest.sha256` so auditors can confirm the exact manifest used to execute the drill.
