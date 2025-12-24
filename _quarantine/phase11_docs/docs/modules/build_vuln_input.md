# Build Vulnerability Input

_Source of truth: `tools/build_vuln_input/README.md`._

## Purpose

Normalize Grype scan results (and optional VEX evidence) into OPA-friendly JSON for `policies/sbom_vex.rego`.

## Usage

```bash
python tools/build_vuln_input.py \
  --grype-report policy-inputs/grype-report.json \
  --output policy-inputs/vulnerabilities.json \
  --cvss-threshold 7.0 \
  --epss-threshold 0.75 \
  --vex artifacts/sbom/app.vex.json
```

## Configuration

- Thresholds determine which vulnerabilities require VEX coverage.
- `--vex` is optional but recommended to include release VEX.

## Testing

```bash
pytest tools/tests/test_build_vuln_input.py
```

## Dependencies

- Python 3.12+
- `pyyaml`
- `jsonschema`

## Output & Artifacts

- Normalized input: `policy-inputs/vulnerabilities.json`

## Changelog

- 2025-10-26: Documentation framework initialized.

## License

See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md)
