# CI/CD Hub - Execution Plan

**Status:** Canonical plan for active work
**Last Updated:** 2025-12-31

---

## Purpose

Single source of truth for what we are doing now. Other docs can provide depth, but this file owns priorities, scope, and sequencing.

## Current Focus (ADR-0035)

- [ ] Implement triage bundles + priority output + LLM prompt pack.
- [ ] Implement registry CLI + versioning/rollback.
- [x] Make aggregate reports resilient to failed repos (render partial summaries instead of aborting).

## Canonical Sources of Truth

1. **Code** (`cihub/`, `schema/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is the authoritative interface documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the authoritative config contract.
4. **AGENTS.md** defines operating rules for AI and contributors.

## References (Background Only)

- `pyqt/planqt.md` (PyQt concept scope)
- `docs/development/architecture/ARCH_OVERVIEW.md` (current architecture overview)
- `docs/development/archive/ARCHITECTURE_PLAN.md` (archived deep-dive plan)

These are references, not competing plans.

---

## Current Decisions

- **CLI is the execution engine**; workflows are thin wrappers.
- **Single entrypoint workflow is `hub-ci.yml`**; it routes to `python-ci.yml`/`java-ci.yml` internally.
- **Local verification uses CLI scaffolding + smoke**; fixtures repo is for CI/regression, not required for local tests.

---

## Near-Term Priorities (In Order)

### 1) Plan Consolidation (Immediate)

- [x] Create this file as the canonical plan.
- [x] Add reference banners to `pyqt/planqt.md` and `docs/development/archive/ARCHITECTURE_PLAN.md` stating this plan is canonical.
- [x] Create `AGENTS.md` and ensure `CLAUDE.md` points to it.

### 2) CLI as Source of Truth (Core)

- [x] Implement CLI helpers:
  - `cihub preflight` (doctor alias)
  - `cihub scaffold <type>`
  - `cihub smoke [--full]`
- [ ] Commit CLI helpers.
- [x] Add CLI doc generation commands:
  - `cihub docs generate` -> `docs/reference/CLI.md` + `docs/reference/CONFIG.md`
  - `cihub docs check` for CI drift prevention
- [x] Add `cihub check` command (local validation suite: preflight → lint → typecheck → test → actionlint → docs-check → smoke)
- [ ] Optional CLI utilities: see **6) CLI Automation** below

### 3) Documentation Cleanup (Controlled Sweep)

- [x] Create `docs/README.md` as index of canonical vs reference vs archive.
- [x] Merge overlapping guides into **one** user entry point:
  - `docs/guides/GETTING_STARTED.md` is canonical user entry point.
  - Folded in ONBOARDING, MODES, DISPATCH_SETUP (now archived with superseded banners).
  - MONOREPOS, TEMPLATES, KYVERNO kept as advanced references.
  - `docs/guides/TROUBLESHOOTING.md` kept separate.
- [x] Archive `CONFIG_REFERENCE.md` (superseded by generated `CONFIG.md`).
- [x] Archive `docs/development/architecture/ARCHITECTURE_PLAN.md`.
- [ ] Move remaining legacy/duplicate docs to `docs/development/archive/` with a superseded header (no deletion).
- [x] Archive legacy dispatch templates under `templates/legacy/` and update docs/tests to match.
- [ ] Make reference docs generated, not hand-written (CLI/CONFIG done; TOOLS still manual).
  - Execution docs: merge `docs/development/execution/SMOKE_TEST*.md` into `docs/guides/INTEGRATION_SMOKE_TEST.md` or archive.
  - Status docs: keep `docs/development/status/STATUS.md` canonical; archive snapshots.
  - Specs docs: keep `docs/development/specs/` as reference (no merge yet).
  - Research docs: keep `docs/development/research/` as reference.
  - Architecture docs: keep `docs/development/architecture/ARCH_OVERVIEW.md` + `SUMMARY_CONTRACT.md` as active references.

### 4) Staleness Audit (Doc + ADR)

- [ ] Run a full stale-reference audit (docs/ADRs/scripts/workflows).
- [x] Record findings in a single audit ledger (`claude_audit.md`).
- [x] Update ADRs that reference old workflow entrypoints and fixture strategy.

### 5) Verification

- [x] Run targeted pytest and record results in `docs/development/status/STATUS.md`.
- [x] Run `cihub smoke --full` on scaffolded fixtures and capture results.
- [ ] Re-run the hub production workflows as needed after CLI changes.
- [x] Define and document a local validation checklist that mirrors CI (`cihub check` + `make check` + GETTING_STARTED.md section).
- [x] Capture a CI parity map in the plan (localizable vs CI-only per hub-production step).

### 6) CLI Automation (Drift Prevention)

- [x] Add pre-commit hooks: actionlint, zizmor, lychee
- [x] Fix stale doc links (TOOLS.md, TEMPLATES.md, TROUBLESHOOTING.md, DEVELOPMENT.md pointed to archived guides)
- [x] `cihub docs links` — Check internal doc links (offline by default, `--external` for web)
- [x] `cihub adr new <title>` — Create ADR from template with auto-number
- [x] `cihub adr list` — List all ADRs with status
- [x] `cihub adr check` — Validate ADRs reference valid files
- [x] `cihub verify` — Contract check for caller templates and reusable workflows (optional remote/integration modes)
- [x] `cihub hub-ci badges` — Generate/validate CI badges from workflow artifacts.
- [ ] `cihub config validate` (or `cihub validate --hub`) — Validate hub configs (resolves validate ambiguity)
- [ ] `cihub audit` — Umbrella: docs check + links + adr check + config validate
- [x] Add `make links` target
- [ ] Add `make audit` target
- [ ] Add a “triage bundle” output for failures (machine-readable: command, env, tool output, file snippet, workflow/job/step).
- [x] Add a template freshness guard (caller templates + legacy dispatch archive).

### 7) Local/CI Parity (Expand `cihub check`)

- [x] Define a CI-parity map: every hub-production-ci.yml step is either locally reproducible or explicitly CI-only.
- [x] Expand `cihub check` tiers:
  - `cihub check` (fast default)
  - `cihub check --audit` (docs links + ADR check + config/profile validation)
  - `cihub check --security` (bandit, pip-audit, gitleaks, trivy; skip if missing)
  - `cihub check --full` (audit + templates + matrix keys + license + zizmor)
  - `cihub check --all` (everything)
- [x] Add optional tool detection and clear "skipped/missing tool" messaging.
- [x] Update `docs/guides/GETTING_STARTED.md` with new flags and expected runtimes.
- [x] Add `docs/guides/CLI_EXAMPLES.md` with runnable command examples.
- [x] Update AGENTS.md rule: "If GitHub CI fails but local checks passed, add it to `cihub check` or document as CI-only."
- [ ] Evaluate `act` integration for local workflow simulation (document limitations; optional).

### 8) Services Layer (Phase 5A, PyQt6 Readiness)

- [x] Add discovery service + tests; wire `cihub discover` to services layer.
- [x] Add report validation service with **parity-first** behavior:
  - include summary parsing + summary/report cross-checks
  - include artifact fallback when metrics are missing
  - include effective-success merging for summary/tool status
  - avoid duplicate maps/logic between service and CLI
- [x] Wire `cihub report validate` to the service and keep CLI-only output/verbosity in the adapter.
- [x] Add aggregation service (Phase 5A pattern) and wire CLI adapter.

### 9) Triage, Registry, and LLM Bundles (New)

- [ ] Define `cihub-triage-v1` schema with severity/blocker fields and stable versioning.
- [ ] Implement `cihub triage` to emit:
  - `.cihub/triage.json` (full bundle)
  - `.cihub/priority.json` (sorted failures)
  - `.cihub/triage.md` (LLM prompt pack)
  - `.cihub/history.jsonl` (append-only run log)
- [ ] Standardize artifact layout under `.cihub/artifacts/<tool>/` with a small manifest.
- [ ] Normalize core outputs to standard formats (SARIF, Stryker mutation, pytest-json/CTRF, Cobertura/lcov, CycloneDX/SPDX).
- [ ] Add severity map defaults (0-10) with category + fixability flags.
- [ ] Add `cihub fix --safe` (deterministic auto-fixes only).
- [ ] Add `cihub assist --prompt` (LLM-ready prompt pack from triage bundle).
- [ ] Define registry format and CLI (`cihub registry list/show/set/diff/sync`). NOTE: this will add `config/registry.json` (Ask First).
- [ ] Add drift detection by cohort (language + profile + hub) and report variance against expected thresholds.
- [ ] Add registry versioning + rollback (immutable version history).
- [ ] Add triage schema validation (`cihub triage --validate-schema`).
- [ ] Add retention policies (`cihub triage prune --days N`).
- [ ] Add aggregate pass rules (composite gating).
- [ ] Add post-mortem logging for drift incidents.
- [ ] Add continuous reconciliation (opt-in auto-sync).
- [ ] Add RBAC guidance (defer to GitHub permissions for MVP).
- [ ] Add DORA metrics derived from history (optional).

---

## Documentation Consolidation Rules

- Do not duplicate CLI help text in markdown; generate it.
- Do not hand-write config field docs; generate from schema.
- If code and docs conflict, code wins and docs must be updated.

---

## Scope Guardrails

1. No large refactors (renames, src/ move, etc.) until workflow migration stabilizes.
2. No deleting docs; archive instead.
3. ADR alignment comes before cleanup decisions.
4. Fixtures repo stays for CI/regression; local dev uses scaffold/smoke.

---

## Open Questions

- Where should the long-term audit ledger live (root vs docs/development)?
- Which generated doc toolchain do we want (custom CLI, sphinx-click, or minimal generator)?
- Do we want a CI gate for ADR drift detection (warn vs fail)?

---

## Definition of Done (Near-Term)

- [x] CLI helpers committed and passing tests (`cihub check`, `preflight`, `scaffold`, `smoke`).
- [x] `docs/reference/CLI.md` and `docs/reference/CONFIG.md` generated from code.
- [x] `docs/README.md` exists and clarifies doc hierarchy.
- [x] Guides consolidated into a single entry point (`GETTING_STARTED.md`).
- [x] ADRs updated to reflect `hub-ci.yml` wrapper and CLI-first execution.
- [ ] Smoke test and targeted pytest results recorded.
- [x] Local validation checklist documented and used before push (`make check` + GETTING_STARTED.md).
- [x] Pre-commit hooks: actionlint, zizmor, lychee.
- [x] CLI automation: `docs links` (with `--external` flag, fallback to Python).
- [x] CLI automation: `adr new/list/check` commands.
- [ ] CLI automation: `config validate`, `audit` (remaining).
