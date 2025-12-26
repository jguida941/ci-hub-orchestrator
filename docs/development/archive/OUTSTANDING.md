# Outstanding Work (CI/CD Hub)

> **Status:** Legacy archive (2025-12-15). This document is retained for historical context only and must not be used as current guidance.

**Last Updated:** 2025-12-15

## Fix First (Priority Queue)

1. **Test coverage** - Expand from 39 tests to 80+ tests
2. **Orchestrator** - Use `scripts/load_config.py --output workflow-inputs` to inject run_* flags into matrix
3. **Hub-run-all matrix** - Replace grep parsing with single Python load for deterministic matrix building

---

## Completed Since Last Review

- [x] `scripts/load_config.py`: emits run flags for all tools (Java: jacoco/checkstyle/spotbugs/owasp/pitest/pmd/semgrep/trivy; Python: pytest/ruff/bandit/pip_audit/black/isort/mypy/mutmut/hypothesis/semgrep/trivy), thresholds, run_group, dispatch
- [x] `.github/workflows/hub-run-all.yml`: tool steps gated on run_* flags; mutmut TOTAL default; PITest search is repo-wide; Semgrep/Trivy gated by flags
- [x] `schema/ci-hub-config.schema.json`: tightened (additionalProperties: false, required repo/language, subdir pattern, run_group enum, language conditionals, full tool definitions, bounded thresholds)
- [x] Dispatch templates created: `templates/java/java-ci-dispatch.yml`, `templates/python/python-ci-dispatch.yml`
- [x] All 13 ADRs written and documented
- [x] Kyverno guide, ADR, and validation workflow added
- [x] Documentation: DISPATCH_SETUP.md, MODES.md, TOOLS.md, CONFIG_REFERENCE.md all complete
- [x] Fixtures repo published (`ci-cd-hub-fixtures`) with passing/failing examples

## Open Fixes to Implement

### High Priority
- [ ] **Orchestrator improvements**: Use `scripts/load_config.py --output workflow-inputs`, inject run_* flags into the matrix, gate dispatch steps on those flags (mirror hub-run-all)
- [ ] **Hub-run-all matrix**: Replace grep parsing with single Python load to build matrix entries deterministically
- [ ] **Test coverage**: Expand from 5 tests to 40+ (see `tests/test_config_pipeline.py`)

### Medium Priority
- [ ] **Reusable workflows** (`java-ci.yml`, `python-ci.yml`): add real gate evaluation (fail when thresholds/policies say so); reduce `continue-on-error` where policy requires failing
- [ ] **apply_profile determinism**: fix merge order (no set-union), document/handle list behavior, consider atomic write; optional diff/dry-run; guardrail for mismatched profile vs repo language
- [ ] **Validation flow**: validate merged configs (or partial schema for defaults/repo overrides); wrap ValidationError cleanly; safe_dump/read with UTF-8

### Low Priority (Phase 4-5)
- [ ] **Dashboard**: add per-repo metrics.json, hub-report.json aggregation, links in summaries to artifacts; optional static page for filters/trends
- [ ] **CHANGES.md**: Add changelog summarizing major changes
- [ ] **Smoke test verifier**: with set -e, guard checks or make check always return 0; avoid eval; anchor greps

## Design Decisions Documented

- **Dispatch mode**: Repo-local `.ci-hub.yml` is merged over hub config (repo wins). See ADR-0011 and ADR-0013.
- **Kyverno**: Optional feature for Kubernetes policy enforcement. See `docs/guides/KYVERNO.md` and ADR-0012.
- **Config precedence**: defaults.yaml → config/repos/*.yaml → .ci-hub.yml (repo wins). See ADR-0002.

## Testing Gaps

| Script                      | Current Coverage | Target |
|-----------------------------|------------------|--------|
| `load_config.py`            | ~30%             | 80%    |
| `validate_config.py`        | ~50%             | 80%    |
| `aggregate_reports.py`      | 0%               | 80%    |
| `apply_profile.py`          | 0%               | 80%    |
| `verify_hub_matrix_keys.py` | 0%               | 80%    |

**Current tests:** 5
**Target tests:** 40+
