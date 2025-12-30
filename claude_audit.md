# CI/CD Hub - Comprehensive Audit Report

**Date:** 2025-12-30
**Scope:** Full codebase audit for stale references, inconsistencies, and alignment issues.
**Status:** Audit complete - actionable items identified.

---

## Executive Summary

8 parallel agents audited every area of the codebase. Key findings:

| Area | Issues Found | Critical | Action Required |
|------|--------------|----------|-----------------|
| docs/ | 3 issues | 1 (MODES.md) | Fix outdated notes |
| templates/ | 3 issues | 1 (trivy field) | Fix schema violations |
| cihub/ CLI | 12 patterns | 0 | Refactor for consistency |
| .github/workflows/ | 9 categories | 2 | Standardize configs |
| config/ | 7 issues | 1 (language field) | Fix schema violations |
| tests/ | 0 issues | 0 | ✅ Clean |
| scripts/ & schema/ | 0 issues | 0 | ✅ Clean |
| Root files | 2 issues | 0 | Update stale notes |

---

## Verified Facts (From Repo)

- Tracked files: 392 (via `git ls-files`)
- Top-level tracked directories: 14 (`.github`, `_quarantine`, `badges`, `cihub`, `config`, `dashboards`, `docs`, `policies`, `pyqt`, `requirements`, `schema`, `scripts`, `templates`, `tests`)
- Workflows: 14 files in `.github/workflows/`
- Docs: 72 Markdown files in `docs/`
- ADRs: 35 files in `docs/adr/`
- Guides: 10 files in `docs/guides/`
- Config repos: 25 files in `config/repos/`
- Scripts: 16 files in `scripts/`

---

## CRITICAL ISSUES (Fix Immediately)

### 1. Config Schema Violation: `language` Field Location

**Severity:** CRITICAL
**Files Affected:** ALL 24 repo configs in `config/repos/*.yaml`

**Problem:** According to `schema/ci-hub-config.schema.json`, `language` is a required root-level property, but all repo configs have `language` nested under the `repo` object.

**Current (WRONG):**
```yaml
repo:
  owner: jguida941
  name: ci-cd-hub-fixtures
  language: java    # WRONG - nested under repo
```

**Expected (CORRECT):**
```yaml
repo:
  owner: jguida941
  name: ci-cd-hub-fixtures
language: java      # CORRECT - root level
```

---

### 2. Invalid Trivy Field in Templates

**Severity:** CRITICAL
**Files:**
- `templates/repo/.ci-hub.yml` (Line 49)
- `templates/hub/config/repos/repo-template.yaml` (Line 35)

**Problem:** Uses `fail_on_cvss: 7` instead of schema-defined `fail_on_high: true`

**Current (WRONG):**
```yaml
trivy:
  enabled: false
  fail_on_cvss: 7  # Invalid field!
```

**Schema expects:** `fail_on_critical` (boolean) and/or `fail_on_high` (boolean)

---

### 3. MODES.md Outdated Hybrid Mode Note

**Severity:** HIGH
**File:** `docs/guides/MODES.md` (Line 284)

**Current:** "Hybrid mode configuration is planned but not yet implemented"

**Reality:** Hybrid mode IS implemented via `repo.use_central_runner` field.

**Fix:** Update to reflect current implementation.

---

## HIGH PRIORITY ISSUES

### 4. Missing Dispatch Fields in Monorepo Template

**File:** `templates/hub/config/repos/monorepo-template.yaml`

**Problem:** Missing `dispatch_enabled`, `dispatch_workflow`, `use_central_runner`, `repo_side_execution` fields that are present in `repo-template.yaml`.

---

### 5. Workflow Config Loading Inconsistency

**Problem:** Three different patterns for loading config:
- `hub-ci.yml`: Uses `cihub config-outputs` command
- `hub-run-all.yml`: Uses inline Python to parse config
- `hub-orchestrator.yml`: Uses inline Python to parse config

**Recommendation:** Centralize config loading into single CLI command.

---

### 6. Hardcoded Owner in hub-orchestrator.yml

**File:** `.github/workflows/hub-orchestrator.yml` (Line 114)
**Problem:** Default owner hardcoded to "jguida941"

---

### 7. Mutmut Field Name Error

**File:** `config/repos/ci-cd-bst-demo-github-actions.yaml` (Line 30)
**Problem:** Uses `min_score` instead of schema-defined `min_mutation_score`

---

## MEDIUM PRIORITY ISSUES

### 8. WORKFLOWS.md Stale Implementation Status

**File:** `docs/guides/WORKFLOWS.md` (Line 290)
**Problem:** Says "repo-local merge planned" but it's already implemented.

---

### 9. CLI Code Duplication

**Files:** `cihub/commands/init.py` and `cihub/commands/update.py`
**Problem:** Identical `repo_side_execution` extraction logic duplicated.

---

### 10. `use_central_runner` Never Used

**Finding:** Field is collected in wizard/core.py (Line 60-67) but never actually used to control runner behavior.

---

### 11. Action Version Comment Inconsistencies

**Files:** Multiple workflows
**Problem:** Same actions have different version comments (e.g., `# v5` vs `# v5.6.0` for setup-python)

---

### 12. Stale Migration Code in templates.py

**File:** `cihub/commands/templates.py` (Lines 114-162)
**Problem:** Workflow cleanup logic for old templates should be feature-flagged.

---

## LOW PRIORITY ISSUES

### 13. Disabled Config with Stale Template Reference

**File:** `config/repos/contact-suite-spring-react.yaml.disabled`
**Problem:** References deprecated `java-ci-dispatch.yml`

---

### 14. Docker Configs Missing Explicit dockerfile Field

**Files:** 5 repo configs with docker enabled but no explicit `dockerfile` property.
**Note:** Not critical as schema has default value.

---

### 15. Optional Configs Undocumented in Examples

**Problem:** No example repo configs showing how to enable optional features (chaos, dr-drill, etc.)

---

## CLEAN AREAS (No Issues Found)

✅ **tests/** - Fully updated with new field names, no stale patterns
✅ **scripts/** - All new fields properly integrated
✅ **schema/** - Complete and correct field definitions
✅ **ADRs** - Properly marked as superseded where applicable

---

## ADR Alignment Needed

These ADRs reference old workflow entrypoints or fixture strategy:

- Workflow entrypoint updates: `0003`, `0009`, `0011`, `0014`, `0017`, `0023`, `0031`
- Fixtures/testing strategy: `0008`, `0018`

---

## Scope Guardrails (To Avoid Drift)

1. **No deletions** (folders or docs) until ADR alignment is complete.
2. **Update ADRs first**, then update status docs, then consider consolidation.
3. **CLI is authoritative**; docs should describe the CLI, not replace it.
4. **Avoid large refactors** (renames, `src/` move, etc.) until the workflow migration stabilizes.
5. **`_quarantine/`** - Keep for future reintegration (per plan).
6. **`dashboards/`, `badges/`, `requirements/`, `policies/`** - Keep (actively referenced).

---

## Recommended Fix Order

### Immediate (P0)
1. Fix `language` field location in all 24 config/repos/*.yaml files
2. Fix `trivy.fail_on_cvss` → `trivy.fail_on_high` in templates
3. Update MODES.md hybrid mode note

### High Priority (P1)
4. Add missing dispatch fields to monorepo-template.yaml
5. Centralize workflow config loading into CLI command
6. Fix mutmut `min_score` → `min_mutation_score`
7. Remove hardcoded owner from hub-orchestrator.yml

### Medium Priority (P2)
8. Update WORKFLOWS.md stale implementation note
9. Refactor duplicated repo_side_execution logic
10. Feature-flag migration code in templates.py
11. Standardize action version comments

### Low Priority (P3)
12. Update disabled config file when re-enabled
13. Add optional feature examples
14. Either implement or remove `use_central_runner` logic

---

## Next Steps

1. Review this audit with stakeholder
2. Create GitHub issues for P0/P1 items
3. Fix critical issues before next release
4. Add ADR update notes (2025-12-30) to affected ADRs
5. Consider doc automation tools (Swimm, sphinx-click) to prevent future drift
