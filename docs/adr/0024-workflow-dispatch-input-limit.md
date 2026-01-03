# ADR-0024: Workflow Dispatch Input Limit

**Status**: Accepted  
**Date:** 2025-12-24  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

**Update:** Simplify-workflows removed `threshold_overrides_yaml`; thresholds and tool toggles are now config-only and resolved by the CLI at runtime. Caller workflows only dispatch minimal metadata (for example, `hub_correlation_id`).

## Context

GitHub Actions `workflow_dispatch` events have a **hard limit of 25 inputs**. Prior caller workflows (e.g., `hub-java-ci.yml`, `hub-python-ci.yml`) exceeded this limit when we tried to dispatch both:
- Tool toggles (booleans like `run_pytest`, `run_jacoco`)
- Threshold values (numbers like `coverage_min`, `max_critical_vulns`)
- Metadata (numbers/strings like `retention_days`, `artifact_prefix`)

This caused dispatch errors:
```
you may only define up to 25 `inputs` for a `workflow_dispatch` event
```

## Decision

**Keep dispatch inputs minimal:**

| Input Type | Where Configured | Dispatch via Orchestrator? |
|------------|------------------|---------------------------|
| Correlation ID | Dispatch input | Yes |
| Tool toggles, settings, thresholds, metadata | `.ci-hub.yml` + hub defaults (resolved by CLI) | No |

**Rationale:**

1. **Keep dispatch inputs minimal** - Avoids the 25-input limit and reduces drift between hub and repo configs.
2. **Resolve config at runtime** - Tool toggles, thresholds, and settings live in `.ci-hub.yml` and hub defaults, so the CLI can normalize them consistently.
3. **Thresholds are stable** - They should not vary per-dispatch; config-only keeps behavior predictable.

**Config Hierarchy for Thresholds:**

Thresholds are read at workflow execution time (not dispatch time):

1. `.ci-hub.yml` in target repo (highest precedence)
2. `config/repos/<repo>.yaml` in hub
3. `config/defaults.yaml` in hub
4. CLI defaults (when a field is omitted)

## Alternatives Considered

1. **Combine thresholds into JSON/YAML object input:**
   ```yaml
   thresholds: '{"coverage_min": 70, "max_critical_vulns": 0}'
   ```
   Initially rejected for complexity. A limited YAML escape hatch was briefly adopted, then removed in simplify-workflows to keep dispatch inputs minimal.

2. **Remove some tool toggles:**
   Rejected: Limits flexibility. Tool toggles are the primary customization point.

3. **Use environment variables instead of inputs:**
   Rejected: Less visible in dispatch UI. Harder to configure per-repo.

4. **Split into multiple workflows:**
   Rejected: Adds complexity. Single caller workflow per language is cleaner.

## Consequences

**Positive:**
- Stays under 25-input limit with room for future tools
- Preserves simple boolean toggle design (`enabled: true`)
- Thresholds still configurable via `.ci-hub.yml`
- Cleaner dispatch UI (only shows what you'd actually change)

**Negative:**
- Can't override thresholds via dispatch UI (must edit `.ci-hub.yml`)
- Must keep caller templates in sync with hub defaults

## Implementation

Files changed:
- `templates/repo/hub-java-ci.yml` - Thin caller; only dispatch metadata and hub ref.
- `templates/repo/hub-python-ci.yml` - Same pattern.
- `.github/workflows/hub-ci.yml` - Reads `.ci-hub.yml` via `cihub config-outputs` and passes resolved settings internally.
- `.github/workflows/hub-orchestrator.yml` - Dispatches without thresholds or tool toggles.

Input counts after change:
- Caller workflow: 1 input (`hub_correlation_id`)

## References

- GitHub docs: [workflow_dispatch event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- ADR-0006: Quality Gates and Thresholds
- ADR-0002: Config Precedence
