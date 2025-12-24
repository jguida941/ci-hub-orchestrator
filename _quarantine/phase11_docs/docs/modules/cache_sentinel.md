# Cache Sentinel

_Source of truth: `tools/cache_sentinel/README.md`._

## Purpose

Record and verify cache manifests (BLAKE3/SHA-256) to detect tampering or drift across builds.

## Usage

### Record

```bash
python tools/cache_sentinel.py record \
  --cache-dir "$(python -m pip cache dir)" \
  --output artifacts/evidence/cache/cache-manifest.json \
  --max-files 500
```

### Verify

```bash
python tools/cache_sentinel.py verify \
  --cache-dir "$(python -m pip cache dir)" \
  --manifest artifacts/evidence/cache/cache-manifest.json \
  --quarantine-dir artifacts/evidence/cache/quarantine \
  --report artifacts/evidence/cache/cache-report.json
```

## Configuration

- `--max-files` controls sampling when recording.
- Verification reads the manifest’s `algorithm` (`blake3` or `sha256`).

## Testing
- Release workflow coverage; expand with unit tests in `tools/tests/test_cache_sentinel.py`.

## Dependencies

- Python 3.12+
- `blake3` (optional fallback to `hashlib.sha256`)

## Output & Artifacts

- Manifest: `artifacts/evidence/cache/cache-manifest.json`
- Report: `artifacts/evidence/cache/cache-report.json`
- Quarantined files: `artifacts/evidence/cache/quarantine/`

## Changelog

- 2025-10-26: Documentation framework initialized.

## License

See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md) · [Testing](../TESTING.md)
