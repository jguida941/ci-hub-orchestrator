# ADR-0026: Repo-Side Execution Guardrails

**Status**: Proposed (Placeholder)  
**Date:** 2025-12-25  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The hub's core principle is "target repos stay clean" - all config lives in the hub, and target repos don't need hub-specific files. However, some users may want the hub to generate workflows directly into their target repos for scenarios like:

- Repos that can't use central runner (network restrictions, private dependencies)
- Teams that prefer seeing the workflow in their repo
- Migration from distributed to central mode

This ADR documents the **guardrails** required before enabling this feature.

## Decision

**Add `repo_side_execution` boolean (default: `false`) with strict guardrails.**

When `repo_side_execution: true`, the hub may write files to target repos via `cihub generate-workflow`. This is an **opt-in escape hatch**, not the default behavior.

### Guardrails

| # | Guardrail | Rationale |
|---|-----------|-----------|
| 1 | **Default OFF** | `repo_side_execution: false` by default. No surprises. |
| 2 | **Explicit command** | Must run `cihub generate-workflow --repo <name>`. No implicit writes. |
| 3 | **Dry-run first** | `--dry-run` is the default. Must explicitly use `--apply` to write. |
| 4 | **Manifest tracking** | Store SHA256 hash of generated workflow for drift detection. |
| 5 | **No writes on failure** | If validation fails, abort entirely. No partial writes. |
| 6 | **Backup before write** | Always save `.bak` before overwriting any file. |
| 7 | **Revert capability** | `cihub generate-workflow --revert` restores from backup. |

### Config Structure

```yaml
# In config/repos/<repo>.yaml
repo:
  owner: jguida941
  name: my-repo
  use_central_runner: false     # Using distributed mode
  repo_side_execution: true     # Opt-in to workflow generation
```

### Command Interface

```bash
# Preview what would be written (default)
cihub generate-workflow --repo my-repo --dry-run

# Actually write to target repo
cihub generate-workflow --repo my-repo --apply

# Revert to backup
cihub generate-workflow --repo my-repo --revert

# Validate generated workflow
cihub generate-workflow --repo my-repo --validate
```

## Alternatives Considered

1. **No repo writes ever:**
   Rejected: Too restrictive for valid use cases.

2. **Automatic workflow generation on config change:**
   Rejected: Implicit writes violate "no surprises" principle.

3. **Single toggle for both central/distributed and repo writes:**
   Rejected: These are orthogonal concerns. Distributed mode doesn't require repo writes.

## Consequences

**Positive:**
- Supports valid use cases (network restrictions, team preferences)
- Multiple layers of protection against accidental writes
- Easy revert path
- Drift detection via manifest

**Negative:**
- More complexity in codebase
- Risk of repos diverging from hub config
- Maintenance burden for generated workflows

## Implementation

**Status: NOT IMPLEMENTED**

This ADR is a placeholder documenting the design. Implementation requires:

1. Workflow templates (`templates/workflows/python-cihub.yml`, `templates/workflows/java-cihub.yml`)
2. Generator script (`scripts/cihub_render.py` or integrated into CLI)
3. Manifest storage mechanism
4. Validation logic for generated workflows

See `docs/development/architecture/ARCHITECTURE_PLAN.md` for the workflow generator plan.

## References

- ADR-0025: CLI Modular Restructure
- ADR-0001: Central vs Distributed Mode
- `docs/development/architecture/ARCHITECTURE_PLAN.md` - Workflow Generator section
