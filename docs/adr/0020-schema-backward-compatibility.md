# ADR-0020: Schema Backward Compatibility

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The CI/CD Hub is migrating from an old lightweight report format to schema 2.0 which includes:
- `schema_version: "2.0"`
- `tool_metrics` object with per-tool issue counts
- `tools_ran` object with boolean flags
- `results.tests_passed` / `results.tests_failed`

During the migration period, some repos will still generate old-format reports. We need a strategy to handle both formats gracefully.

## Decision

### 1. Schema Version Field

All new reports must include `schema_version: "2.0"` at the top level. This allows tooling to detect and handle different formats.

### 2. Aggregator Schema Mode Flag

The `aggregate_reports.py` script supports a `--schema-mode` flag:

```bash
# Default: warn mode - include all reports, log warning for non-2.0
python aggregate_reports.py --output dashboard.html --schema-mode warn

# Strict mode - skip non-2.0 reports, exit 1 if any skipped
python aggregate_reports.py --output dashboard.html --schema-mode strict
```

**Modes:**

| Mode | Behavior | Exit Code |
|------|----------|-----------|
| `warn` (default) | Include all reports, log warning for non-2.0 schema | 0 |
| `strict` | Skip non-2.0 reports, log skip message | 1 if any skipped, else 0 |

### 3. Validation Script Schema Check

The `validate_report.sh` script always requires `schema_version: "2.0"`. This is appropriate for fixture validation where we expect the new schema.

### 4. Migration Path

1. **Phase 1 (current):** Update hub workflows to emit 2.0 schema
2. **Phase 2:** Run aggregator in `warn` mode during migration
3. **Phase 3:** After all repos migrated, switch to `strict` mode
4. **Phase 4:** Remove old schema support (optional)

## Consequences

### Positive

- Backward compatible during migration period
- Clear migration path with configurable strictness
- CI can gate on schema compliance when ready
- No breaking changes for existing integrations

### Negative

- Must maintain two code paths temporarily
- Old reports may have incomplete data in dashboards
- Teams must coordinate migration timing

## Usage Examples

### CI Workflow (Warn Mode)

```yaml
- name: Aggregate Reports
  run: |
    python scripts/aggregate_reports.py \
      --reports-dir ./reports \
      --output dashboard.html \
      --schema-mode warn
```

### CI Workflow (Strict Mode - Post Migration)

```yaml
- name: Aggregate Reports
  run: |
    python scripts/aggregate_reports.py \
      --reports-dir ./reports \
      --output dashboard.html \
      --schema-mode strict
```

### Fixture Validation (Always Strict)

```bash
./scripts/validate_report.sh --report report.json --stack python --expect-clean
# Always requires schema_version: "2.0"
```

## Related ADRs

- ADR-0019: Report Validation Policy
- ADR-0014: Reusable Workflow Migration
