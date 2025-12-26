# ADR-0015: Workflow Versioning & Release Policy

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

With the migration to reusable workflows (ADR-0014), we need a clear policy for:
1. When to create releases (tags)
2. How to name version tags
3. How to handle floating tags
4. When breaking changes warrant major version bumps
5. Deprecation timeline for old versions

Callers should pin to tagged releases (`@v1` floating or exact tag), not branches.

## Decision

### 1. Semantic Versioning for Workflows

Follow semver for all workflow releases:

| Version | Meaning |
|---------|---------|
| `v1.0.0` | Initial stable release |
| `v1.1.0` | New features (backward compatible) |
| `v1.1.1` | Bug fixes only |
| `v2.0.0` | Breaking changes |

### 2. Floating Tags

Maintain floating major version tags:

```
v1 → points to latest v1.x.x (currently v1.2.3)
v2 → points to latest v2.x.x (currently v2.0.1)
```

**Caller templates should pin to floating tags** (`@v1`) for automatic patch/minor updates.

### 3. Breaking Change Definition

A change is **breaking** if it:
- Removes or renames an input parameter
- Changes the default value of an input in a way that affects behavior
- Changes the structure of `report.json` in a way that breaks aggregator parsing
- Removes a job or step that callers depend on

A change is **non-breaking** if it:
- Adds new optional input parameters
- Adds new fields to `report.json` (additive)
- Fixes bugs without changing interfaces
- Improves performance

### 4. Release Process

```bash
# 1. Ensure all changes pass actionlint and tests
actionlint .github/workflows/*.yml

# 2. Create semantic version tag
git tag -a v1.2.0 -m "v1.2.0: Add max_semgrep_findings threshold"
git push origin v1.2.0

# 3. Update floating tag
git tag -f v1 v1.2.0
git push -f origin v1

# 4. Create GitHub Release (automated via release.yml)
```

### 5. Deprecation Timeline

| Action | Timeline |
|--------|----------|
| Deprecation announcement | At v(N+1).0.0 release |
| Deprecation warnings in logs | 30 days after announcement |
| Removal of v(N) floating tag | 90 days after v(N+1).0.0 |
| Archive of v(N).x.x tags | Never (always accessible) |

## Consequences

### Positive

- Clear versioning contract for callers
- Automatic minor/patch updates via floating tags
- Breaking changes are opt-in (callers must update to `@v2`)
- Reproducible builds (pin to specific tag if needed)

### Negative

- Requires discipline to follow semver
- Floating tags require force-push (potential for confusion)
- Repos on old versions miss security updates

## Implementation

### Release Workflow (`.github/workflows/release.yml`)

```yaml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate workflows
        run: actionlint .github/workflows/*.yml
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
      - name: Update floating tag
        run: |
          VERSION=${GITHUB_REF#refs/tags/}
          MAJOR=$(echo $VERSION | cut -d. -f1)
          git tag -f $MAJOR
          git push -f origin $MAJOR
```

## Related ADRs

- ADR-0014: Reusable Workflow Migration
