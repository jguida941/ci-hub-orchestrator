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

## Monitoring
- Rekor inclusion proofs verified post-release.
- Rekor monitor job stores proofs under `artifacts/evidence/` for audit.
