# DR Drill Orchestrator

## Purpose

Exercise the full disaster-recovery restore path: verify backup integrity, validate SBOM + provenance, run the recall script, and gate on RPO/RTO objectives while emitting auditable evidence.

## Manifest-Driven Execution

The drill is parameterised by `data/dr/manifest.json`. The manifest pins:

- Backup artifact path, digest, and capture timestamp.
- SBOM and provenance locations aligned with the backup digest.
- Restore configuration (output directory, recall script, whether to copy the backup before executing the script).
- Policy thresholds (`max_rpo_minutes`, `max_rto_seconds`).

## CLI Usage

```bash
python tools/run_dr_drill.py \
  --manifest data/dr/manifest.json \
  --output artifacts/dr/dr-report.json \
  --ndjson artifacts/dr/dr-events.ndjson \
  --evidence-dir artifacts/dr
```

Optional flags:

- `--current-time` – override the clock (ISO-8601) to make policy tests deterministic.

## Drill Flow

1. Verify the backup digest and JSON payload (all services must be `ready`).
2. Validate SBOM structure and provenance envelopes for the expected digest.
3. Run the restore pipeline (`data-quality-and-dr/dr_recall.sh`) and ensure the recovered artifact matches the source digest.
4. Enforce RPO/RTO policies and record the measured metrics.

Each stage emits structured events (start/end timestamps, status, context). Failures propagate as `DrDrillError` / `PolicyViolation` exceptions, causing the workflow to fail.

## Evidence Outputs

- `dr-report.json` (`schema=dr_drill.v2`) – run metadata and metrics.
- `dr-events.ndjson` – step-by-step event log for telemetry ingestion.
- `drill-metrics.json` – copy of the report stored under the evidence directory for quick inspection.
- `restore/` – recovered artifacts, digests, and restore logs from the recall script.

## Workflows

`.github/workflows/dr-drill.yml` runs weekly (and via manual dispatch), surfaces the metrics via `jq`, and uploads the evidence bundle. The release pipeline (`.github/workflows/release.yml`) gates production by rerunning the drill and refusing releases when the RPO/RTO checks fail.

## Tests

`pytest tools/tests/test_dr_drill.py` covers manifest parsing, digest/SBOM/provenance validation, restore behaviour, and the policy gate.

## Dependencies

- Python 3.12+
- Standard library + existing `tools.provenance_io` helpers.

## License

See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md)
