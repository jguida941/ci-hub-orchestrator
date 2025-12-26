# ADR-0014: Reusable Workflow Migration

**Status**: Accepted  
**Date:** 2025-12-17  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

- Supersedes: ADR-0013

## Context

ADR-0013 established dispatch workflow templates (`*-ci-dispatch.yml`) that users copy to target repos. While this solved the immediate need for dispatchable workflows, it created maintenance problems:

1. **Template drift**: Dispatch templates in repos become outdated as the hub evolves
2. **Incomplete reports**: Repos running old templates emit 4-field reports instead of 12+ fields
3. **0% mutation scores**: Parsing issues in outdated templates cause incorrect metrics
4. **Manual sync required**: No mechanism to propagate hub updates to dispatched repos
5. **Duplicated logic**: Each repo contains the full CI pipeline logic (300+ lines)

The root cause of the "orchestrator claims to run everything but reports show 0%" issue is that dispatch templates diverge from the hub's reusable workflows.

## Decision

### 1. Migrate to Reusable Workflows with `workflow_call`

Replace copy-paste dispatch templates with minimal "caller" workflows that invoke the hub's reusable workflows:

**Before (ADR-0013 - 300+ lines per repo):**
```yaml
# target-repo/.github/workflows/java-ci-dispatch.yml
name: Java CI (Dispatch)
on:
  workflow_dispatch:
    inputs:
      java_version: ...
      # 50+ lines of input definitions
jobs:
  build:
    # 250+ lines of job steps duplicating hub logic
```

**After (Caller - ~30 lines per repo):**
```yaml
# target-repo/.github/workflows/hub-ci.yml
name: Hub CI
on:
  workflow_dispatch:
    inputs:
      # All inputs forwarded
jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      python_version: ${{ inputs.python_version }}
      # All inputs passed through
    secrets: inherit
```

### 2. Semantic Versioning for Workflows

Tag workflow releases with semantic versions:
- `@v1` - Floating tag pointing to latest v1.x.x
- `@v1.0.0`, `@v1.1.0` - Specific releases
- `@main` - Development only (never use in production)

### 3. Full Report Schema with `schema_version`

All reusable workflows emit a standardized `report.json` with:

```json
{
  "schema_version": "2.0",
  "metadata": {
    "workflow_version": "v1.0.0",
    "workflow_ref": "jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1"
  },
  "results": {
    "coverage": 87,
    "mutation_score": 72,
    "tests_passed": 42,
    "tests_failed": 0,
    "ruff_errors": 0,
    "bandit_high": 0,
    "bandit_medium": 2,
    // ... 12+ fields total
  }
}
```

### 4. Caller Templates in Hub

Provide official caller templates in `templates/repo/`:
- `hub-python-ci.yml` - Python caller with full input passthrough
- `hub-java-ci.yml` - Java caller with full input passthrough
- `.ci-hub.yml` - Updated starter config

## Consequences

### Positive

- **Automatic sync**: Hub updates propagate to all repos via `@v1` tag
- **Single source of truth**: CI logic lives in hub, not copied everywhere
- **Complete reports**: All repos get full 12+ field reports
- **Version control**: Repos can pin to specific versions or float with `@v1`
- **Simpler repos**: Caller is ~30 lines vs 300+ for dispatch templates
- **Breaking change isolation**: Breaking changes go to `@v2`, repos opt-in

### Negative

- **Migration effort**: Existing repos must replace dispatch templates with callers
- **Cross-repo dependency**: Caller depends on hub being available
- **Version coordination**: Major version bumps require repo-by-repo migration

## Alternatives Considered

1. **Keep dispatch templates + auto-sync tool**: Rejected - still requires per-repo files with full logic
2. **GitHub Template Sync action**: Rejected - overwrites customizations, not incremental
3. **Copier for template updates**: Rejected - adds tooling dependency

## Implementation

### Files Created/Modified

| File | Change |
|------|--------|
| `templates/repo/hub-python-ci.yml` | NEW - Python caller template |
| `templates/repo/hub-java-ci.yml` | NEW - Java caller template |
| `.github/workflows/python-ci.yml` | MODIFIED - Add schema_version, full metrics |
| `.github/workflows/java-ci.yml` | MODIFIED - Add schema_version, full metrics |
| `.github/workflows/release.yml` | NEW - Workflow release pipeline |

### Migration Path

1. **Phase 1**: Update reusable workflows to emit full report schema
2. **Phase 2**: Create caller templates with full input passthrough
3. **Phase 3**: Tag v1.0.0, create floating v1 tag
4. **Phase 4**: Migrate repos one-by-one (replace dispatch template with caller)
5. **Phase 5**: Deprecate and remove old dispatch templates

### User Migration

```bash
# 1. Remove old dispatch template
rm .github/workflows/java-ci-dispatch.yml

# 2. Copy new caller template
cp hub-release/templates/repo/hub-java-ci.yml .github/workflows/hub-ci.yml

# 3. Update config (optional - defaults work)
# repo:
#   dispatch_workflow: hub-ci.yml

# 4. Push and test
git add . && git commit -m "Migrate to reusable workflow caller"
git push
```

## Related ADRs

- ADR-0011: Dispatchable Workflow Requirement
- ADR-0013: Dispatch Workflow Templates (SUPERSEDED)
