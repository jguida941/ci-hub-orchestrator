# Testing Matrix

| Suite | Command | Runs In | Notes |
| --- | --- | --- | --- |
| Tooling unit tests | `pytest tools/tests` | `tools-ci.yml`, local | Covers mutation observatory helpers, cache sentinel, provenance utilities. |
| Schema validation | `python scripts/check_schema_registry.py --registry schema/registry.json`<br>`python scripts/validate_schema.py fixtures/pipeline_run_v1_2/sample.ndjson` | `schema-ci.yml` | Verifies registry metadata + fixtures and enforces `pipeline_run.v1.2` contract before ingest. |
| Policy bundle | `opa test -v --ignore kyverno policies` | `release.yml` (policy-gates job) | Requires `policy-inputs/*` fixtures (SBOM, issuer, referrers). |
| Mutation synthetic workflow | `pytest tools/tests/test_mutation_observatory.py` | `mutation.yml` | Exercises diff thresholds and stale report logic. |
| Ingest dry run (chaos/DR) | `python ingest/chaos_dr_ingest.py --project fake --dataset tmp --chaos-ndjson artifacts/chaos.ndjson --dr-ndjson artifacts/dr.ndjson --dry-run` | local/ingest job | Verifies chaos/DR NDJSON parse + metadata injection without touching BigQuery. |
| Pipeline run emitter + ingest | `python scripts/emit_pipeline_run.py --output artifacts/pipeline_run.ndjson --status success --environment staging` then `python ingest/chaos_dr_ingest.py --project fake --dataset tmp --pipeline-run-ndjson artifacts/pipeline_run.ndjson --dry-run` | `release.yml` (pipeline-run-ingest job) | Guarantees every release publishes a schema-valid `pipeline_run.v1.2` record before loading to BigQuery. |
| Kyverno manifest check | `kyverno apply supply-chain-enforce/kyverno/verify-images.yaml --resource <sample manifest>` | `release.yml` / ops runbook | Confirms signed images + attestations satisfy policy before rollout. |

## Unified Make Targets

All of the common local workflows are wired through the root `Makefile`. Examples:

```bash
make help                 # discover available targets
make setup                # install dev requirements (pytest, mkdocs, etc.)
make all                  # lint + docs + pytest + simulators + sample policy data
make run-chaos            # execute chaos simulator (artifacts/chaos/*)
make run-dr               # run DR drill simulator (artifacts/dr/*)
make run-mutation         # run Mutation Observatory with repo config
make run-cache-sentinel   # record+verify sample cache manifest
make build-vex            # emit CycloneDX VEX under artifacts/sbom/
make build-vuln-input     # turn the sample Grype report into policy-inputs JSON
REKOR_DIGEST=sha256:<..> make run-rekor-monitor  # download Rekor proof bundle
```

Targets are composable, so CI-equivalent flows (`lint`, `docs`, `test`, etc.) can be run individually without waiting on GitHub Actions.

## Local Smoke Suite

```bash
python -m pip install -r requirements-dev.txt
pytest tools/tests
python scripts/check_schema_registry.py --registry schema/registry.json
python scripts/validate_schema.py fixtures/pipeline_run_v1_2/sample.ndjson
python scripts/run_dbt.py deps
python scripts/run_dbt.py build --select stg_pipeline_runs+ run_health
# Optional: exercise cache provenance script with a scratch cache directory
python scripts/cache_provenance.sh --stage test --cache-dir artifacts/cache --output artifacts/cache/provenance
python ingest/chaos_dr_ingest.py \
  --project demo --dataset ci_intel \
  --chaos-ndjson artifacts/evidence/chaos/events.ndjson \
  --dr-ndjson artifacts/evidence/dr/events.ndjson \
  --dry-run
python scripts/emit_pipeline_run.py \
  --output artifacts/pipeline_run.ndjson \
  --status success \
  --environment staging \
  --autopsy-report fixtures/autopsy/sample.json
python ingest/chaos_dr_ingest.py \
  --project demo --dataset ci_intel \
  --pipeline-run-ndjson artifacts/pipeline_run.ndjson \
  --dry-run
opa test -v --ignore kyverno policies

> **Tip**: Ensure `data/warehouse/pipeline_runs.ndjson` contains the autopsy payload (for example, copy `fixtures/pipeline_run_v1_2/sample.ndjson`) before running the dbt models so `stg_autopsy_findings` can materialize.

> **Note**: The dbt `deps`/`build` steps require outbound access to `hub.getdbt.com`.
> If they fail locally because of network restrictions, rerun them once connectivity is
> available—CI executes the same commands inside `schema-ci.yml`.

> **Tip**: `scripts/cache_provenance.sh` is safe to run locally; point `--cache-dir`
> at a throwaway directory if you don’t want to hash your entire pip cache.
```

To exercise the full release path locally, run `./scripts/install_tools.sh` once, then execute the relevant sections from `.github/workflows/release.yml` (syft → cosign → publish referrers). Capture the generated NDJSON artifacts and feed them to the ingest dry run above.

## MkDocs Preview

Documentation edits should pass `markdownlint` and render via MkDocs:

```bash
pip install mkdocs-material
cd docs
mkdocs serve
```

## Changelog

- 2025-10-26: Documentation framework initialized.
- 2025-11-14: Added ingest + Kyverno checks to the matrix.
- 2025-11-19: Documented Makefile-based local CI flow.
- 2025-11-25: Added pipeline_run emitter + ingest validation steps.
