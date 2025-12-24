# ADR-0003: Documentation Governance & Sources of Truth
Status: Accepted
Date: 2025-11-02
Owners: Docs & Platform

## Context
Documentation had drift: broken references (`issues.md`, `START_HERE.md` casing), duplicated readiness narratives, empty directories, and generated indexes with placeholders. The project needs a single map of sources of truth (SoT) and required hygiene (linting, regeneration) to keep docs trustworthy.

## Decision
- Establish SoT per concern:
  - Roadmap/control catalog: `plan.md`
  - Readiness/status: `docs/status/honest-status.md` (primary); historical snapshot at `docs/status/archive/implementation-2025-11-02.md`
  - Day-1 actions: `docs/start-here.md`
  - Backlog summary: `docs/backlog.md` (issues are canonical)
  - Changelog: `CHANGELOG.md`
  - Decisions: `docs/adr/`
  - Module/tool references: `docs/modules/*` and tool READMEs
  - CI summary of multi-repo runs: run-level `project-ci-summary` artifact + run summary table emitted by `.github/workflows/project-ci.yml` (tests/coverage/spotbugs/bandit/ruff per repo); mutation summaries live under `mutation-observatory-*` artifacts.
- Regenerate `docs/index.md` and `STRUCTURE.md` via scripts and fail CI on broken/orphaned links once wired.
- Remove or archive empty/backup doc directories after owner review; exclude backup trees from generated indexes.

## Consequences
- Future doc changes must update the relevant SoT and add ADRs when decisions materially change scope or guarantees. Historical status snapshot is archived at `docs/status/archive/implementation-2025-11-02.md`.
- PRs should include doc lint/index regeneration; templates/checklists must be updated accordingly.
- Stale references to deprecated files (`issues.md`, missing indexes) must be cleaned as part of this effort.
- CI reporting locations (project-ci and mutation summaries) are part of the SoT map and must stay accurate in README/plan/audit; changes to output paths require doc updates.

## References
- audit.md
- docs/index.md
- STRUCTURE.md
- scripts/docs/generate_index.sh, scripts/docs/generate_structure.sh
