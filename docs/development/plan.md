# CI/CD Hub Development Plan

> **Single source of truth** for project status, priorities, and remaining work.
>
> **See also:** `REUSABLE_WORKFLOW_MIGRATION.md` for detailed technical implementation.
>
> **Last Updated:** 2025-12-23
> **Version Target:** v1.0.0

---

## Current Status

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Central Mode (`hub-run-all.yml`) | **PASSING** | Full tool coverage, 5m35s runs |
| Reusable Workflows | Working | `python-ci.yml`, `java-ci.yml` with `workflow_call` |
| Caller Templates | Working | `hub-python-ci.yml`, `hub-java-ci.yml` |
| Schema Validation | Working | `config-validate.yml` workflow |
| CLI Tool (`cihub`) | **v0.1.0** | 5 commands: detect/init/update/validate/setup-secrets |
| Tests | **80 tests** | 6 test files covering all scripts |
| ADRs | **20 ADRs** | 0001 through 0020 complete |
| Smoke Test | **PASSING** | Last run: 2025-12-22 |

### What's Broken

| Component | Status | Issue |
|-----------|--------|-------|
| Hub Orchestrator | **FAILING** | Schedule and push triggers failing (needs investigation) |
| Hub Security | **FAILING** | Security workflow also failing |

### Workflow Health (2025-12-23)

```
Hub: Run All Repos     PASSING  (5m35s)
Smoke Test             PASSING  (1m30s)
Hub Self-Check         PASSING  (20s)
Validate Hub Configs   PASSING  (13s)
Hub Orchestrator       FAILING  (schedule + push)
```

---

## P0 Checklist (Ship-Ready)

All P0 items complete. See `requirements/P0.md` for details.

- [x] Central mode clones and tests repos
- [x] Java CI (Maven/Gradle support)
- [x] Python CI (pytest, coverage)
- [x] Config hierarchy (defaults → repo config → .ci-hub.yml)
- [x] Schema validation (fail fast on bad YAML)
- [x] Step summaries with metrics
- [x] Artifact uploads
- [x] Documentation (WORKFLOWS, CONFIG_REFERENCE, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING)
- [x] Templates (12 profiles: java/python × minimal/fast/quality/coverage-gate/compliance/security)
- [x] Smoke test verified

**P0 Blockers:** None

---

## P1 Checklist (Should-Have)

- [x] ADRs: 20 complete (0001-0020)
- [x] Profiles/templates: 12 profiles complete
- [x] Fixtures: `ci-cd-hub-fixtures` repo with passing/failing examples
- [x] CLI: `cihub` v0.1.0 with detect/init/update/validate/setup-secrets
- [ ] CLI: validate `setup-secrets` token trim/verify with a real dispatch run
- [ ] Dashboard: GitHub Pages site (HTML exists, needs deployment)
- [x] Orchestrator fix: Input passthrough complete (mutation_score_min, run_hypothesis, run_jqwik, all max_* thresholds)
- [ ] Refactor: Move inline Python from workflows to scripts/
- [ ] Composite actions: Reduce java-ci.yml + python-ci.yml duplication
- [ ] CODEOWNERS: Protect workflows/config/schema/templates
- [ ] Integration tests: `act` or similar for workflow testing

---

## Blocking Issues for v1.0.0

### 1. Hub Orchestrator Failing

**Impact:** Distributed mode doesn't work reliably.

**Note:** Input passthrough is COMPLETE (mutation_score_min, run_hypothesis, run_jqwik, all max_* thresholds are passed). The failure is something else - needs investigation.

### 2. Hub Security Workflow Failing

Security scan workflow also failing. Needs investigation.

### 3. Report Schema ✅ Complete

All fields now implemented:
- `tools_ran` includes hypothesis (Python) and jqwik (Java)
- `tool_metrics` includes mypy_errors
- Schema version 2.0 emitted by both workflows

---

## Architecture

### Config Hierarchy (Highest Wins)

```
1. Repo's .ci-hub.yml        ← Highest priority
2. Hub's config/repos/<repo>.yaml
3. Hub's config/defaults.yaml ← Lowest priority
```

### Two Operating Modes

| Mode | Description | Status |
|------|-------------|--------|
| **Central** | Hub clones repos, runs tests directly | **Default, Working** |
| **Distributed** | Hub dispatches to repo workflows | Partial (orchestrator issues) |

### ADRs

20 ADRs document all major decisions. See `docs/adr/README.md`.

Key decisions:
- ADR-0001: Central mode is default
- ADR-0002: Config precedence (repo wins)
- ADR-0014: Reusable workflow migration
- ADR-0019: Report validation policy
- ADR-0020: Schema backward compatibility

---

## Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test_config_pipeline.py` | 5 | Config loading |
| `test_apply_profile.py` | 19 | Profile merging |
| `test_templates.py` | 16 | Template validation |
| `test_aggregate_reports.py` | 28 | Report aggregation |
| `test_cihub_cli.py` | 7 | CLI functions |
| `test_contract_consistency.py` | 5 | Schema contracts |
| **Total** | **80** | |

Run: `pytest tests/`

---

## Scripts

| Script | Purpose | Documented |
|--------|---------|------------|
| `load_config.py` | Load/merge configs | Yes |
| `validate_config.py` | Schema validation | Yes |
| `aggregate_reports.py` | Report aggregation | Yes |
| `apply_profile.py` | Apply profile to config | Yes |
| `verify_hub_matrix_keys.py` | Matrix key verification | Partial |
| `debug_orchestrator.py` | Debug artifact downloads | Yes |

---

## Remaining Work (Priority Order)

### High Priority
1. **Fix Hub Orchestrator** - Investigate why schedule/push triggers fail
2. **Fix Hub Security** - Investigate why security workflow fails
3. **Complete report schema** - Add hypothesis/jqwik to tools_ran, mypy_errors to tool_metrics
4. **Dashboard deployment** - GitHub Pages setup

### Medium Priority
5. **CLI completion** - Add `add`, `list`, `lint`, `apply` commands
6. **Composite actions** - Reduce workflow duplication
7. **CODEOWNERS** - Protect critical paths

### Low Priority
8. **Integration tests** - Workflow testing with `act`
9. **Docker templates** - Separate `hub-*-docker.yml` (deferred to v1.1.0)

---

## v1.0.0 Scope

**Included:**
- Reusable workflows (`python-ci.yml`, `java-ci.yml`, `kyverno-ci.yml`)
- Caller templates (`hub-python-ci.yml`, `hub-java-ci.yml`)
- Report schema 2.0
- CLI v0.1.0 (`cihub`) with 5 commands
- 80 tests across 6 files
- 20 ADRs

**Deferred to v1.1.0:**
- Dashboard/GitHub Pages
- Docker templates
- CLI `add/list/lint/apply` commands
- Full fixture expansion (16+ planned)

---

## Quick Links

| Resource | Path |
|----------|------|
| Requirements | `requirements/P0.md`, `requirements/P1.md` |
| ADRs | `docs/adr/` |
| Schema | `schema/ci-hub-config.schema.json` |
| Fixtures | `ci-cd-hub-fixtures` repo |
| Smoke Test | `docs/development/SMOKE_TEST_SETUP_SUMMARY.md` |

---

## Notes

- Keep checkboxes honest - only mark `[x]` after verification
- AGENTS.md should reflect current focus from this plan
- Run smoke test after significant workflow changes

