# ADR-0009: Monorepo Support via repo.subdir

**Status**: Accepted  
**Date:** 2026-12-15  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

Some teams keep multiple services in a single repository. The hub originally assumed one project per repo root, which breaks for monorepos (e.g., fixtures repo with multiple subprojects). We need a first-class way to target a subdirectory without duplicating repos.

## Decision

- Add `repo.subdir` to the config schema.
- Central workflow (`hub-run-all.yml`) rewrites checkout to the specified subdir before running tools.
- Distributed workflow (`hub-orchestrator.yml`) passes `workdir` to reusable `java-ci.yml` / `python-ci.yml`, which run all steps with `working-directory: ${{ inputs.workdir }}`.
- Provide a monorepo config template and documentation (`templates/hub/config/repos/monorepo-template.yaml`, `docs/guides/MONOREPOS.md`).

## Implementation Details

### Job-Level Working Directory

All jobs that run tools must set `defaults.run.working-directory` to scope operations to the correct subdirectory:

```yaml
jobs:
  lint:
    defaults:
      run:
        working-directory: ${{ inputs.workdir }}
```

**Jobs requiring workdir scoping:**

| Workflow | Jobs |
|----------|------|
| `python-ci.yml` | lint, test, security, typecheck, mutation-test, semgrep, trivy, docker-build, codeql |
| `java-ci.yml` | build-test, pmd, semgrep, trivy, mutation-test, docker-build, codeql |

**Jobs NOT requiring workdir:** `report` (downloads artifacts, no source access needed)

### CodeQL Source Root

CodeQL requires explicit `source-root` to scope analysis:

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: python
    source-root: ${{ inputs.workdir }}
```

Without `source-root`, CodeQL scans the entire checkout (all fixtures instead of just one).

### Trivy Action Output Path

The `trivy-action` outputs files to **workspace root**, ignoring `working-directory`. Use `scan-ref` to scope the scan and reference output via `${{ github.workspace }}`:

```yaml
- name: Run Trivy Scan
  uses: aquasecurity/trivy-action@0.28.0
  with:
    scan-type: 'fs'
    scan-ref: ${{ inputs.workdir }}  # Scope scan to workdir
    format: 'json'
    output: 'trivy-report.json'      # Outputs to workspace root

- name: Parse Trivy Results
  run: |
    # trivy-action outputs to workspace root, not working-directory
    REPORT="${{ github.workspace }}/trivy-report.json"
    if [ -f "$REPORT" ]; then
      CRITICAL=$(jq '...' "$REPORT")
    fi
```

**Gotcha**: Without `scan-ref`, Trivy scans entire repo. Without `${{ github.workspace }}` path, parsing fails silently (reports 0 findings).

### Artifact Name Collisions

When multiple fixture jobs call the same reusable workflow, artifacts collide (409 Conflict). Use `artifact_prefix` to namespace:

```yaml
jobs:
  ci-passing:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      workdir: 'python-passing'
      artifact_prefix: 'python-passing-'  # Prevents collision

  ci-failing:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      workdir: 'python-failing'
      artifact_prefix: 'python-failing-'  # Different prefix
```

### Update History

- 2025-12-18: Added `working-directory` to lint and codeql jobs in both Python and Java workflows. Previously lint and CodeQL scanned entire repo root, causing failures when multiple fixtures shared a repo.
- 2025-12-18: Fixed Trivy action to use `scan-ref` and `${{ github.workspace }}` path. Previously Trivy reported 0 findings because output file was written to workspace root but parsing looked in workdir.
- 2025-12-18: Added `artifact_prefix` input to prevent artifact name collisions when multiple jobs call the same workflow.
- 2025-12-18: Updated caller templates with `max_semgrep_findings` and `artifact_prefix` inputs.

## Consequences

Positive:
- Monorepo projects can be tested without repo splitting.
- Fixtures monorepo (`ci-cd-hub-fixtures`) works with the hub smoke tests.
- Each fixture runs in isolation without cross-contamination.

Negative:
- Additional config surface; mis-set `subdir` will fail early.
- Distributed paths required workflow updates to respect `workdir`.
- All new jobs must remember to set `working-directory`.

## Alternatives Considered

- Split fixtures into separate repos: rejected to keep fixture maintenance simple.
- Per-step custom working directories: more boilerplate; defaults at job level are cleaner.
