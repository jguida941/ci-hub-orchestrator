# Data Files

This directory holds small, versioned fixtures that tests and demos consume. Larger/generated artifacts live under `artifacts/`.

## Fixtures
- `multi.jsonl`: Sample NDJSON feed used by analytics/unit tests.
- `test.jsonl`: Minimal NDJSON fixture for parser smoke tests.
- `dr/backup.json`, `dr/manifest.json`, `dr/provenance.json`, `dr/sbom.json`: DR recovery bundle inputs; referenced by `data-quality-and-dr/dr_recall.sh` and DR runbook drills.
- `artifacts/dr/restore/*`: Example recovered backups and checksums produced by `data-quality-and-dr/dr_recall.sh`.

## Guidance
- Keep new JSON/NDJSON fixtures here (or under `fixtures/` if they are test-only) to avoid polluting the repo root.
- Treat files under `artifacts/` as generated evidence; refresh them via the scripts that produce them rather than hand-editing.

## Changelog
- 2025-11-21: Documented DR/provenance fixtures and the generated restore outputs.
- 2025-10-26: Initialized data directory.
