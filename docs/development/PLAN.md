# CI/CD Hub - Execution Plan

**Status:** Canonical plan for active work
**Last Updated:** 2026-01-03

---

## Purpose

Single source of truth for what we are doing now. Other docs can provide depth, but this file owns priorities, scope, and sequencing.

## Current Focus (ADR-0035)

- [ ] Implement triage bundles + priority output + LLM prompt pack.
- [ ] Implement registry CLI + versioning/rollback.
- [x] Make aggregate reports resilient to failed repos (render partial summaries instead of aborting).
- [x] Implement `cihub report dashboard` (HTML + JSON output) replacing scripts/aggregate_reports.py.
- [x] Add CLI env overrides for tool toggles and summary toggle (`CIHUB_RUN_*`, `CIHUB_WRITE_GITHUB_SUMMARY`).
- [x] Add Java SBOM support (schema + CLI runner + workflow wiring).
- [x] Toggle audit + enforcement:
  - [x] Align defaults for `repo.dispatch_enabled`, `repo.force_all_tools`, and `python.tools.sbom.enabled`.
  - [x] Add notifications env-var names to schema/defaults and CLI.
  - [x] Warn when reserved optional feature toggles are enabled.
  - [x] Gate hub-production-ci jobs via `cihub hub-ci outputs`.
- [x] Ensure workflow toggles install required CLIs (Trivy) and wire bandit severity env toggles.
- [x] **No-inline workflow cleanup:**
  - [x] Wire summary toggle in `hub-run-all.yml` summary job (`CIHUB_WRITE_GITHUB_SUMMARY`).
  - [x] Replace zizmor SARIF heredoc in `hub-production-ci.yml` with `cihub hub-ci zizmor-run`.
  - [x] Remove all multi-line `run: |` blocks by moving logic into `cihub hub-ci` helpers.
  - [x] Summary commands implemented and wired:
    - `cihub report security-summary` (modes: repo, zap, overall)
    - `cihub report smoke-summary` (modes: repo, overall)
    - `cihub report kyverno-summary`
    - `cihub report orchestrator-summary` (modes: load-config, trigger-record)
  - [x] Snapshot tests in `tests/test_summary_commands.py` (19 tests) verify parity with old heredocs.
  - [x] Toggle audit tests verify `CIHUB_WRITE_GITHUB_SUMMARY` env var behavior.

## Canonical Sources of Truth

1. **Code** (`cihub/`, `schema/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is the authoritative interface documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the authoritative config contract.

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
  - [x] PR trigger on `template-guard.yml` (validate-local job runs tests/test_templates.py + test_commands_scaffold.py)
  - [x] Render-diff tests (`TestRenderCallerWorkflow`) verify CLI output matches templates
  - [x] Contract verification (`cihub verify`) added to `cihub check --full`
  - [x] Remote sync check (`sync-templates --check`) in `cihub check --full` (skips gracefully if no GH_TOKEN)
  - [x] All 5 scaffold types tested (python-pyproject, python-setup, java-maven, java-gradle, monorepo)

### 7) Local/CI Parity (Expand `cihub check`)

- [x] Define a CI-parity map: every hub-production-ci.yml step is either locally reproducible or explicitly CI-only.
- [x] Expand `cihub check` tiers:
  - `cihub check` (fast default)
  - `cihub check --audit` (docs links + ADR check + config/profile validation)
  - `cihub check --security` (bandit, pip-audit, gitleaks, trivy; skip if missing)
  - `cihub check --full` (audit + templates + verify-contracts + sync-templates-check + matrix keys + license + zizmor)
  - `cihub check --all` (everything)
- [x] Add optional tool detection and clear "skipped/missing tool" messaging.
- [x] Update `docs/guides/GETTING_STARTED.md` with new flags and expected runtimes.
- [x] Add `docs/guides/CLI_EXAMPLES.md` with runnable command examples.
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
- [x] Add CI service wrapper for GUI/programmatic access (`cihub.services.ci`).
- [x] Add config service helpers for load/edit operations (`cihub.services.configuration`).
- [x] Add report summary service for GUI consumption (`cihub.services.report_summary`).
- [x] Move CI execution core into services layer; keep CLI as thin adapter.

### 8b) Config Ergonomics (Shorthand + Threshold Presets)

- [x] Expand shorthand booleans to enabled sections (reports, notifications, kyverno, optional features, hub_ci).
- [x] Add `thresholds_profile` presets with explicit `thresholds` overrides.
- [x] Split CVSS thresholds for OWASP/Trivy and add workflow input parity.

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
