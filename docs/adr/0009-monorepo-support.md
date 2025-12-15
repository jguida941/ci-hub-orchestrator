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

## Consequences

Positive:
- Monorepo projects can be tested without repo splitting.
- Fixtures monorepo (`ci-cd-hub-fixtures`) works with the hub smoke tests.

Negative:
- Additional config surface; mis-set `subdir` will fail early.
- Distributed paths required workflow updates to respect `workdir`.

## Alternatives Considered

- Split fixtures into separate repos: rejected to keep fixture maintenance simple.
- Per-step custom working directories: more boilerplate; defaults at job level are cleaner.
