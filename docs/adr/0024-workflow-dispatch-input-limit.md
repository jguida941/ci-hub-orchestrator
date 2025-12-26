# ADR-0024: Workflow Dispatch Input Limit

**Status**: Accepted  
**Date:** 2025-12-24  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

GitHub Actions `workflow_dispatch` events have a **hard limit of 25 inputs**. Our caller workflows (e.g., `hub-java-ci.yml`, `hub-python-ci.yml`) were exceeding this limit when we tried to dispatch both:
- Tool toggles (booleans like `run_pytest`, `run_jacoco`)
- Threshold values (numbers like `coverage_min`, `max_critical_vulns`)
- Metadata (numbers/strings like `retention_days`, `artifact_prefix`)

This caused dispatch errors:
```
you may only define up to 25 `inputs` for a `workflow_dispatch` event
```

## Decision

**Split inputs by type:**

| Input Type | Where Configured | Dispatch via Orchestrator? |
|------------|------------------|---------------------------|
| Tool toggles (`run_*`) | Dispatch inputs | Yes (booleans) |
| Essential settings | Dispatch inputs | Yes (version, workdir, build_tool) |
| Thresholds (`*_min`, `max_*`) | Caller template defaults or `.ci-hub.yml` | No |
| Metadata (`retention_days`, `artifact_prefix`) | Caller template defaults | No |
| Threshold override escape hatch | `threshold_overrides_yaml` dispatch input | Yes (single YAML string) |

**Rationale:**

1. **Tool toggles must be dispatchable** - The orchestrator enables/disables tools per-repo based on config. Users can also manually override via dispatch UI.

2. **Thresholds rarely need per-dispatch override** - Most repos set thresholds once in `.ci-hub.yml` or accept caller defaults. Thresholds don't need to be different per-run.

3. **Metadata is truly static** - `retention_days` (30) and `artifact_prefix` ('') almost never change. Hardcode in caller template.

**Config Hierarchy for Thresholds:**

Thresholds are read at workflow execution time (not dispatch time):

1. `.ci-hub.yml` in target repo (highest precedence)
2. `config/repos/<repo>.yaml` in hub
3. `config/defaults.yaml` in hub
4. Hardcoded defaults in caller template `with:` block

## Alternatives Considered

1. **Combine thresholds into JSON/YAML object input:**
   ```yaml
   thresholds: '{"coverage_min": 70, "max_critical_vulns": 0}'
   ```
   Initially rejected for complexity. **Later adopted as narrow escape hatch:** `threshold_overrides_yaml` input allows orchestrator to pass resolved thresholds. This is dispatch-time only, NOT a config tier.

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
- `templates/repo/hub-java-ci.yml` - Removed threshold dispatch inputs, hardcoded in `with:`
- `templates/repo/hub-python-ci.yml` - Same pattern
- `.github/workflows/hub-orchestrator.yml` - Removed threshold inputs from dispatch payload

Input counts after change:
- Java caller: 17 inputs (was 26) - 4 essential + 12 tool toggles + 1 threshold_overrides_yaml
- Python caller: 17 inputs (was 26) - 3 essential + 13 tool toggles + 1 threshold_overrides_yaml

Note: `run_docker` was added as a dispatchable toggle (per Option 1), while `docker_compose_file` and `docker_health_endpoint` remain config/with-block strings.

## References

- GitHub docs: [workflow_dispatch event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- ADR-0006: Quality Gates and Thresholds
- ADR-0002: Config Precedence
