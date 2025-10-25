# CI Intelligence Hub

This repository implements the production-grade CI/CD platform defined in `plan.md`.

## Current focus

- Supply-chain enforcement (Kyverno policies, OCI referrers, Rekor proofs)
- Determinism tooling and data-quality/DR pipelines

Refer to `plan.md` for the complete architecture, roadmap, and v1.0 exit criteria.

## Development setup

Install the Python dependencies needed for local tooling/tests:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### Mutation Observatory workflow

- Config: `mutation-observatory.ci.yaml`
- Run locally:

```bash
python tools/scripts/generate_mutation_reports.py \
  --stryker artifacts/mutation/stryker-report.json \
  --mutmut artifacts/mutation/mutmut-report.json

python tools/mutation_observatory.py \
  --config mutation-observatory.ci.yaml \
  --output artifacts/mutation/run.json \
  --ndjson artifacts/mutation/run.ndjson \
  --markdown artifacts/mutation/summary.md
```

GitHub Actions job `mutation-observatory` (see `.github/workflows/mutation.yml`) runs the same command on every push/PR, uploads the JSON/NDJSON/Markdown artifacts, and fails the build if the aggregate resilience drops below the configured thresholds.
