# CI/CD Hub Development Plan

> **Single source of truth** for project status, priorities, and remaining work.
>
> **See also:** `docs/development/architecture/ARCH_OVERVIEW.md`
>
> **Last Updated:** 2025-12-30
> **Version Target:** v1.0.0

---

## Current Focus (Near Term)

1. Align ADRs with the `hub-ci.yml` wrapper and CLI-first execution model.
2. Make CLI the source of truth (preflight/scaffold/smoke) and keep docs minimal.
3. Re-verify workflows and smoke tests after CLI changes land.

---

## Observed in Repo (Not Execution-Tested)

- `hub-ci.yml` wrapper routes to `python-ci.yml`/`java-ci.yml` based on `.ci-hub.yml`.
- CLI command surface includes detect/init/update/validate/config-outputs/ci/run/report/etc.
- New CLI helpers (preflight/doctor, scaffold, smoke) exist in the working tree and need commit + verification.
- Templates still provide language-specific sources that render to a single `hub-ci.yml` in target repos.

---

## Needs Verification (Run Required)

- Hub Orchestrator (`hub-orchestrator.yml`)
- Hub Security (`hub-security.yml`)
- Hub Production CI (`hub-production-ci.yml`) gates
- End-to-end smoke on scaffolds and/or fixtures
- Pytest pass after recent CLI changes

---

## ADR Status

- 35 ADRs in `docs/adr/`.
- Alignment updates added on 2025-12-30 for workflow entrypoints and fixtures strategy.
- Remaining stale references should be addressed as part of any workflow changes.

---

## Scope Guardrails

1. **No deletions** (docs/directories) until ADR alignment is complete.
2. **CLI is authoritative**; docs should describe CLI behavior, not replace it.
3. **Fixtures repo stays for CI/regression**; local dev uses `cihub scaffold` + `cihub smoke`.
4. **Avoid large refactors** (renames, `src/` move, etc.) until workflow migration stabilizes.

---

## Next Steps (Ordered)

1. Commit CLI additions and doc updates.
2. Run targeted pytest and record results here.
3. Run `cihub smoke --full` on scaffolded fixtures and record results.
4. Revisit guide consolidation after ADR alignment and smoke verification.
