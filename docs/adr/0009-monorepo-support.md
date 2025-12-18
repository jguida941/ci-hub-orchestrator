# ADR-0009: Monorepo Support via repo.subdir

- Status: Accepted
- Date: 2026-12-15

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

### Update History

- 2025-12-18: Added `working-directory` to lint and codeql jobs in both Python and Java workflows. Previously lint and CodeQL scanned entire repo root, causing failures when multiple fixtures shared a repo.

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
