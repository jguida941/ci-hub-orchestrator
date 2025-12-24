# ADR-0022: Summary Verification Against Reports

## Status
Accepted

## Date
2025-12-24

## Context

The hub workflows render human-readable summaries in `$GITHUB_STEP_SUMMARY`. These summaries are built manually from matrix inputs and tool outputs. We observed drift where disabled tools were shown as enabled because of fallback expressions in the summary table. This undermines trust in the summary and makes it hard to verify that reported tool runs match actual artifacts.

We need a repeatable way to validate that the summary matches the actual execution state and generated artifacts.

## Decision

1. **Make summaries authoritative**
   - Remove fallback expressions that coerce false to true in `hub-run-all.yml`.
   - Include `config_basename` and `run_group` in the summary environment table to identify which config produced the output.

2. **Add a validation script**
   - Introduce `scripts/validate_summary.py` to compare:
     - Summary table entries vs `report.json` `tools_ran` booleans.
     - Artifact presence vs `tools_ran` for tools that generate reports.
   - Script returns non-zero in `--strict` mode.

3. **Prevent regressions**
   - Add a test that fails if `matrix.run_* || 'true'` style fallbacks appear in `hub-run-all.yml`.

## Consequences

### Positive
- Summary output reflects real tool toggles.
- A reusable validation script can be run locally or in CI.
- Future summary drift is caught early.

### Negative
- Requires manual capture of summary text if validation against summaries is desired.
- Some tools do not emit artifacts; validation for those is limited to `report.json`.

## Usage

```bash
python scripts/validate_summary.py \
  --report report.json \
  --summary summary.md \
  --reports-dir all-reports \
  --strict
```

## Follow-ups

- Consider exporting summary text to a file and uploading it as an artifact for automated validation.
- Optionally run `validate_summary.py` in hub workflows after `report.json` is generated.

## Related

- ADR-0021: Java POM Compatibility and CLI Enforcement
