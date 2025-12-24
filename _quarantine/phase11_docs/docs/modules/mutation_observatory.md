# Mutation Observatory

_Source of truth: `tools/mutation_observatory/README.md`._

## Purpose

Run mutation analyzers (e.g., Stryker, mutmut) and emit structured resilience telemetry for CI gating.

## Usage

```bash
python tools/mutation_observatory.py \
  --config config/mutation-observatory.ci.yaml \
  --output artifacts/mutation/run.json \
  --ndjson artifacts/mutation/run.ndjson \
  --markdown artifacts/mutation/summary.md
```

## Configuration

- `config/mutation-observatory.ci.yaml` defines targets (tool, parser, report path, thresholds).
- Supports optional commands that generate reports relative to `workdir`.

## Testing

```bash
pytest tools/tests/test_mutation_observatory.py
```

Workflow: `.github/workflows/mutation.yml` runs the same suite.

## Dependencies

- Python 3.12+
- `pytest` for tests
- Upstream workflow relies on `syft`, `grype` for SBOM inputs when running real mutators.

## Output & Artifacts

- JSON: `artifacts/mutation/run.json`
- NDJSON: `artifacts/mutation/run.ndjson`
- Markdown summary: `artifacts/mutation/summary.md`

## Changelog

- 2025-10-26: Documentation framework initialized.

## License

See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md) · [Testing](../TESTING.md)
