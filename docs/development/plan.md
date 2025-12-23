# Execution Checklist

Links: requirements/P0.md (must-have), requirements/P1.md (should-have), requirements/nonfunctional.md (quality targets).

## P0 Focus (ship-ready)
- [x] Dispatch fixes: pass computed inputs, honor `default_branch`, add `actions: write`/`contents: read`, fail on dispatch errors, capture run IDs. (refs: requirements/P0.md §2.1)
- [x] Aggregation: collect downstream artifacts/metrics, produce real `hub-report.json` (JSON + HTML), fail hub run on missing/failed/timeout repos. (refs: requirements/P0.md §2.2)
- [x] Schema validation: add schema checks to config loading/workflows; fail fast on bad YAML. (refs: requirements/P0.md §1.2) (config-validate workflow added, validate_config.py added)
- [x] Docs: WORKFLOWS, CONFIG_REFERENCE, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING all in place with content. (refs: requirements/P0.md §3.1)
- [x] Templates: master `.ci-hub.yml`, hub repo-template, 12 profiles (minimal/fast/quality/coverage-gate/compliance/security × Java/Python). (refs: requirements/P0.md §3.2)
- [x] Smoke test: run hub on fixtures (Java + Python passing/failing), verify pass/fail detection, artifacts, summaries. (refs: requirements/P0.md §4)

## P1 (after P0 is green)
- [x] ADRs: 8 ADRs complete (0001-central-vs-distributed, 0002-config-precedence, 0003-dispatch-orchestration, 0004-aggregation-reporting, 0005-dashboard-approach, 0006-quality-gates-thresholds, 0007-templates-and-profiles-strategy, 0008-hub-fixtures-strategy). (refs: requirements/P1.md §1)
- [x] Profiles/templates: 12 profiles complete (java/python × minimal/fast/quality/coverage-gate/compliance/security). (refs: requirements/P1.md §3)
- [x] Fixtures: jguida941/ci-cd-hub-fixtures repo created with passing/failing Java/Python projects. configs: fixtures-{java,python}-{passing,failing}.yaml (refs: requirements/P1.md §5)
- [ ] Dashboard: Pages site reading hub-report JSON; overview + drill-down. (refs: requirements/P1.md §4)
- [~] CLI: detect/init/update/validate/setup-secrets + dry-run; add/list/lint/apply still pending. (refs: requirements/P1.md §6)
- [~] Dispatch polish: agent template, correlation ID, poll, download artifacts, merge results. (refs: requirements/P1.md §7) (polling and artifact download implemented)
- [ ] Refactor inline Python from workflows into scripts/ for testability (orchestrator, hub-run-all).
- [ ] Reduce workflow duplication via composite actions/shared steps (java-ci.yml + python-ci.yml).
- [ ] Add CODEOWNERS to protect workflows/config/schema/templates.
- [ ] Add workflow integration tests (act or similar) for hub-run-all/orchestrator/reusables.

## Security/Quality Fixes Applied
- [x] Script injection vulnerability fixed (orchestrator uses env vars instead of direct interpolation)
- [x] Trivy curl-pipe-shell replaced with official action (aquasecurity/trivy-action@0.28.0)
- [x] Concurrency control added to hub-orchestrator.yml
- [x] Tool defaults documented and aligned with `config/defaults.yaml`
- [x] hashFiles() bug fixed (moved Dockerfile check to step level)

## Nonfunctional (measure as we go)
- Baseline runtime (no/with mutation), validation time, summary generation.
- Usability (time to add repo via CLI/manual, find docs, understand toggles).
- Reliability (validation accuracy, artifact upload success, dispatch failure detection).
- Retention targets for coverage/security/hub summary/dashboard data.

## Notes
- Keep checkboxes honest; only mark `[x]` after verification.
- ROADMAP should link to requirements; AGENTS should reflect current focus.
- Smoke test run recorded in `docs/development/SMOKE_TEST_SETUP_SUMMARY.md`.

## P0 Blockers
None. Smoke test completed: https://github.com/jguida941/ci-cd-hub/actions/runs/20424144678
