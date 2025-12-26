# Integration Status

> Track graduation of files from `_quarantine/` to their final locations in `cihub/`.
>
> **Rule:** Files only leave quarantine when ALL checkboxes in their row are checked.

## Legend

| Column | Meaning |
|--------|---------|
| Copied | File exists in `_quarantine/` |
| Target | Final location (decided) |
| Imports | Imports fixed for new location |
| Tests | Unit tests pass |
| Wired | Added to CLI (if applicable) |
| Done | Graduated via `git mv` |

---

## Phase 0: Utils (Graduate First - No Dependencies)

These are foundational utilities that other tools depend on.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `safe_subprocess.py` | ☐ | `cihub/utils/` | ☐ | ☐ | N/A | ☐ | **PILOT** - Graduate first |
| `derive_dr_current_time.py` | ☐ | `cihub/utils/` | ☐ | ☐ | N/A | ☐ | Time utility for DR |

---

## Phase 1: Supply Chain (Depends on Utils)

SLSA provenance, SBOM, VEX, signing, Rekor.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `provenance_io.py` | ☐ | `cihub/tools/provenance/` | ☐ | ☐ | ☐ | ☐ | Read/write SLSA envelopes |
| `normalize_provenance.py` | ☐ | `cihub/tools/provenance/` | ☐ | ☐ | ☐ | ☐ | Normalize formats |
| `verify_provenance.py` | ☐ | `cihub/tools/provenance/` | ☐ | ☐ | ☐ | ☐ | Verify signatures |
| `export_provenance_envelope.py` | ☐ | `cihub/tools/provenance/` | ☐ | ☐ | ☐ | ☐ | Export to file |
| `generate_vex.py` | ☐ | `cihub/tools/vex/` | ☐ | ☐ | ☐ | ☐ | VEX document generation |
| `build_vuln_input.py` | ☐ | `cihub/tools/vex/` | ☐ | ☐ | ☐ | ☐ | Vulnerability input builder |
| `build_issuer_subject_input.py` | ☐ | `cihub/tools/provenance/` | ☐ | ☐ | ☐ | ☐ | SLSA issuer/subject |
| `rekor_monitor.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Rekor transparency log |
| `publish_referrers.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | OCI referrers |
| `sign_evidence_bundle.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Cosign signing |
| `cache_provenance.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Provenance caching |

---

## Phase 2: Resilience (Depends on Supply Chain, Utils)

Chaos testing and disaster recovery.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `run_chaos.py` | ☐ | `cihub/tools/chaos/` | ☐ | ☐ | ☐ | ☐ | Chaos test runner |
| `run_dr_drill.py` | ☐ | `cihub/tools/dr/` | ☐ | ☐ | ☐ | ☐ | DR drill runner |
| `dr_drill/*.py` | ☐ | `cihub/tools/dr/` | ☐ | ☐ | ☐ | ☐ | DR drill modules |
| `chaos/chaos-fixture.json` | ☐ | `config/chaos/` | N/A | N/A | N/A | ☐ | Config file |

---

## Phase 3: Performance (Depends on Utils)

Cache optimization and predictive scheduling.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `cache_sentinel.py` | ☐ | `cihub/tools/cache/` | ☐ | ☐ | ☐ | ☐ | Cache quarantine |
| `predictive_scheduler.py` | ☐ | `cihub/tools/scheduler/` | ☐ | ☐ | ☐ | ☐ | ML-based scheduling |
| `emit_cache_quarantine_event.py` | ☐ | `cihub/tools/cache/` | ☐ | ☐ | ☐ | ☐ | Telemetry events |
| `generate_scheduler_reports.py` | ☐ | `cihub/tools/scheduler/` | ☐ | ☐ | ☐ | ☐ | Scheduler reports |

---

## Phase 4: Policy (Depends on Utils)

Kyverno and OPA/Rego policy enforcement.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `kyverno_policy_checker.py` | ☐ | `cihub/tools/policy/` | ☐ | ☐ | ☐ | ☐ | Kyverno validation |
| `prepare_policy_inputs.py` | ☐ | `cihub/tools/policy/` | ☐ | ☐ | ☐ | ☐ | Policy input prep |
| `deploy_kyverno.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Kyverno deployment |
| `deploy_kyverno_policies.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Policy deployment |
| `run_kyverno_kind.sh` | ☐ | `cihub/tools/scripts/` | ☐ | ☐ | ☐ | ☐ | Kind cluster testing |
| `policies/*.rego` | ☐ | `policies/` | N/A | ☐ | N/A | ☐ | OPA policies |
| `deploy/kyverno/*.yaml` | ☐ | `deploy/kyverno/` | N/A | N/A | N/A | ☐ | K8s manifests |

---

## Phase 5: Analysis (Depends on Utils)

Mutation testing and failure analysis.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `mutation_observatory.py` | ☐ | `cihub/tools/mutation/` | ☐ | ☐ | ☐ | ☐ | Mutation analysis |
| `autopsy/*.py` | ☐ | `cihub/autopsy/` | ☐ | ☐ | ☐ | ☐ | Failure analysis |

---

## Phase 6: Ingestion (Depends on Utils)

Telemetry and data ingestion.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `chaos_dr_ingest.py` | ☐ | `cihub/ingestion/` | ☐ | ☐ | ☐ | ☐ | BigQuery ingest |
| `event_loader.py` | ☐ | `cihub/ingestion/` | ☐ | ☐ | ☐ | ☐ | Event loading |
| `consolidate_telemetry.py` | ☐ | `cihub/ingestion/` | ☐ | ☐ | ☐ | ☐ | Telemetry consolidation |
| `emit_pipeline_run.py` | ☐ | `cihub/ingestion/` | ☐ | ☐ | ☐ | ☐ | Pipeline run events |
| `record_job_telemetry.py` | ☐ | `cihub/ingestion/` | ☐ | ☐ | ☐ | ☐ | Job telemetry |

---

## Phase 7: Validators (Depends on Utils)

Security and integrity checks.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `check_runner_isolation.py` | ☐ | `cihub/validators/` | ☐ | ☐ | ☐ | ☐ | Runner budget check |
| `check_schema_registry.py` | ☐ | `cihub/validators/` | ☐ | ☐ | ☐ | ☐ | Schema validation |
| `check_workflow_integrity.py` | ☐ | `cihub/validators/` | ☐ | ☐ | ☐ | ☐ | Workflow integrity |
| `enforce_concurrency_budget.py` | ☐ | `cihub/validators/` | ☐ | ☐ | ☐ | ☐ | Concurrency limits |

---

## Phase 8: Security Scripts (Standalone)

Shell scripts for security enforcement.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `scan_runtime_secrets.sh` | ☐ | `cihub/tools/scripts/` | N/A | ☐ | ☐ | ☐ | Secret scanning |
| `enforce_egress_control.sh` | ☐ | `cihub/tools/scripts/` | N/A | ☐ | ☐ | ☐ | Egress enforcement |
| `github_actions_egress_wrapper.sh` | ☐ | `cihub/tools/scripts/` | N/A | ☐ | ☐ | ☐ | Egress wrapper |
| `determinism_check.sh` | ☐ | `cihub/tools/scripts/` | N/A | ☐ | ☐ | ☐ | Build determinism |

---

## Phase 9: Runners & Misc Scripts

Other execution scripts.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `resolve_container_digest.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | Container resolution |
| `ephemeral_data_lab.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | Ephemeral testing |
| `run_dbt.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | dbt execution |
| `load_projects.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | Project loading |
| `load_repository_matrix.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | Repo matrix |
| `capture_canary_decision.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | Canary decisions |
| `build_project_ci_summary.py` | ☐ | `cihub/runners/` | ☐ | ☐ | ☐ | ☐ | CI summary |
| `install_tools.sh` | ☐ | `scripts/` | N/A | N/A | N/A | ☐ | Tool installation |

---

## Phase 10: Config & Data Files

Static configuration and data files.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `models/*.yml` | ☐ | `models/` | N/A | N/A | N/A | ☐ | dbt models |
| `dashboards/*.json` | ☐ | `dashboards/` | N/A | N/A | N/A | ☐ | Grafana dashboards |
| `data/*.yaml` | ☐ | `data/` | N/A | N/A | N/A | ☐ | Data files |
| `.bandit*.yaml` | ☐ | `.` | N/A | N/A | N/A | ☐ | Bandit config |
| `.markdownlint*` | ☐ | `.` | N/A | N/A | N/A | ☐ | Markdown lint config |

---

## Phase 11: Documentation

Docs that need consolidation.

| File | Copied | Target | Imports | Tests | Wired | Done | Notes |
|------|:------:|--------|:-------:|:-----:|:-----:|:----:|-------|
| `docs/SUPPLY_CHAIN.md` | ☐ | `docs/guides/` | N/A | N/A | N/A | ☐ | Supply chain guide |
| `docs/DR_RUNBOOK.md` | ☐ | `docs/guides/` | N/A | N/A | N/A | ☐ | DR runbook |
| `docs/SECURITY.md` | ☐ | `docs/guides/` | N/A | N/A | N/A | ☐ | Security guide |
| `docs/adr/*.md` | ☐ | `docs/adr/` | N/A | N/A | N/A | ☐ | Merge with existing |

---

## Summary

| Phase | Files | Status | Blocker |
|-------|-------|--------|---------|
| 0: Utils | 2 | Not started | None |
| 1: Supply Chain | 11 | Not started | Phase 0 |
| 2: Resilience | 4 | Not started | Phase 1 |
| 3: Performance | 4 | Not started | Phase 0 |
| 4: Policy | 7 | Not started | Phase 0 |
| 5: Analysis | 2+ | Not started | Phase 0 |
| 6: Ingestion | 5 | Not started | Phase 0 |
| 7: Validators | 4 | Not started | Phase 0 |
| 8: Security Scripts | 4 | Not started | None |
| 9: Runners | 8 | Not started | Phase 0 |
| 10: Config | 5+ | Not started | None |
| 11: Documentation | 5+ | Not started | None |

**Total:** ~60+ files across 12 phases

---

## Graduation Checklist (For Each File)

Before moving a file out of `_quarantine/`:

1. [ ] Target directory exists in `cihub/`
2. [ ] All imports updated (absolute paths)
3. [ ] No circular dependencies
4. [ ] Unit tests pass
5. [ ] Ruff lint passes
6. [ ] Type hints added (if missing)
7. [ ] Docstring present
8. [ ] Added to `__init__.py` exports
9. [ ] CLI command added (if applicable)
10. [ ] Schema updated (if new config key)
11. [ ] Committed with `feat(integration): graduate <file>`

---

## Notes

- **Start with Phase 0** - utils have no deps, everything else needs them
- **Parallel work:** Phases 8, 10, 11 can happen anytime (no Python deps)
- **Biggest risk:** Phase 1 (supply chain) has most interconnected files
- **CLI wiring:** Save for last - files work before CLI exposes them
