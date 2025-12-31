# Plan: Unify Summary Format Across ALL Workflows

## Summary Contract (Single Source of Truth)

### Scope
This contract applies to all workflow paths:
- `.github/workflows/hub-production-ci.yml` (hub infrastructure validation)
- `.github/workflows/hub-run-all.yml` (central)
- `.github/workflows/hub-orchestrator.yml` (dispatch parent)
- `.github/workflows/hub-security.yml` (security dispatch parent)
- `.github/workflows/java-ci.yml` (reusable child)
- `.github/workflows/python-ci.yml` (reusable child)

### Ownership
- Child workflows emit per-repo summaries.
- Orchestrator/security aggregate child outputs into a combined view.
- The `report` job in each reusable workflow is responsible for the consolidated per-repo summary.
- The parent aggregation uses child `report.json` artifacts as the source of truth.

### Mandatory Sections (Canonical Order)
All sections are required in all workflow modes and must appear in this order:
1. `# Configuration Summary`
2. `## Tools Enabled`
3. `## Environment`
4. `## Thresholds`
5. `## QA Metrics (Java/Python)`
6. `## Dependency Severity (Java) / Security Summary (Python)`
7. `## Quality Gates`
8. `## Run Metadata`
9. `## Config Provenance`
10. `## Workflow Health`
11. `## Environment / Build Info`
12. `## Artifacts Produced`
13. `## Compliance / Security`
14. `## Dispatch Topology`

### Summary Emission
All summaries must be written via `GITHUB_STEP_SUMMARY`. Do not mix mechanisms.

### Tools Enabled Table
**Columns:** `| Category | Tool | Configured | Ran | Success |`

**Tool rows must include these exact names:**
- Java: `JaCoCo Coverage`, `PITest`, `Checkstyle`, `PMD`, `SpotBugs`, `OWASP Dependency-Check`, `Semgrep`, `Trivy`, `jqwik`, `CodeQL`, `Docker`
- Python: `pytest`, `mutmut`, `Ruff`, `Black`, `isort`, `mypy`, `Bandit`, `pip-audit`, `Semgrep`, `Trivy`, `hypothesis`, `CodeQL`, `Docker`
- Hub Production (hub-production-ci.yml):
  - Workflow: `actionlint`, `zizmor`
  - Quality: `ruff`, `syntax`, `mypy`, `yamllint`
  - Testing: `pytest`, `mutmut`
  - Security: `bandit`, `pip-audit`, `gitleaks`, `trivy`
  - Validate: `templates`, `configs`, `matrix-keys`, `licenses`
  - Supply Chain: `dependency-review`, `scorecard`

### Boolean Contract
- **Canonical output:** summaries must emit lowercase `true` or `false`.
- **Parser compatibility:** `validate_summary.py` accepts `true/false/yes/no/1/0` for backward compatibility.

### Summary to Report Mapping
**Tools Enabled table:**
- `Configured` -> `tools_configured.{tool}`
- `Ran` -> `tools_ran.{tool}`
- `Success` -> `tools_success.{tool}`

**QA Metrics table:**
- Tests -> `results.tests_passed`, `results.tests_failed`
- Coverage -> `results.coverage`
- Mutation Score -> `results.mutation_score`
- Checkstyle -> `tool_metrics.checkstyle_issues`
- SpotBugs -> `tool_metrics.spotbugs_issues`
- PMD -> `tool_metrics.pmd_violations`
- OWASP -> `tool_metrics.owasp_critical`, `tool_metrics.owasp_high`
- Semgrep -> `tool_metrics.semgrep_findings`
- Trivy -> `tool_metrics.trivy_critical`, `tool_metrics.trivy_high`
- Ruff -> `tool_metrics.ruff_errors`
- Black -> `tool_metrics.black_issues`
- isort -> `tool_metrics.isort_issues`
- mypy -> `tool_metrics.mypy_errors`
- Bandit -> `tool_metrics.bandit_high`, `tool_metrics.bandit_medium`
- pip-audit -> `tool_metrics.pip_audit_vulns`

**Quality Gates table (derived checks):**
- Unit Tests: `results.tests_failed == 0`
- Coverage: `results.coverage >= thresholds.coverage_min`
- Mutation: `results.mutation_score >= thresholds.mutation_score_min`
- Checkstyle: `tool_metrics.checkstyle_issues <= thresholds.max_checkstyle_errors`
- SpotBugs: `tool_metrics.spotbugs_issues <= thresholds.max_spotbugs_bugs`
- PMD: `tool_metrics.pmd_violations <= thresholds.max_pmd_violations`
- OWASP: `tool_metrics.owasp_critical <= thresholds.max_critical_vulns`
- Semgrep: `tool_metrics.semgrep_findings <= thresholds.max_semgrep_findings`

### Artifact and Run Contract
- `tools_ran=true` and `tools_success=true` -> required artifact(s) must exist.
- `tools_ran=true` and `tools_success=false` -> artifacts may be missing.
- `tools_ran=false` -> artifacts must not be expected.

### Required Metadata Tables
**Run Metadata**
| Setting | Value |
|---------|-------|
| Mode | central / orchestrator / security |
| Repo | owner/name |
| SHA | git commit |
| Run URL | https://github.com/.../actions/runs/... |
| Workflow | workflow name |
| Run ID | numeric |

**Config Provenance**
| Setting | Value |
|---------|-------|
| Config Source | defaults / config/repos / .ci-hub.yml |
| Profile | profile name (if applied) |
| Schema Version | schema version used |

**Workflow Health**
| Setting | Value |
|---------|-------|
| Orchestrator Status | PASS/FAIL |
| Security Status | PASS/FAIL |
| Retries | number |
| Timeout | minutes |

**Environment / Build Info**
| Setting | Value |
|---------|-------|
| Runner OS | ubuntu-latest |
| Java Version | 17 |
| Python Version | 3.11 |
| Build Tool | Maven/Gradle |

**Artifacts Produced**
| Artifact | Path | Status |
|----------|------|--------|

**Compliance / Security**
| Tool | Key Detail |
|------|------------|

**Dispatch Topology**
| Metric | Value |
|--------|-------|
| Repos Targeted | number |
| Repos Succeeded | number |
| Repos Failed | number |
| Child Runs Linked | list |

---

## Parsing Dependencies (Do Not Break)

### validate_summary.py
- Requires `## Tools Enabled` section.
- Parses 5-column table: `| Category | Tool | Configured | Ran | Success |`.
- Mapping must include: Java + Python tool names listed in the contract.

### aggregate_reports.py
- Requires `schema_version: "2.0"` in `report.json`.
- Parses `results`, `tool_metrics`, `tools_ran` objects.
- Field names are hardcoded.

### cihub report aggregate
- Extracts metrics from `report.json` using exact field names.
- Maps `tools_ran` boolean flags to determine which tools executed.

---

## Caller Template Sync (Drift Prevention)

```bash
python -m cihub sync-templates --check
python -m cihub sync-templates
python -m cihub sync-templates --repo jguida941/some-repo
```

PR checklist:
- Run `sync-templates --check` before merging workflow changes.
- Update v1 tag if reusable workflow inputs changed.
- Verify caller templates reference correct `@v1`.

---

## Implementation Plan

### Phase 1: Align First Job Summaries
- Update `.github/workflows/java-ci.yml` build-test summary to 5-column Tools Enabled format.
- Update `.github/workflows/python-ci.yml` lint summary to 5-column Tools Enabled format.

### Phase 1.5: Update Summary Parser and Mappings
- Update `scripts/validate_summary.py` mappings for jqwik/hypothesis/codeql/docker.
- Ensure parsing expects all tools listed in the contract.

### Phase 2: Update Report Jobs
- Update `.github/workflows/java-ci.yml` report job to generate QA Metrics, Dependency Severity, Quality Gates.
- Update `.github/workflows/python-ci.yml` report job to generate QA Metrics, Security Summary, Quality Gates.
- Emit `tools_success` in `report.json` and align summary Success column to it.

### Phase 3: Consolidate Individual Job Summaries
- Remove or simplify tool-specific summaries (PMD, Semgrep, Trivy, PITest, Docker, CodeQL).

### Phase 4: Add Production Metadata Sections
- Emit Run Metadata, Config Provenance, Workflow Health, Environment/Build Info, Artifacts Produced, Compliance/Security, Dispatch Topology.

### Phase 5: Verify and Prevent Drift
- Run `validate_summary.py`, `aggregate_reports.py`, and `scripts/validate_report.sh`.
- Run `python -m cihub sync-templates --check` and fix drift.
- Update docs: `docs/guides/GETTING_STARTED.md`, `docs/reference/CONFIG.md`, `docs/guides/WORKFLOWS.md`.
- Document which job in orchestrator/security owns the consolidated summary and artifact sources.

---

## Production Readiness Evidence

### Acceptance Criteria
- Central, orchestrator, security, and reusable workflows emit the full mandatory section set.
- Tools Enabled table uses exact tool names and canonical booleans.
- `report.json` includes `schema_version: "2.0"`, `tools_ran`, `tool_metrics`, `tools_success`.
- Artifact presence matches `tools_ran`/`tools_success` contract.
- Dashboard generation renders metrics without missing values.

### Golden Samples
- Passing and failing summaries for Java and Python, stored under `docs/development/summaries/`.

### Verifier Outputs
- Capture success and failure outputs for `validate_summary.py` and `aggregate_reports.py`.

### Artifact Proof
- Verify at least one expected artifact exists per successful tool.
- Document artifact-to-metric mapping used by report job.

### Failure Mode Examples
- Provide at least one example row per tool where `Configured=true`, `Ran=true`, `Success=false`.

---

## Audit Findings (2024-12-24)

This section documents gaps identified by auditing the plan against the current codebase.

### Pre-Requisites (Must Complete Before Phase 1)

These items MUST be addressed before starting the implementation phases:

#### 1. Update `validate_summary.py` Tool Mappings

**Current state** (`scripts/validate_summary.py:18-40`):
```python
JAVA_SUMMARY_MAP = {
    "JaCoCo Coverage": "jacoco",
    "PITest": "pitest",
    "Checkstyle": "checkstyle",
    "PMD": "pmd",
    "SpotBugs": "spotbugs",
    "OWASP Dependency-Check": "owasp",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
}
# MISSING: jqwik, CodeQL, Docker, maven/gradle (build tool)

PYTHON_SUMMARY_MAP = {
    "pytest": "pytest",
    "mutmut": "mutmut",
    "Ruff": "ruff",
    "Black": "black",
    "isort": "isort",
    "mypy": "mypy",
    "Bandit": "bandit",
    "pip-audit": "pip_audit",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
}
# MISSING: hypothesis, CodeQL, Docker
```

**Action required**: Add missing mappings before Phase 1.

#### 2. Update Artifact Expectations

**Current state** (`scripts/validate_summary.py:42-65`):
```python
JAVA_ARTIFACTS = {
    "jacoco": ["**/target/site/jacoco/jacoco.xml"],
    "checkstyle": ["**/checkstyle-result.xml"],
    # ... existing entries
}
# MISSING: jqwik, codeql, docker

PYTHON_ARTIFACTS = {
    "pytest": ["**/coverage.xml", ...],
    # ... existing entries
}
# MISSING: hypothesis, codeql, docker
```

**Action required**: Add artifact patterns for missing tools.

#### 3. Update Schema `ci-report.v2.json`

**Current schema** (`schema/ci-report.v2.json`) is missing:

| Field                              | Status    | Required By               |
|------------------------------------|-----------|---------------------------|
| `tools_configured`                 | ❌ Missing | Summary to Report Mapping |
| `tools_success`                    | ❌ Missing | Summary to Report Mapping |
| `thresholds.max_critical_vulns`    | ❌ Missing | Quality Gates             |
| `thresholds.max_high_vulns`        | ❌ Missing | Quality Gates             |
| `thresholds.max_semgrep_findings`  | ❌ Missing | Quality Gates             |
| `thresholds.max_checkstyle_errors` | ❌ Missing | Quality Gates             |
| `thresholds.max_spotbugs_bugs`     | ❌ Missing | Quality Gates             |

**Note**: These thresholds ARE output by workflows (java-ci.yml:197-200) but not in schema.

**Action required**: Update schema before Phase 2.

---

### Gaps in Tool Coverage

#### Tools in Workflows but Missing from Plan's Tool List

| Tool | Workflow | In Plan? | Notes |
|------|----------|----------|-------|
| `maven`/`gradle` | java-ci.yml:580 | ❌ No | Build tool row in Tools Enabled table |
| `hypothesis` | python-ci.yml | ✅ Yes | Listed correctly |

**Action required**: Add build tool (maven/gradle) to Java tools list in plan.

#### Current Summary Format vs Plan

**Current java-ci.yml summary** (lines 576-595):
```markdown
## Tools Enabled
| Category | Tool | Configured | Ran | Success |
| Build | maven | true | true | ... |
| Testing | JaCoCo Coverage | ... |
```

**Issue**: Build tool row uses `maven`/`gradle` but no parser mapping exists.

---

### Orchestrator & Security Workflow Gaps

#### hub-orchestrator.yml (lines 1006-1121)

The orchestrator generates its own aggregate summary with different format:
- Uses `| Config | Status | Cov | Mut | ... |` columns (not the 5-column Tools Enabled format)
- Separate tables for Java and Python repos
- No per-tool breakdown, only aggregated metrics

**Clarification needed**: Does orchestrator:
1. Emit its own summary in the unified format? OR
2. Only aggregate child `report.json` artifacts (current behavior)?

**Recommendation**: Keep orchestrator as aggregator-only; child workflows own per-repo summaries.

#### hub-security.yml (lines 240-282)

Current summary format:
```markdown
# Security & Supply Chain: ${{ matrix.name }}
## Jobs
| Job | Status | Duration |
```

**Issue**: Completely different structure than reusable workflows.

**Recommendation**: Security workflow should emit:
- `## Tools Enabled` with security tools (CodeQL, SBOM, pip-audit/OWASP, Bandit, ZAP)
- `## Security Summary` with findings

---

### Schema vs Workflow Output Alignment

| Field               | In Schema? | In Workflow Output? | Notes                                    |
|---------------------|------------|---------------------|------------------------------------------|
| `results.build`     | ✅          | ✅ java-ci           | Java uses `build`                        |
| `results.test`      | ✅          | ✅ python-ci         | Python uses `test`                       |
| `tools_ran`         | ✅          | ✅                   | Both workflows                           |
| `tools_configured`  | ❌          | ❌                   | Plan requires, neither has               |
| `tools_success`     | ❌          | ❌                   | Plan requires, neither has               |
| `thresholds` (full) | Partial    | ✅                   | Workflow outputs more than schema allows |

---

### Potential Breaking Changes

| Change                                              | Impact                          | Mitigation                       |
|-----------------------------------------------------|---------------------------------|----------------------------------|
| New required sections in summary                    | Downstream parsing may break    | Phase rollout, version flag      |
| Adding `tools_configured`/`tools_success` to schema | Existing reports won't validate | Schema v2.1? Or optional fields? |
| Renaming tool display names                         | `validate_summary.py` will fail | Update mappings first            |
| Changing orchestrator summary format                | Dashboard may break             | Keep aggregator format separate  |

---

### Scripts That Parse Artifacts (Audit Required)

These scripts parse report.json and/or artifacts - verify compatibility:

| Script                                 | Parses                | Fields Used                            | Status                   |
|----------------------------------------|-----------------------|----------------------------------------|--------------------------|
| `scripts/validate_summary.py`          | summary + report.json | `tools_ran`, mappings                  | ⚠️ Needs updates         |
| `scripts/aggregate_reports.py`         | report.json           | `results`, `tool_metrics`, `tools_ran` | ✅ OK                     |
| `cihub report aggregate`              | report.json           | Same as above                          | ✅ OK                     |
| `hub-orchestrator.yml` (CLI command)  | report.json           | All fields                             | ✅ OK                     |

---

### Implementation Checklist (Updated)

#### Phase 0: Pre-Requisites (NEW)
- [ ] Update `validate_summary.py` JAVA_SUMMARY_MAP: add jqwik, CodeQL, Docker, maven/gradle
- [ ] Update `validate_summary.py` PYTHON_SUMMARY_MAP: add hypothesis, CodeQL, Docker
- [ ] Update `validate_summary.py` JAVA_ARTIFACTS: add jqwik, codeql, docker patterns
- [ ] Update `validate_summary.py` PYTHON_ARTIFACTS: add hypothesis, codeql, docker patterns
- [ ] Decide: schema v2.0 additive changes vs v2.1 bump
- [ ] Add `tools_configured` to schema (optional field)
- [ ] Add `tools_success` to schema (optional field)
- [ ] Add missing threshold fields to schema
- [ ] Run existing tests: `pytest tests/test_aggregate_reports.py tests/test_contract_consistency.py`

#### Phase 1: (As written, after Phase 0)

#### Phase 1.5: (Merged into Phase 0)

---

### Open Questions

1. **Build tool row**: Should `maven`/`gradle` be in Tools Enabled, or is build implicit?
2. **Orchestrator summary**: Keep separate aggregate format or unify?
3. **Schema versioning**: Bump to v2.1 or keep v2.0 with optional new fields?
4. **Security workflow**: Should it emit per-repo summaries or just aggregate?

---

### Risk Assessment

| Risk                              | Likelihood | Impact | Mitigation                    |
|-----------------------------------|------------|--------|-------------------------------|
| Breaking `validate_summary.py`    | High       | Medium | Complete Phase 0 first        |
| Breaking orchestrator aggregation | Medium     | High   | Test with fixture repos       |
| Schema validation failures        | High       | Low    | Make new fields optional      |
| Dashboard rendering issues        | Medium     | Medium | Golden samples before rollout |

---

## Deep Dive: Script Parsing Analysis

This section documents exactly what each script parses and what would break.

### validate_summary.py (scripts/validate_summary.py)

**Purpose**: Validates that workflow summaries and artifacts match report.json tool flags.

**What it parses from report.json**:
```python
tools_ran = report.get("tools_ran", {})        # Line 258
tools_configured = report.get("tools_configured", {})  # Line 259 - CURRENTLY EMPTY
tools_success = report.get("tools_success", {})        # Line 260 - CURRENTLY EMPTY
```

**Current tool mappings** (lines 18-40):

| JAVA_SUMMARY_MAP | PYTHON_SUMMARY_MAP |
|------------------|-------------------|
| JaCoCo Coverage → jacoco | pytest → pytest |
| PITest → pitest | mutmut → mutmut |
| Checkstyle → checkstyle | Ruff → ruff |
| PMD → pmd | Black → black |
| SpotBugs → spotbugs | isort → isort |
| OWASP Dependency-Check → owasp | mypy → mypy |
| Semgrep → semgrep | Bandit → bandit |
| Trivy → trivy | pip-audit → pip_audit |
| | Semgrep → semgrep |
| | Trivy → trivy |

**Missing from JAVA_SUMMARY_MAP**:
- `jqwik` (in schema tools_ran, not in map)
- `codeql` (in schema tools_ran, not in map)
- `docker` (in schema tools_ran, not in map)
- `maven`/`gradle` (in workflow summary, not in map)

**Missing from PYTHON_SUMMARY_MAP**:
- `hypothesis` (in PYTHON_ARTIFACTS but NOT in summary map!)
- `codeql` (in schema tools_ran, not in map)
- `docker` (in schema tools_ran, not in map)

**Artifact expectations** (lines 42-65):

| JAVA_ARTIFACTS               | PYTHON_ARTIFACTS               |
|------------------------------|--------------------------------|
| jacoco, checkstyle, spotbugs | pytest, ruff, bandit           |
| pmd, owasp, pitest           | pip_audit, black, isort        |
| semgrep, trivy               | mypy, mutmut, **hypothesis** ✅ |
|                              | semgrep, trivy                 |

**Note**: `hypothesis` is in PYTHON_ARTIFACTS but NOT in PYTHON_SUMMARY_MAP - inconsistency!

**What would break if plan is implemented**:
1. Adding new tools to summary without updating mappings → validation fails
2. Renaming tool display names → "summary missing tool row" warnings
3. If `tools_configured` / `tools_success` are added to report.json, validation will work (code is ready at lines 269-270)

---

### aggregate_reports.py (scripts/aggregate_reports.py)

**Purpose**: Aggregates CI reports from all connected repositories into a single dashboard.

**What it parses from report.json** (lines 107-111):
```python
results = report.get("results", {})
tool_metrics = report.get("tool_metrics", {})
tools_ran = report.get("tools_ran", {})
```

**Does NOT parse**:
- `tools_configured` ❌
- `tools_success` ❌

**Fields extracted from results** (lines 118-137):
- `coverage`
- `mutation_score`
- `tests_passed`
- `tests_failed`

**Language detection** (lines 67-83):
- Checks `java_version` / `python_version`
- Falls back to `tools_ran.jacoco`, `tools_ran.pytest`, etc.

**What would break if plan is implemented**:
- Nothing - this script only uses `results`, `tool_metrics`, `tools_ran` which will remain
- If we want dashboard to show configured vs ran, need to add parsing

---

### cihub report aggregate

**Purpose**: Hub orchestrator aggregation - downloads artifacts, polls runs, validates correlation IDs.

**What it parses from report.json** (lines 217-251):
```python
# From results:
coverage, mutation_score, tests_passed, tests_failed

# From tool_metrics (Java):
checkstyle_issues, spotbugs_issues, pmd_violations
owasp_critical, owasp_high, owasp_medium

# From tool_metrics (Python):
ruff_errors, black_issues, isort_issues, mypy_errors
bandit_high, bandit_medium, pip_audit_vulns

# Cross-language:
semgrep_findings, trivy_critical, trivy_high

# Track which tools ran:
tools_ran = report_data.get("tools_ran", {})
```

**Does NOT parse**:
- `tools_configured` ❌
- `tools_success` ❌

**Metrics tracked in run_status** (lines 137-163):
All metrics above plus `tools_ran` dict.

**What would break if plan is implemented**:
- Nothing for current metrics
- If `tools_configured` / `tools_success` added to report, aggregation won't break but won't use them
- To track success status in aggregate, add `tools_success` parsing

---

### hub-orchestrator.yml Aggregation Step (CLI)

**Purpose**: Runs `python -m cihub report aggregate` and writes the GitHub step summary.

**Summary format generated** (different from child workflows):

**Java table columns**:
```
| Config | Status | Cov | Mut | CS | SB | PMD | OWASP | Semgrep | Trivy |
```

**Python table columns**:
```
| Config | Status | Cov | Mut | Tests | Ruff | Black | isort | mypy | Bandit | pip-audit | Semgrep | Trivy |
```

**Note**: This is a DIFFERENT format than the unified 5-column Tools Enabled table in the plan. Orchestrator shows aggregate metrics per-repo, not per-tool breakdown.

**What would break if plan is implemented**:
- If we try to unify orchestrator summary format with child workflow format, the CLI aggregation template needs rewrite
- Recommendation: Keep orchestrator as separate aggregate view

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW EXECUTION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  java-ci.yml / python-ci.yml                                        │
│       │                                                             │
│       ├── Emits → GITHUB_STEP_SUMMARY (markdown)                    │
│       │            └── ## Tools Enabled table                       │
│       │            └── ## Thresholds (effective)                    │
│       │            └── ### Results                                  │
│       │                                                             │
│       └── Emits → report.json (artifact)                            │
│                    └── schema_version: "2.0"                        │
│                    └── results: { coverage, mutation_score, ... }   │
│                    └── tool_metrics: { ... }                        │
│                    └── tools_ran: { jacoco: true, ... }             │
│                    └── tools_configured: ❌ MISSING                  │
│                    └── tools_success: ❌ MISSING                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         VALIDATION LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  validate_summary.py                                                │
│       │                                                             │
│       ├── Reads: summary markdown + report.json                     │
│       ├── Checks: tools_ran matches summary table                   │
│       ├── Checks: tools_configured (if present) matches             │
│       ├── Checks: artifacts exist for successful tools              │
│       └── Returns: warnings list                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGGREGATION LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  aggregate_reports.py                                               │
│       └── Reads: report.json files                                  │
│       └── Generates: dashboard.html or summary.json                 │
│                                                                     │
│  cihub report aggregate (orchestrator)                              │
│       └── Reads: dispatch metadata + report.json from child runs    │
│       └── Generates: hub-report.json + GITHUB_STEP_SUMMARY          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Complete Tool Inventory

### Java Tools (All Sources)

| Tool         | In Schema tools_ran | In Workflow | In JAVA_SUMMARY_MAP | In JAVA_ARTIFACTS | In defaults.yaml |
|--------------|---------------------|-------------|---------------------|-------------------|------------------|
| jacoco       | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| checkstyle   | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| spotbugs     | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| pmd          | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| owasp        | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| pitest       | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| jqwik        | ✅                   | ✅           | ❌                   | ❌                 | ✅                |
| semgrep      | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| trivy        | ✅                   | ✅           | ✅                   | ✅                 | ✅                |
| codeql       | ✅                   | ✅           | ❌                   | ❌                 | ✅                |
| docker       | ✅                   | ✅           | ❌                   | ❌                 | ✅                |
| maven/gradle | ❌                   | ✅ (summary) | ❌                   | ❌                 | ✅ (build_tool)   |

### Python Tools (All Sources)

| Tool       | In Schema tools_ran | In Workflow | In PYTHON_SUMMARY_MAP | In PYTHON_ARTIFACTS | In defaults.yaml |
|------------|---------------------|-------------|-----------------------|---------------------|------------------|
| pytest     | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| ruff       | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| bandit     | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| pip_audit  | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| mypy       | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| black      | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| isort      | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| mutmut     | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| hypothesis | ✅                   | ✅           | ❌                     | ✅                   | ✅                |
| semgrep    | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| trivy      | ✅                   | ✅           | ✅                     | ✅                   | ✅                |
| codeql     | ✅                   | ✅           | ❌                     | ❌                   | ✅                |
| docker     | ✅                   | ✅           | ❌                     | ❌                   | ✅                |

---

## Schema v2.0 Gap Analysis

**Current schema** (`schema/ci-report.v2.json`):

```json
{
  "tools_ran": {
    "pytest": boolean, "ruff": boolean, "bandit": boolean,
    "pip_audit": boolean, "mypy": boolean, "hypothesis": boolean,
    "black": boolean, "isort": boolean, "mutmut": boolean,
    "jacoco": boolean, "checkstyle": boolean, "spotbugs": boolean,
    "pmd": boolean, "owasp": boolean, "pitest": boolean,
    "jqwik": boolean, "semgrep": boolean, "trivy": boolean,
    "docker": boolean, "codeql": boolean
  },
  "thresholds": {
    "coverage_min": number,
    "mutation_score_min": number,
    "owasp_cvss_fail": number,
    "max_pmd_violations": number
  }
}
```

**Required additions for plan**:
```json
{
  "tools_configured": { /* same structure as tools_ran */ },
  "tools_success": { /* same structure as tools_ran */ },
  "thresholds": {
    // Existing:
    "coverage_min": number,
    "mutation_score_min": number,
    "owasp_cvss_fail": number,
    "max_pmd_violations": number,
    // Missing:
    "max_critical_vulns": number,
    "max_high_vulns": number,
    "max_semgrep_findings": number,
    "max_checkstyle_errors": number,
    "max_spotbugs_bugs": number,
    "max_ruff_errors": number,
    "max_black_issues": number,
    "max_isort_issues": number
  }
}
```

---

## Recommended Phase 0 Checklist (Revised)

Based on deep analysis, here's the complete pre-requisite checklist:

### validate_summary.py Updates

- [ ] Add to JAVA_SUMMARY_MAP:
  - `"jqwik": "jqwik"`
  - `"CodeQL": "codeql"`
  - `"Docker": "docker"`

- [ ] Add to PYTHON_SUMMARY_MAP:
  - `"Hypothesis": "hypothesis"` (already in artifacts, missing in map!)
  - `"CodeQL": "codeql"`
  - `"Docker": "docker"`

- [ ] Add to JAVA_ARTIFACTS:
  - `"jqwik": ["**/jqwik-report.json"]` (or appropriate pattern)
  - `"codeql": []` (CodeQL uploads to Security tab, no local artifact)
  - `"docker": []` (Docker produces images, not file artifacts)

- [ ] Add to PYTHON_ARTIFACTS:
  - `"codeql": []`
  - `"docker": []`

### Schema Updates

- [ ] Add `tools_configured` object (optional, same keys as tools_ran)
- [ ] Add `tools_success` object (optional, same keys as tools_ran)
- [ ] Add missing thresholds:
  - `max_critical_vulns`
  - `max_high_vulns`
  - `max_semgrep_findings`
  - `max_checkstyle_errors`
  - `max_spotbugs_bugs`
  - `max_ruff_errors`
  - `max_black_issues`
  - `max_isort_issues`

### Workflow Updates (java-ci.yml, python-ci.yml)

- [ ] Emit `tools_configured` in report.json (map of input booleans)
- [ ] Emit `tools_success` in report.json (map of step outcomes)
- [ ] Ensure Summary `## Tools Enabled` table Success column matches `tools_success`

### Test Updates

- [ ] Update test fixtures to include new fields
- [ ] Add tests for new tool mappings
- [ ] Add tests for tools_configured/tools_success validation

---

## Decision Required: Build Tool in Summary

**Current state** (java-ci.yml line ~580):
```markdown
| Build | maven | true | true | ${{ steps.build.outcome == 'success' }} |
```

**Options**:

1. **Keep build tool row**: Add `maven`/`gradle` to JAVA_SUMMARY_MAP
   - Pro: Shows build status in tool table
   - Con: Build isn't really a "quality tool", it's infrastructure

2. **Remove build tool row from Tools Enabled**: Report build status separately
   - Pro: Cleaner separation of concerns
   - Con: Requires summary restructure

3. **Add to report.json as separate field**: `build_tool: "maven"` + `build_success: true`
   - Pro: Explicit tracking without conflating with quality tools
   - Con: Schema change needed

**Recommendation**: Option 3 - keep build separate from quality tools.

---

## Unified Solution Design

This section provides concrete solutions for all identified gaps.

### Solution 1: Orchestrator Unified Format

**Problem**: Orchestrator uses completely different columns than child workflows.

**Solution**: Orchestrator emits the SAME `## Tools Enabled` format, but aggregated across all repos.

**Current orchestrator format**:

```markdown
## Java Repos
| Config | Status | Cov | Mut | CS | SB | PMD | OWASP | Semgrep | Trivy |
```

**Proposed unified format**:

## Aggregate Tools Summary

| Category | Tool            | Repos Configured | Repos Ran | Repos Passed | Repos Failed |
|----------|-----------------|------------------|-----------|--------------|--------------|
| Testing  | JaCoCo Coverage | 5                | 5         | 4            | 1            |
| Testing  | PITest          | 3                | 2         | 2            | 0            |
| Linting  | Checkstyle      | 5                | 5         | 3            | 2            |
| Security | OWASP           | 4                | 4         | 4            | 0            |
| Security | Semgrep         | 2                | 0         | -            | -            |


## Per-Repo Summary (existing format, keep)
| Repo | Status | Coverage | Mutation | Critical | High |

**Implementation**:
- Orchestrator aggregates `tools_configured`, `tools_ran`, `tools_success` from all child `report.json` files
- For each tool, count how many repos had it configured/ran/passed
- Emit both aggregate AND per-repo views

### Solution 2: Emit tools_configured and tools_success in Workflows

**Problem**: Workflows emit `tools_ran` but not `tools_configured` or `tools_success`.

**Solution**: Add these to the report job in both workflows.

**java-ci.yml report job addition**:
```yaml
# In the Generate Report step, add:
"tools_configured": {
  "jacoco": ${{ inputs.run_jacoco }},
  "checkstyle": ${{ inputs.run_checkstyle }},
  "spotbugs": ${{ inputs.run_spotbugs }},
  "pmd": ${{ inputs.run_pmd }},
  "owasp": ${{ inputs.run_owasp }},
  "pitest": ${{ inputs.run_pitest }},
  "jqwik": ${{ inputs.run_jqwik }},
  "semgrep": ${{ inputs.run_semgrep }},
  "trivy": ${{ inputs.run_trivy }},
  "codeql": ${{ inputs.run_codeql }},
  "docker": ${{ inputs.run_docker }}
},
"tools_success": {
  "jacoco": ${{ needs.build-test.outputs.jacoco_success == 'true' }},
  "checkstyle": ${{ needs.build-test.outputs.checkstyle_success == 'true' }},
  ...
}
```

**python-ci.yml report job addition**:
```yaml
"tools_configured": {
  "pytest": ${{ inputs.run_pytest }},
  "ruff": ${{ inputs.run_ruff }},
  "bandit": ${{ inputs.run_bandit }},
  "pip_audit": ${{ inputs.run_pip_audit }},
  "mypy": ${{ inputs.run_mypy }},
  "black": ${{ inputs.run_black }},
  "isort": ${{ inputs.run_isort }},
  "mutmut": ${{ inputs.run_mutmut }},
  "hypothesis": ${{ inputs.run_hypothesis }},
  "semgrep": ${{ inputs.run_semgrep }},
  "trivy": ${{ inputs.run_trivy }},
  "codeql": ${{ inputs.run_codeql }},
  "docker": ${{ inputs.run_docker }}
},
"tools_success": {
  "pytest": ${{ needs.test.outputs.status == 'success' }},
  "ruff": ${{ needs.lint.outputs.ruff_success == 'true' }},
  ...
}
```

### Solution 3: Update validate_summary.py Mappings

**Add to JAVA_SUMMARY_MAP** (line ~27):
```python
JAVA_SUMMARY_MAP = {
    "JaCoCo Coverage": "jacoco",
    "PITest": "pitest",
    "Checkstyle": "checkstyle",
    "PMD": "pmd",
    "SpotBugs": "spotbugs",
    "OWASP Dependency-Check": "owasp",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    # ADD THESE:
    "jqwik": "jqwik",
    "CodeQL": "codeql",
    "Docker": "docker",
}
```

**Add to PYTHON_SUMMARY_MAP** (line ~40):
```python
PYTHON_SUMMARY_MAP = {
    "pytest": "pytest",
    "mutmut": "mutmut",
    "Ruff": "ruff",
    "Black": "black",
    "isort": "isort",
    "mypy": "mypy",
    "Bandit": "bandit",
    "pip-audit": "pip_audit",
    "Semgrep": "semgrep",
    "Trivy": "trivy",
    # ADD THESE:
    "Hypothesis": "hypothesis",
    "CodeQL": "codeql",
    "Docker": "docker",
}
```

**Add to JAVA_ARTIFACTS** (line ~51):
```python
JAVA_ARTIFACTS = {
    # existing...
    "jqwik": [],  # jqwik doesn't produce file artifacts, runs inline
    "codeql": [],  # CodeQL uploads to Security tab
    "docker": [],  # Docker produces images, not files
}
```

**Add to PYTHON_ARTIFACTS** (line ~65):
```python
PYTHON_ARTIFACTS = {
    # existing...
    # hypothesis already present at line 62!
    "codeql": [],
    "docker": [],
}
```

### Solution 4: Update aggregate_reports.py

**Add parsing for new fields** (after line 111):
```python
tools_configured = report.get("tools_configured", {})
tools_success = report.get("tools_success", {})
```

**Add to repo_detail** (after line 159):
```python
if tools_configured:
    repo_detail["tools_configured"] = tools_configured
if tools_success:
    repo_detail["tools_success"] = tools_success
```

**Add aggregate stats to summary**:
```python
# Count tools across all repos
tool_stats = {}
for report in reports:
    for tool, configured in report.get("tools_configured", {}).items():
        if tool not in tool_stats:
            tool_stats[tool] = {"configured": 0, "ran": 0, "passed": 0, "failed": 0}
        if configured:
            tool_stats[tool]["configured"] += 1
        if report.get("tools_ran", {}).get(tool):
            tool_stats[tool]["ran"] += 1
        if report.get("tools_success", {}).get(tool):
            tool_stats[tool]["passed"] += 1
        elif report.get("tools_ran", {}).get(tool):
            tool_stats[tool]["failed"] += 1

summary["tool_stats"] = tool_stats
```

### Solution 5: Update cihub report aggregate

**Add to extract_metrics_from_report** (aggregation module):
```python
run_status["tools_configured"] = report_data.get("tools_configured", {})
run_status["tools_success"] = report_data.get("tools_success", {})
```

**Add to create_run_status** (aggregation module):
```python
"tools_configured": {},
"tools_success": {},
```

**Update generate_summary_markdown to emit unified format**:
```python
def generate_tool_aggregate_table(results: list[dict]) -> str:
    """Generate unified Tools Enabled aggregate table."""
    tool_stats = {}

    for r in results:
        for tool, configured in r.get("tools_configured", {}).items():
            if tool not in tool_stats:
                tool_stats[tool] = {"configured": 0, "ran": 0, "passed": 0}
            if configured:
                tool_stats[tool]["configured"] += 1
            if r.get("tools_ran", {}).get(tool):
                tool_stats[tool]["ran"] += 1
            if r.get("tools_success", {}).get(tool):
                tool_stats[tool]["passed"] += 1

    lines = [
        "## Tools Summary (Aggregate)",
        "",
        "| Category | Tool | Configured | Ran | Passed |",
        "|----------|------|------------|-----|--------|",
    ]

    # Categorize tools
    categories = {
        "Testing": ["jacoco", "pytest", "pitest", "mutmut", "hypothesis", "jqwik"],
        "Linting": ["checkstyle", "spotbugs", "pmd", "ruff", "black", "isort", "mypy"],
        "Security": ["owasp", "bandit", "pip_audit", "semgrep", "trivy", "codeql"],
        "Container": ["docker"],
    }

    for category, tools in categories.items():
        for tool in tools:
            if tool in tool_stats:
                stats = tool_stats[tool]
                lines.append(
                    f"| {category} | {tool} | {stats['configured']} | "
                    f"{stats['ran']} | {stats['passed']} |"
                )

    return "\n".join(lines)
```

### Solution 6: Update Schema

**Add to schema/ci-report.v2.json**:
```json
{
  "tools_configured": {
    "type": "object",
    "description": "Which tools were configured to run (from inputs)",
    "additionalProperties": false,
    "properties": {
      "pytest": { "type": "boolean" },
      "ruff": { "type": "boolean" },
      // ... same keys as tools_ran
    }
  },
  "tools_success": {
    "type": "object",
    "description": "Which tools completed successfully",
    "additionalProperties": false,
    "properties": {
      "pytest": { "type": "boolean" },
      "ruff": { "type": "boolean" },
      // ... same keys as tools_ran
    }
  },
  "thresholds": {
    "properties": {
      // Existing:
      "coverage_min": { "type": ["number", "null"] },
      "mutation_score_min": { "type": ["number", "null"] },
      "owasp_cvss_fail": { "type": ["number", "null"] },
      "max_pmd_violations": { "type": ["integer", "null"] },
      // ADD:
      "max_critical_vulns": { "type": ["integer", "null"] },
      "max_high_vulns": { "type": ["integer", "null"] },
      "max_semgrep_findings": { "type": ["integer", "null"] },
      "max_checkstyle_errors": { "type": ["integer", "null"] },
      "max_spotbugs_bugs": { "type": ["integer", "null"] },
      "max_ruff_errors": { "type": ["integer", "null"] },
      "max_black_issues": { "type": ["integer", "null"] },
      "max_isort_issues": { "type": ["integer", "null"] }
    }
  }
}
```

---

## Revised Implementation Phases

### Phase 0: Foundation (Pre-requisites)
**Goal**: Prepare infrastructure without breaking anything.

1. **Update validate_summary.py**
   - Add jqwik, CodeQL, Docker to JAVA_SUMMARY_MAP
   - Add Hypothesis, CodeQL, Docker to PYTHON_SUMMARY_MAP
   - Add empty artifact patterns for codeql, docker
   - Run tests: `pytest tests/test_aggregate_reports.py -v`

2. **Update schema/ci-report.v2.json**
   - Add `tools_configured` (optional object)
   - Add `tools_success` (optional object)
   - Add missing threshold fields
   - Run tests: `pytest tests/test_contract_consistency.py -v`

3. **Update test fixtures**
   - Add new fields to test report.json files
   - Verify all tests pass

### Phase 1: Emit New Fields
**Goal**: Workflows start emitting `tools_configured` and `tools_success`.

1. **Update java-ci.yml**
   - Add `tools_configured` to report.json output
   - Add `tools_success` to report.json output
   - Capture step outcomes for each tool
   - Update Tools Enabled table Success column

2. **Update python-ci.yml**
   - Same as Java

3. **Verify**
   - Run smoke test repos
   - Validate report.json has new fields
   - Run `validate_summary.py --strict`

### Phase 2: Update Aggregation Scripts
**Goal**: Scripts use new fields for richer reporting.

1. **Update aggregate_reports.py**
   - Parse `tools_configured` and `tools_success`
   - Add tool_stats to summary output
   - Update HTML dashboard with tool aggregate view

2. **Update cihub report aggregate**
   - Parse new fields
   - Add `generate_tool_aggregate_table()` function
   - Include in GITHUB_STEP_SUMMARY

### Phase 3: Unify Orchestrator Format
**Goal**: Orchestrator emits same format as child workflows.

1. **Update hub-orchestrator.yml (CLI aggregate output)**
   - Add Tools Summary (Aggregate) table
   - Keep per-repo metrics table (but after Tools Summary)
   - Use consistent section headers

2. **Update hub-security.yml**
   - Add Tools Enabled table with security tools
   - Use same format as reusable workflows

### Phase 4: Polish & Documentation
**Goal**: Complete the unification.

1. **Add golden samples**
   - Save example summaries to `docs/development/summaries/`
   - Include passing and failing examples
   - Include Java and Python examples

2. **Update documentation**
   - `docs/guides/GETTING_STARTED.md`
   - `docs/reference/CONFIG.md`
   - `docs/guides/WORKFLOWS.md`

3. **Add drift detection**
   - CI check that validates summary format
   - Fail PR if format drifts from specification

---

## Summary Format Specification (Final)

All workflows (reusable, orchestrator, security) MUST emit these sections in order:

```markdown
# CI Report: {repo_name}

## Tools Enabled
| Category | Tool | Configured | Ran | Success |
|----------|------|------------|-----|---------|
| Testing | JaCoCo Coverage | true | true | true |
| Testing | PITest | true | false | - |
| Linting | Checkstyle | true | true | false |
| Security | OWASP | false | - | - |
...

## Thresholds (effective)
| Setting | Value |
|---------|-------|
| Min Coverage | 70% |
| Min Mutation Score | 70% |
...

## Results
| Metric | Value | Status |
|--------|-------|--------|
| Coverage | 85% | PASS |
| Mutation Score | 72% | PASS |
| Tests Passed | 150 | - |
| Tests Failed | 0 | PASS |
| Critical Vulns | 0 | PASS |
...

## Environment
| Setting | Value |
|---------|-------|
| Java Version | 21 |
| Build Tool | Maven |
| Runner | ubuntu-latest |
...
```

**For orchestrator aggregate view, add**:
```markdown
## Tools Summary (Aggregate)
| Category | Tool | Repos Configured | Repos Ran | Repos Passed |
|----------|------|------------------|-----------|--------------|
| Testing | JaCoCo Coverage | 5/5 | 5/5 | 4/5 |
...
```

**Dash conventions**:
- `-` = Not applicable (tool wasn't configured, so Ran/Success don't apply)
- `0` = Zero count (tool ran, found zero issues)
- Empty = Data not available (shouldn't happen in valid reports)
