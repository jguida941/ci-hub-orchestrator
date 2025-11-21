# Documentation & Process Audit

Snapshot: repository state inspected in this session (root README/plan plus docs/*). Objective: consolidate documentation into authoritative sources (ADRs, changelog, backlog), remove drift, and enforce governance around Markdown assets and pipelines.

## Updates this run (2025-11-21)
- Project CI workflow now builds a consolidated summary (tests, JaCoCo line coverage, SpotBugs counts) via `scripts/build_project_ci_summary.py` and publishes it to the run summary + `project-ci-summary` artifact.
- Per-repo summary records now include stable artifact names and matrix identifiers so aggregation works across all repos in `config/repositories.yaml`.
- Mutation/CI matrices remain manifest-driven (`config/repositories.yaml`), keeping python/java repos in lockstep; PyYAML/defusedxml are installed where needed to unblock runs.
- Remaining gaps are documented below (e.g., richer metrics parsing, unifying security/workflow lint runners, and moving more jobs to the manifest).

## Key Findings
- Readiness/confidence signals now align between `README.md`, `docs/status/honest-status.md`, and `docs/analysis/index.md`; keep them in lockstep when numbers change.
- Doc index review dates were placeholders; they’re now filled, but regeneration + CI enforcement are still needed to prevent regressions.
- Non-doc Markdown drift: `data/README.md` omits the DR/provenance fixtures actually present; `data-quality-and-dr/README.md` understates `dr_recall.sh`; `policies/egress-allowlist.md` contains placeholder hosts/ports and needs real allowlist entries.
- Generated + vendor assets need clear non-SoT markings: `artifacts/**`, `models/target/**`, `tmp/**` are now tagged “generated” in `audit-index.md` but still appear under the repo tree; vendor dbt packages are tagged “yes”. Treat them as read-only when consolidating.
- Backlog/changelog exist now, but `docs/backlog.md` uses placeholder Issue URLs (1–23). Replace with real GitHub Issue links or IDs when available and keep the root `CHANGELOG.md` as the only changelog.

## CI/CD workflow audit (python + java focus)
- Manifest-driven workflows: `project-ci.yml` (lint/test per repo + aggregated summary) and `mutation.yml` (pytest or PIT via manifest; installs PyYAML/defusedxml). Repos tracked in `config/repositories.yaml`.
- Single-repo workflows still scoped to this hub: `unit.yml`, `security-lint.yml`, `tools-ci.yml`, `chaos.yml`, `dr-drill.yml`, `schema-ci.yml`, `kyverno-e2e.yml`, `rekor-monitor.yml`, `sign-digest.yml`, `update-action-pins.yml`, `cross-time-determinism.yml`. Decide which should become manifest-driven versus remain hub-only.
- Gaps: project summary does not yet parse coverage/mutation/SpotBugs severities per repo; Python coverage is not captured; Java dep-check relies on `NVD_API_KEY` secret; CodeQL is hub-only.
- Duplication risk: multiple workflows run overlapping lint/test steps; need a single promotion path (lint → unit → mutation) with fan-out per repo + a shared summary artifact.
- Artifact hygiene: summaries now publish to `project-ci-summary` but mutation summaries stay per-repo; add a roll-up once mutation + project-ci are green to show tests/coverage/mutation in one table.

## Source-of-Truth Map (proposed)
- Strategy/roadmap: `plan.md` (trim to controls + phased outcomes; demote gap tracker to backlog source).
- Current readiness: `docs/status/honest-status.md` (canonical status; historical snapshot in `docs/status/archive/implementation-2025-11-02.md`).
- Day-1 actions: `docs/start-here.md` (fix links; keep lightweight).
- Architecture/runbooks: `docs/OVERVIEW.md`, `docs/RUNNER_ISOLATION.md`, `docs/SUPPLY_CHAIN.md`, `docs/DR_RUNBOOK.md`, `docs/TESTING.md`.
- Module references: `docs/modules/*.md` + tool READMEs under `tools/**/README.md` (cross-link back to OVERVIEW/testing).
- Backlog: GitHub Issues as canonical; mirrored summary in `docs/backlog.md` (new) to group themes tied to plan phases.
- Changelog: `CHANGELOG.md` at root using Keep a Changelog; per-module changelog snippets roll up here.
- Decisions: `docs/adr/*.md` (ADR-0001… with template owner/date/status).

## Consolidation & Cleanup Plan
1) Fix broken/missing references
   - Update `plan.md`, `README.md`, `docs/start-here.md`, `docs/analysis/index.md`, and `docs/status/*.md` to point to the live files (GitHub Issues instead of `issues.md`; lowercase `docs/start-here.md`; remove calls to `ANALYSIS_INDEX.md`/`MULTI_REPO_IMPLEMENTATION_STATUS.md` unless recreated).
   - Replace `docs/index.md` placeholders with real dates/status and regenerate via `scripts/docs/generate_index.sh`; wire the generator into CI.
2) Establish ADR baseline (docs/adr/)
   - Seed ADRs immediately:
     - ADR-0001 Supply-chain trust boundary (SHA-pinned actions, cosign/Rekor, SBOM/VEX referrers, evidence bundle signing).
     - ADR-0002 Multi-repo isolation model (matrix + proxy allowlists today; roadmap to per-repo secrets, fairness, self-hosted runners).
     - ADR-0003 Determinism & evidence gating (dual-build diff policy, cross-time workflow disposition, evidence bundle as OCI artifact).
     - ADR-0004 Docs governance (SoT map, lint rules, required index/regeneration in CI).
   - Template fields: Context, Decision, Consequences, Status (Proposed/Accepted), Owners, Links to plan/workflows.
3) Create single changelog
   - Add root `CHANGELOG.md` (Keep a Changelog format); backfill entries for v1.0.10 snapshot and notable changes listed in `plan.md` gap tracker and README status history.
   - Stop per-doc ad-hoc changelog sections; link them to the root changelog.
4) Normalize backlog handling
   - Create `docs/backlog.md` that groups work by theme (supply chain, determinism, multi-repo isolation, observability). Each item links to GitHub Issues; mark source (plan gap tracker, docs/TODO).
   - Migrate `docs/TODO.md` items into GitHub Issues with labels; leave TODO.md as a pointer or remove once empty.
   - Remove/replace all references to `issues.md` with GitHub Issues URLs.
5) Reconcile readiness/status
   - Choose `docs/status/honest-status.md` as the readiness SoT; update figures to match current evidence; keep historical snapshot only in `docs/status/archive/implementation-2025-11-02.md`.
   - Ensure README’s status block pulls from the same numbers and caveats as honest-status; avoid marketing claims in analysis docs.
6) Document/navigation hygiene
   - Trim `docs/analysis/index.md` to a short nav that links only to existing files; move long-form analysis to an “Appendix” section in `plan.md` or a dedicated `docs/analysis/README.md`.
   - Remove or archive `.doc-link-backup-*` directories from STRUCTURE/index outputs; exclude transient directories in the generator config.
   - Populate empty directories (`docs/audit`, `docs/reference`, `docs/versions`) or remove them; keep `docs/audit` for future evidence audits if needed.
7) Automation & linting
   - Enforce Markdown linting + link check in CI (`scripts/docs/check_orphan_docs.py`, `scripts/docs/update_doc_links.sh` or markdownlint + lychee equivalent).
   - Add a docs governance checklist to PR template: regenerate `STRUCTURE.md`/`docs/index.md`, update changelog/backlog/ADR if decision or scope changes, refresh status date.

## Immediate Next Steps (order)
- Regenerate `docs/index.md` with real review dates/status and add a CI guard; re-run `scripts/docs/generate_index.sh` + `generate_structure.sh`.
- Reconcile readiness narratives: rewrite `docs/analysis/index.md` to match `docs/status/honest-status.md`/README and remove conflicting percentages or hour estimates.
- Update non-doc drift: refresh `data/README.md`, `data-quality-and-dr/README.md`, and `policies/egress-allowlist.md` with accurate paths/hosts and call out source-of-truth locations.
- Decide handling for generated Markdown: add “Generated – not SoT” banners to `artifacts/**/summary.md` or relocate under `generated/`; keep tagged as generated in `audit-index.md`.
- Replace placeholder Issue links in `docs/backlog.md` with real GitHub Issues; keep root `CHANGELOG.md` as the single changelog.
- Add ADR-0004 (determinism + docs governance) if the decision is already made; otherwise note status in `docs/adr/README.md`.

## Acceptance Criteria for “docs organized”
- One SoT per concern: roadmap (`plan.md`), readiness (`docs/status/honest-status.md`), day-1 steps (`docs/start-here.md`), changelog (`CHANGELOG.md`), backlog (`docs/backlog.md` + real Issues), decisions (`docs/adr/`), module references (`docs/modules` + tool READMEs).
- No broken or missing links in Markdown; `scripts/docs/check_orphan_docs.py` passes.
- README status and `docs/status/honest-status.md` match exactly (date, % readiness, gating conditions).
- ADRs exist for the core design choices above and are referenced from README/plan.
- Doc index/structure generated without backup noise; empty directories removed or populated with an intent README.
- Full-file index available at `audit-index.md` with type/vendor/generated tags for every file; use it to drive consolidation.

## Execution checklist (do this next)
- [x] Refresh `audit-index.md` with vendor/generated tagging (2025-11-21) and rerun orphan check.
- [x] Standardize module/tool READMEs to the shared template; cross-links back to `docs/OVERVIEW.md` and `docs/TESTING.md` in place.
- [x] Link `docs/backlog.md` items to GitHub Issues (currently example URLs 1–23; replace with real Issues).
- [x] Regenerate `docs/index.md` with real review dates/status; add CI guard to fail on placeholders/Unknown.
- [x] Reconcile readiness narrative: trim `docs/analysis/index.md` to nav + align % figures with `docs/status/honest-status.md` and the README.
- [x] Fix non-doc drift: update `data/README.md`, `data-quality-and-dr/README.md`, and `policies/egress-allowlist.md` with real paths/hosts; mark `artifacts/**` summaries as generated/non-SoT.
- [x] Re-run `scripts/docs/generate_index.sh` and `scripts/docs/generate_structure.sh` after fixes; rerun orphan/link checks.

## Directory-by-directory audit (Markdown + generated notes)
- root (`README.md`, `plan.md`, `STRUCTURE.md`, `CHANGELOG.md`, `audit.md`): canonical; keep README status in lockstep with `docs/status/honest-status.md`.
- docs/: doc index still stale (“Unknown” review dates); `docs/analysis/index.md` conflicts with honest-status; backlog linked but URLs are placeholders; ADRs present (0001–0003).
- docs/status/archive/: historical snapshot only; banner present.
- docs/modules/ + tools/: standardized templates applied and cross-linked; keep synced when logic changes.
- policies/ (`README.md`, `egress-allowlist.md`): README aligns with policy files; egress list uses example hosts—replace with real allowlist and note source of truth.
- deploy/kyverno/: README matches `scripts/deploy_kyverno.sh`/`verify_kyverno_enforcement.sh`; includes new `install.yaml`.
- data/: README outdated (only mentions `multi.jsonl`/`test.jsonl`); directory now holds `data/dr/*` and `data/artifacts/dr/restore/*` fixtures—document these and their consumers.
- data-quality-and-dr/: README labels `dr_recall.sh` as placeholder but the script restores + hashes backups; clarify usage and link to DR runbook.
- supply-chain-enforce/: README consistent with release workflow; keep references to `tools/publish_referrers.sh` and `kyverno/verify-images.yaml`.
- artifacts/: `*/summary.md` are generated; tagged as `generated` in `audit-index.md`—treat as non-SoT or move under a `generated/` prefix.
- tmp/: scratch/generated content tagged in `audit-index.md`; keep ignored from SoT.
- models/dbt_packages/dbt_utils/*: vendored; do not edit, mark as third-party in governance.
