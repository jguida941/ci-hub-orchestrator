# Reusable Workflow Migration Plan

> **This is the primary execution plan for CI/CD Hub.** Supersedes ROADMAP.md phases 4-8.

**Status:** Phase 1B In Progress
**Created:** 2025-12-15
**Last Updated:** 2025-12-18
**Goal:** Migrate from dispatch templates to GitHub reusable workflows + CLI tool for automatic repo onboarding

## Quick Status

| Part | Description | Status |
|------|-------------|--------|
| **Part 1** | Reusable Workflows | 🔄 Phase 1B active (blocking Part 4) |
| **Part 2** | CLI Tool (`cihub`) | ⚪ Not started |
| **Part 3** | Test Fixtures Expansion | ⚪ Not started |
| **Part 4** | Aggregation | ✅ Mostly done (needs Part 1 for correct reports) |
| **Part 5** | Dashboard | 🟡 Partial (HTML exists, needs GitHub Pages) |
| **Part 6** | Polish & Release | ⚪ Not started |

**Critical Path:** Part 1 → Part 4 unlocks → Part 5 completes → Release

---

## Problem Statement

The current dispatch pattern requires each connected repo to have a full `python-ci-dispatch.yml` or `java-ci-dispatch.yml` workflow file. When the hub updates its template, every repo becomes outdated and must be manually updated.

**Current Issues Discovered:**
- Connected repos have outdated dispatch workflows (only 4 fields in report.json vs 12+ expected)
- Mutation scores showing 0% because workflows aren't generating proper output
- No automatic sync mechanism - templates drift over time
- Manual updates don't scale as more repos connect
- No easy way for new repos to onboard

---

## Solution Overview

Two-part solution:

1. **Reusable Workflows** - Repos call hub's workflow instead of copying templates
2. **CLI Tool (`cihub`)** - Automatically detects repo structure and generates config + minimal workflow

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NEW ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ONBOARDING (one-time):                                                    │
│   ┌──────────┐    scans     ┌──────────┐    generates    ┌──────────────┐  │
│   │  cihub   │ ──────────►  │   repo   │ ──────────────► │ .ci-hub.yml  │  │
│   │   CLI    │              │ structure│                 │ hub-ci.yml   │  │
│   └──────────┘              └──────────┘                 └──────────────┘  │
│                                                                             │
│   RUNTIME (ongoing):                                                        │
│   ┌─────────────────┐     dispatch      ┌─────────────────────────────┐    │
│   │ Hub Orchestrator│ ───────────────►  │ Repo's hub-ci.yml (15 lines)│    │
│   └─────────────────┘                   └──────────────┬──────────────┘    │
│                                                        │ calls             │
│                                         ┌──────────────▼──────────────┐    │
│                                         │ Hub's python-ci.yml          │    │
│                                         │ (ALWAYS CURRENT)             │    │
│                                         └─────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Reusable Workflows

### Phase 1: Validate & Align Reusable Workflows

The hub already has reusable workflows with `workflow_call`:
- `.github/workflows/python-ci.yml`
- `.github/workflows/java-ci.yml`

**CRITICAL: Report Schema Mismatch**

Current reusable workflows emit lightweight `report.json`:
```json
{ "coverage": 87, "mutation_score": 0, "high_vulns": 0, "dependency_vulns": 0 }
```

But orchestrator aggregator expects the richer schema (12+ fields):
```json
{
  "schema_version": "2.0",  // ADD THIS for future compatibility
  "coverage": 87,
  "tests_passed": 10, "tests_failed": 0,
  "mutation_score": 72,
  "ruff_errors": 0, "black_issues": 0, "isort_issues": 0, "mypy_errors": 0,
  "bandit_high": 0, "bandit_medium": 2,
  "pip_audit_vulns": 0,
  "semgrep_findings": 0,
  "trivy_critical": 0, "trivy_high": 0,
  "tools_ran": { "pytest": true, "ruff": true, ... }
}
```

**NOTE: Add `schema_version` field** to guard aggregator against future changes. Aggregator can check version and handle old/new formats gracefully.

**Tasks:**
- [ ] Audit `python-ci.yml` - expand report.json to include ALL 12+ fields
- [ ] Audit `java-ci.yml` - same expansion (checkstyle, spotbugs, pmd, pitest, owasp)
- [ ] Ensure `tools_ran` object is included
- [ ] Match thresholds/defaults with dispatch templates (mutation gate off by default in python-ci.yml - fix this)
- [ ] Align semgrep/trivy/codeql defaults between reusable and dispatch
- [ ] Run actionlint on reusable workflows
- [ ] Test with fixtures to prove 12+ fields are populated
- [ ] Ensure both upload `ci-report` artifact with correct structure

**Verification:**
```yaml
# Test from any repo
jobs:
  test:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@main
    with:
      python_version: '3.12'
    secrets: inherit
```

### Branch-Based Testing Strategy for Phase 1

**IMPORTANT: Always test workflow changes on a branch before merging to main.**

Reusable workflows can be called from any git ref (branch, tag, commit SHA), enabling safe testing:

**Step 1: Create feature branch**
```bash
git checkout -b phase1-report-schema
git add .github/workflows/python-ci.yml .github/workflows/java-ci.yml
git commit -m "Phase 1: Expand CI report schema to 12+ fields"
git push -u origin phase1-report-schema
```

**Step 2: Update fixture repo to test the branch**
```yaml
# In ci-cd-hub-fixtures/.github/workflows/hub-ci.yml (temporary)
jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@phase1-report-schema  # Branch ref
    with:
      python_version: '3.12'
    secrets: inherit
```

**Step 3: Trigger and verify**
```bash
# Trigger workflow dispatch from hub
gh workflow run hub-orchestrator.yml

# Download and inspect artifact
gh run download <run-id> -n ci-report
cat report.json | jq .
```

**Step 4: Verify report.json has all expected fields**
```bash
# Check for schema_version
jq '.schema_version' report.json  # Should be "2.0"

# Check for test counts
jq '.results.tests_passed, .results.tests_failed' report.json

# Check for tool metrics
jq '.tool_metrics' report.json
```

**Step 5: After verification, merge and tag**
```bash
git checkout main
git merge phase1-report-schema
git tag -a v1.0.0 -m "v1.0.0: Full report schema"
git push origin main --tags
```

**Step 6: Update fixture repo to use tag**
```yaml
uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1  # Stable tag
```

**What could break:**
| Risk | Mitigation |
|------|------------|
| Report job `needs` optional jobs (semgrep, trivy) | Use `|| 0` fallbacks for all optional job outputs |
| JUnit XML parsing fails | Default to 0 if file missing or malformed |
| Ruff JSON output format varies | Wrap in try/catch, default to 0 |
| Workflow syntax errors | Run `actionlint` locally before push |

**Local validation before push:**
```bash
# Install actionlint
brew install actionlint

# Validate workflow syntax
actionlint .github/workflows/python-ci.yml
actionlint .github/workflows/java-ci.yml
```

---

### Phase 2: Create Caller Templates with Full Input Passthrough

Create "caller" workflow templates that repos will use.

**CRITICAL: Full Input Passthrough Required**

The orchestrator sends MANY inputs - caller must forward ALL of them:
- `python_version` / `java_version`
- `workdir`
- `coverage_min`, `mutation_score_min`
- `run_pytest`, `run_ruff`, `run_black`, `run_isort`, `run_bandit`, `run_pip_audit`, `run_mypy`, `run_mutmut`
- `run_semgrep`, `run_trivy`, `run_codeql`, `run_docker`
- `retention_days`
- Java-specific: `run_jacoco`, `run_pitest`, `run_checkstyle`, `run_spotbugs`, `run_pmd`, `run_owasp`
- Thresholds: `max_critical_vulns`, `max_high_vulns`

**File:** `templates/repo/hub-python-ci.yml`

```yaml
# Caller workflow - forwards ALL inputs to hub's reusable workflow
# Copy to: .github/workflows/hub-ci.yml
# Pin to @v1 for stability (not @main)
name: "Hub: Python CI"

on:
  workflow_dispatch:
    inputs:
      python_version: { type: string, default: '3.12' }
      workdir: { type: string, default: '.' }
      # Thresholds
      coverage_min: { type: number, default: 70 }
      mutation_score_min: { type: number, default: 70 }
      max_critical_vulns: { type: number, default: 0 }
      max_high_vulns: { type: number, default: 0 }
      # Tool toggles
      run_pytest: { type: boolean, default: true }
      run_ruff: { type: boolean, default: true }
      run_black: { type: boolean, default: true }
      run_isort: { type: boolean, default: true }
      run_bandit: { type: boolean, default: true }
      run_pip_audit: { type: boolean, default: true }
      run_mypy: { type: boolean, default: false }
      run_mutmut: { type: boolean, default: true }
      # NOTE: run_hypothesis removed - not in reusable workflow
      run_semgrep: { type: boolean, default: false }
      run_trivy: { type: boolean, default: false }
      run_codeql: { type: boolean, default: false }
      run_docker: { type: boolean, default: false }
      retention_days: { type: number, default: 30 }

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1  # PIN TO TAG
    with:
      python_version: ${{ inputs.python_version }}
      workdir: ${{ inputs.workdir }}
      coverage_min: ${{ inputs.coverage_min }}
      mutation_score_min: ${{ inputs.mutation_score_min }}
      max_critical_vulns: ${{ inputs.max_critical_vulns }}
      max_high_vulns: ${{ inputs.max_high_vulns }}
      run_pytest: ${{ inputs.run_pytest }}
      run_ruff: ${{ inputs.run_ruff }}
      run_black: ${{ inputs.run_black }}
      run_isort: ${{ inputs.run_isort }}
      run_bandit: ${{ inputs.run_bandit }}
      run_pip_audit: ${{ inputs.run_pip_audit }}
      run_mypy: ${{ inputs.run_mypy }}
      run_mutmut: ${{ inputs.run_mutmut }}
      run_semgrep: ${{ inputs.run_semgrep }}
      run_trivy: ${{ inputs.run_trivy }}
      run_codeql: ${{ inputs.run_codeql }}
      run_docker: ${{ inputs.run_docker }}
      retention_days: ${{ inputs.retention_days }}
    secrets: inherit
```

**File:** `templates/repo/hub-java-ci.yml` (FULL EXAMPLE - matches actual java-ci.yml inputs)

```yaml
# Caller workflow - forwards ALL inputs to hub's reusable workflow
# NOTE: Input names must match java-ci.yml exactly
name: "Hub: Java CI"

on:
  workflow_dispatch:
    inputs:
      java_version: { type: string, default: '21' }
      build_tool: { type: string, default: 'maven' }  # CRITICAL: maven or gradle
      # NOTE: java_distribution is hardcoded in java-ci.yml, not an input
      workdir: { type: string, default: '.' }
      # Thresholds (defaults match defaults.yaml)
      coverage_min: { type: number, default: 70 }
      mutation_score_min: { type: number, default: 70 }
      max_critical_vulns: { type: number, default: 0 }
      max_high_vulns: { type: number, default: 0 }  # defaults.yaml = 0
      owasp_cvss_fail: { type: number, default: 7 }
      # Tool toggles
      run_jacoco: { type: boolean, default: true }
      run_pitest: { type: boolean, default: true }
      run_checkstyle: { type: boolean, default: true }
      run_spotbugs: { type: boolean, default: true }
      run_pmd: { type: boolean, default: true }
      run_owasp: { type: boolean, default: true }
      run_semgrep: { type: boolean, default: false }
      run_trivy: { type: boolean, default: false }
      run_codeql: { type: boolean, default: false }
      run_docker: { type: boolean, default: false }
      # Docker settings (use EXACT names from java-ci.yml)
      docker_compose_file: { type: string, default: 'docker-compose.yml' }
      docker_health_endpoint: { type: string, default: '/actuator/health' }
      # NOTE: No health_timeout input in java-ci.yml
      retention_days: { type: number, default: 30 }

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@v1
    with:
      java_version: ${{ inputs.java_version }}
      build_tool: ${{ inputs.build_tool }}
      workdir: ${{ inputs.workdir }}
      coverage_min: ${{ inputs.coverage_min }}
      mutation_score_min: ${{ inputs.mutation_score_min }}
      max_critical_vulns: ${{ inputs.max_critical_vulns }}
      max_high_vulns: ${{ inputs.max_high_vulns }}
      owasp_cvss_fail: ${{ inputs.owasp_cvss_fail }}
      run_jacoco: ${{ inputs.run_jacoco }}
      run_pitest: ${{ inputs.run_pitest }}
      run_checkstyle: ${{ inputs.run_checkstyle }}
      run_spotbugs: ${{ inputs.run_spotbugs }}
      run_pmd: ${{ inputs.run_pmd }}
      run_owasp: ${{ inputs.run_owasp }}
      run_semgrep: ${{ inputs.run_semgrep }}
      run_trivy: ${{ inputs.run_trivy }}
      run_codeql: ${{ inputs.run_codeql }}
      run_docker: ${{ inputs.run_docker }}
      docker_compose_file: ${{ inputs.docker_compose_file }}
      docker_health_endpoint: ${{ inputs.docker_health_endpoint }}
      retention_days: ${{ inputs.retention_days }}
    secrets: inherit
```

**Tasks:**
- [ ] Create `templates/repo/hub-python-ci.yml` with ALL inputs
- [ ] Create `templates/repo/hub-java-ci.yml` with ALL inputs
- [ ] Pin to `@v1` tag (not `@main`) - requires Phase 3.5 tagging first
- [ ] Verify input names match between orchestrator → caller → reusable
- [ ] Document input passthrough requirements
- [ ] Add to README/docs

---

### Phase 3: Update Hub Orchestrator (Safe Rollout)

Update `hub-orchestrator.yml` to dispatch to `hub-ci.yml` instead of `python-ci-dispatch.yml`.

**CRITICAL: Safe Rollout Required**

Changing default `dispatch_workflow` to `hub-ci.yml` will **404** until each repo has the new caller workflow. Need phased approach:

**Option A: Per-Repo Override (Recommended)**
```yaml
# In config/repos/my-repo.yaml
repo:
  dispatch_workflow: hub-ci.yml  # Override when repo is ready
```

Keep default as old workflow, migrate repos one-by-one by adding override.

**Option B: Support Both Names (with GitHub API check)**

**NOTE:** If using Python `requests`, add to workflow dependencies. Alternatively use `gh api` or `curl`:
```bash
# Shell alternative (no extra deps)
gh api repos/{owner}/{repo}/contents/.github/workflows/hub-ci.yml --silent && echo "exists" || echo "missing"
```

```python
# Python version (requires requests in workflow)
import requests

def check_workflow_exists(owner, repo, workflow_name, token):
    """Check if workflow file exists via GitHub API"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/.github/workflows/{workflow_name}"
    resp = requests.get(url, headers={"Authorization": f"token {token}"})
    return resp.status_code == 200

dispatch_workflow = repo_info.get("dispatch_workflow")
if not dispatch_workflow:
    if check_workflow_exists(owner, repo, "hub-ci.yml", token):
        dispatch_workflow = "hub-ci.yml"
    else:
        dispatch_workflow = "python-ci-dispatch.yml"  # fallback to old
```

**Option C: Parallel Period**
1. Add `hub-ci.yml` to repos (doesn't break existing)
2. Update orchestrator to use new name
3. Remove old `python-ci-dispatch.yml` after confirming

**Tasks:**
- [x] ~~Add `dispatch_workflow` field to repo config schema~~ (ALREADY EXISTS - use existing field)
- [x] Update orchestrator to respect per-repo override
- [x] Keep `python-ci-dispatch.yml` as default during migration (smoke-test configs use old names)
- [ ] Document migration path for each repo
- [x] Test with one repo (fixtures) before others
- [x] After all repos migrated, change default to `hub-ci.yml` (fixtures use new hub-*-ci.yml)

---

### Phase 3.5: Versioning & Release Pipeline

**CRITICAL: No Tags Exist Yet**

Plan says "use @v1" but repo has no workflow tags or release pipeline.

**Tagging Strategy:**
```
v1.0.0  - Initial stable release
v1.1.0  - New features (backward compatible)
v2.0.0  - Breaking changes (new report schema, etc.)

v1      - Floating tag pointing to latest v1.x.x
```

**Release Workflow:** `.github/workflows/release.yml`
```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate reusable workflows
        run: |
          actionlint .github/workflows/python-ci.yml
          actionlint .github/workflows/java-ci.yml

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true

      - name: Update floating tag (v1 → v1.x.x)
        run: |
          VERSION=${GITHUB_REF#refs/tags/}
          MAJOR=$(echo $VERSION | cut -d. -f1)
          git tag -f $MAJOR
          git push -f origin $MAJOR
```

**Tasks:**
- [ ] Create `.github/workflows/release.yml`
- [ ] Cut initial tag `v1.0.0` after Phase 1 complete
- [ ] Create floating `v1` tag
- [ ] Document version policy in README
- [ ] Update caller templates to use `@v1` not `@main`

---

### Phase 4: Migrate Connected Repos

Update each connected repo to use the new minimal caller workflow.

**For each repo:**
1. Delete old `python-ci-dispatch.yml` or `java-ci-dispatch.yml`
2. Add new `hub-ci.yml` (the minimal caller)
3. Test dispatch from hub
4. Verify report.json has all expected fields

**Repos to migrate:**
- [ ] `ci-cd-hub-fixtures` (monorepo - python-passing, python-failing, java-passing, java-failing)
- [ ] `ci-cd-bst-demo-github-actions`
- [ ] `java-spring-tutorials`
- [ ] `smoke-test-python`
- [ ] `smoke-test-java`
- [ ] (add others as needed)

---

### Phase 5: Deprecate Old Templates

Once all repos are migrated:

**Tasks:**
- [ ] Remove `templates/python/python-ci-dispatch.yml`
- [ ] Remove `templates/java/java-ci-dispatch.yml`
- [ ] Update documentation
- [ ] Add migration guide for external users

---

## Part 2: CLI Tool (`cihub`)

A CLI that automates repo onboarding by detecting structure and generating config.

### Why a CLI?

| Manual Onboarding | With CLI |
|------------------|----------|
| Read docs, understand config schema | Run `cihub init` |
| Manually create `.ci-hub.yml` | CLI detects and generates |
| Copy workflow template, edit it | CLI generates correct workflow |
| Hope it works, debug on GitHub | `cihub preflight` tests locally |
| Push and pray | `cihub verify-github` confirms it works |

---

### Phase 6: CLI Core Commands

**Command Set:**

| Command | Description |
|---------|-------------|
| `cihub detect --repo <path>` | Scan repo, print detected settings (no writes) |
| `cihub detect --repo <path> --explain` | Show which files triggered which decisions |
| `cihub init --repo <path>` | Interactive setup, generates `.ci-hub.yml` + `hub-ci.yml` |
| `cihub init --repo <path> --non-interactive` | Use flags for all options |
| `cihub preflight --repo <path>` | Run local validation and tool checks |
| `cihub verify-github --repo <path>` | Push temp branch, run CI, verify it works |
| `cihub validate --repo <path>` | Validate existing config against schema |

**Example Usage:**
```bash
# Detect what the CLI would do
cihub detect --repo /path/to/my-python-app --explain

# Interactive init
cihub init --repo /path/to/my-python-app

# Non-interactive with flags
cihub init --repo /path/to/my-python-app \
  --non-interactive \
  --lang python \
  --coverage-min 80 \
  --mutation-min 70 \
  --enable semgrep,trivy

# Test locally before pushing
cihub preflight --repo /path/to/my-python-app

# Full end-to-end verification on GitHub
cihub verify-github --repo /path/to/my-python-app --branch cihub/verify
```

**Tasks:**
- [ ] Create CLI scaffold with typer
- [ ] Implement `detect` command
- [ ] Implement `init` command
- [ ] Implement `validate` command

---

### Phase 7: Repo Detection Engine

The CLI scans for common "signals" to infer settings.

**Detection Rules:**

| Signal File | Infers |
|-------------|--------|
| `pyproject.toml` | Python, check for pytest/ruff/black/isort/mypy config |
| `requirements*.txt` | Python |
| `setup.cfg`, `setup.py` | Python (legacy) |
| `pom.xml` | Java Maven, scan for plugins (jacoco, pitest, spotbugs) |
| `build.gradle`, `gradlew` | Java Gradle |
| `Dockerfile` | Docker build enabled |
| `docker-compose.yml` | Docker compose enabled |
| `src/`, `app/`, `tests/` | Source/test directories |
| `poetry.lock`, `uv.lock` | Package manager |

**What CLI Infers vs Asks:**

| Inferred Automatically | Asked as Questions |
|-----------------------|-------------------|
| Language (python/java) | "Which directory is app root?" (if ambiguous) |
| Build tool (maven/gradle/pip) | "Which test command?" (if multiple found) |
| Tools present (ruff, pytest, jacoco) | "Enforce gates or warn only?" |
| Source/test locations | "Which scanners to enable?" |
| Docker usage | "Paths to exclude?" |

**Safety Rules:**
- Never guess silently if multiple plausible roots exist
- `--dry-run` prints what would be written
- `--explain` shows which files triggered decisions
- Run schema validation before writing
- Allowlist of scanned file types (no .env, no secrets)

**Tasks:**
- [ ] Implement Python detection rules
- [ ] Implement Java Maven detection rules
- [ ] Implement Java Gradle detection rules
- [ ] Implement Docker detection
- [ ] Implement monorepo/subdir detection
- [ ] Add `--explain` output

---

### Phase 8: Config & Workflow Generation

**Outputs Generated:**

1. **`.ci-hub.yml`** - Repo-local config read by hub

**CRITICAL: Must include required `repo` block per schema**

```yaml
# Generated by cihub init
version: "1.0"  # Schema version for future compatibility

# REQUIRED: repo block with owner/name
repo:
  owner: jguida941
  name: my-python-app
  language: python
  default_branch: main
  dispatch_workflow: hub-ci.yml  # Use new reusable workflow pattern

language: python  # REQUIRED at top level

python:
  version: "3.12"
  tools:
    pytest: { enabled: true, min_coverage: 80 }
    ruff: { enabled: true }
    black: { enabled: true }
    bandit: { enabled: true }
    mutmut: { enabled: true, min_mutation_score: 70 }
    semgrep: { enabled: true }
    trivy: { enabled: false }

thresholds:
  coverage_min: 70       # match defaults.yaml
  mutation_score_min: 70
  max_critical_vulns: 0
  max_high_vulns: 0      # match defaults.yaml

reports:
  retention_days: 30
```

2. **`.github/workflows/hub-ci.yml`** - Full dispatch workflow (must match Phase 2)

**NOTE: This must pass ALL inputs, matching Phase 2 caller template exactly.**

```yaml
# Generated by cihub init - DO NOT EDIT
# Updates automatically when hub reusable workflow changes
name: "Hub: Python CI"

on:
  workflow_dispatch:
    inputs:
      python_version: { type: string, default: '3.12' }
      workdir: { type: string, default: '.' }
      coverage_min: { type: number, default: 70 }  # match defaults.yaml
      mutation_score_min: { type: number, default: 70 }
      max_critical_vulns: { type: number, default: 0 }
      max_high_vulns: { type: number, default: 0 }  # match defaults.yaml
      run_pytest: { type: boolean, default: true }
      run_ruff: { type: boolean, default: true }
      run_black: { type: boolean, default: true }
      run_isort: { type: boolean, default: true }
      run_bandit: { type: boolean, default: true }
      run_pip_audit: { type: boolean, default: true }
      run_mypy: { type: boolean, default: false }
      run_mutmut: { type: boolean, default: true }
      run_semgrep: { type: boolean, default: false }
      run_trivy: { type: boolean, default: false }
      run_codeql: { type: boolean, default: false }
      run_docker: { type: boolean, default: false }
      retention_days: { type: number, default: 30 }

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      python_version: ${{ inputs.python_version }}
      workdir: ${{ inputs.workdir }}
      coverage_min: ${{ inputs.coverage_min }}
      mutation_score_min: ${{ inputs.mutation_score_min }}
      max_critical_vulns: ${{ inputs.max_critical_vulns }}
      max_high_vulns: ${{ inputs.max_high_vulns }}
      run_pytest: ${{ inputs.run_pytest }}
      run_ruff: ${{ inputs.run_ruff }}
      run_black: ${{ inputs.run_black }}
      run_isort: ${{ inputs.run_isort }}
      run_bandit: ${{ inputs.run_bandit }}
      run_pip_audit: ${{ inputs.run_pip_audit }}
      run_mypy: ${{ inputs.run_mypy }}
      run_mutmut: ${{ inputs.run_mutmut }}
      run_semgrep: ${{ inputs.run_semgrep }}
      run_trivy: ${{ inputs.run_trivy }}
      run_codeql: ${{ inputs.run_codeql }}
      run_docker: ${{ inputs.run_docker }}
      retention_days: ${{ inputs.retention_days }}
    secrets: inherit
```

**Tasks:**
- [ ] Implement `.ci-hub.yml` generation
- [ ] Implement `hub-ci.yml` workflow generation (MUST match Phase 2 template)
- [ ] Template rendering (Jinja2 or string replace)
- [ ] Handle monorepo subdirs
- [ ] Verify generated workflow matches Phase 2 exactly

---

### Phase 9: Local Preflight Checks

Run the same commands locally that the workflow would run on GitHub.

**Preflight Levels:**

**Level 1: Static Validation (fast)**
- [ ] Validate YAML syntax
- [ ] Run `actionlint` on generated workflow
- [ ] Validate config against JSON schema
- [ ] Check required files exist (pyproject.toml, pom.xml, etc.)

**Level 2: Tool Execution (thorough)**
Run actual tools locally:

| Language | Commands Run |
|----------|-------------|
| Python | `pip install`, `ruff check`, `black --check`, `pytest --cov`, `bandit`, `pip-audit` |
| Java | `mvn verify`, jacoco report, pitest, dependency-check |

**Output:**
```
$ cihub preflight --repo /path/to/app

Preflight Check: my-python-app
==============================

[1/6] Validating config...           OK
[2/6] Validating workflow YAML...    OK
[3/6] Running ruff...                OK (0 issues)
[4/6] Running black --check...       OK
[5/6] Running pytest --cov...        OK (Coverage: 87%)
[6/6] Running bandit...              OK (0 high, 2 medium)

Summary:
  Coverage:     87% (threshold: 80%)  PASS
  Ruff issues:  0                     PASS
  Bandit high:  0 (threshold: 0)      PASS

Preflight PASSED - Ready for GitHub
```

**Tasks:**
- [ ] Implement static validation
- [ ] Implement Python tool runner
- [ ] Implement Java tool runner
- [ ] Generate preflight report

---

### Phase 10: GitHub Verification

True end-to-end test on GitHub (optional, the real proof).

**Flow:**
1. Create temporary branch (`cihub/verify-<timestamp>`)
2. Write generated workflows to `.github/workflows/`
3. Push branch
4. Trigger workflow via `gh workflow run`
5. Poll run status until complete
6. Fetch logs and artifacts via `gh run view` / `gh run download`
7. Report success/failure with exact failing step
8. Optionally clean up branch

**Command:**
```bash
cihub verify-github --repo /path/to/app --branch cihub/verify

# Output:
Pushing verification branch...
Triggering workflow...
Waiting for run to complete... (run #12345)
Run completed: SUCCESS

Artifacts downloaded to: ./cihub-verify-artifacts/
  - coverage.xml (87%)
  - report.json

Verification PASSED
```

**Tasks:**
- [ ] Implement branch creation/push
- [ ] Implement workflow trigger via `gh` CLI
- [ ] Implement run polling
- [ ] Implement artifact download
- [ ] Implement cleanup option

---

## CLI Technical Design

### CRITICAL: Reuse Existing Schema & Loader

The hub already has config infrastructure - CLI MUST reuse it:

**Existing Files:**
- `hub-release/schema/ci-hub-config.schema.json` - JSON Schema for repo configs
- `hub-release/scripts/load_config.py` - Config loader with validation

**CLI Must:**
1. Import and use `load_config.py` for validation
2. Generate configs that conform to `ci-hub-config.schema.json`
3. NOT create a divergent config format
4. Share validation logic between hub and CLI

```python
# In CLI
from hub_release.scripts.load_config import load_config, validate_config

def init_command(repo_path):
    config = detect_and_generate(repo_path)
    validate_config(config)  # Use existing validation
    write_config(config)
```

### Technology Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Already used in hub, familiar |
| CLI Framework | `typer` | Modern, type-safe, auto-generates help |
| YAML Handling | `ruamel.yaml` | Preserves comments and formatting |
| Templates | `jinja2` | Flexible, well-known |
| Validation | `jsonschema` | **Reuse existing hub schema** |
| Config Loader | `load_config.py` | **Reuse existing hub loader** |
| GitHub API | `gh` CLI | Already installed, handles auth |

### File Structure

```
hub-release/
├── schema/
│   └── ci-hub-config.schema.json    # EXISTING - reuse
├── scripts/
│   └── load_config.py               # EXISTING - reuse
├── cli/
│   ├── cihub/
│   │   ├── __init__.py
│   │   ├── __main__.py              # Entry point
│   │   ├── commands/
│   │   │   ├── detect.py
│   │   │   ├── init.py
│   │   │   ├── preflight.py
│   │   │   ├── validate.py          # Wraps existing schema validation
│   │   │   └── verify_github.py
│   │   ├── detection/
│   │   │   ├── python.py
│   │   │   ├── java.py
│   │   │   └── docker.py
│   │   ├── generators/
│   │   │   ├── config.py            # Generates schema-compliant configs
│   │   │   └── workflow.py
│   │   └── preflight/
│   │       ├── static.py
│   │       └── runners.py
│   ├── pyproject.toml
│   └── README.md
```

### Installation & Packaging

**NOTE: `hub-release/pyproject.toml` already exists**

Options for CLI packaging:

**Option A: Add CLI to existing pyproject.toml (recommended)**
```toml
# In hub-release/pyproject.toml
[project.scripts]
cihub = "cihub.__main__:main"

[project.optional-dependencies]
cli = ["typer", "ruamel.yaml", "jinja2"]
```

Then: `pip install -e ".[cli]"`

**Option B: Separate CLI package (more complex)**
```
hub-release/
├── pyproject.toml           # Existing
├── cli/
│   └── pyproject.toml       # New - needs path config for imports
```

Would need namespace package or path manipulation to import `scripts/load_config.py`.

**Recommended: Option A** - simpler, avoids import path issues.

```bash
# Install with CLI extras
pip install -e ".[cli]"

# Or published to PyPI
pip install ci-cd-hub[cli]

# Usage
cihub --help
```

**Tasks:**
- [ ] Audit existing `ci-hub-config.schema.json` for CLI needs
- [ ] Audit existing `load_config.py` for CLI reuse
- [ ] **Decision: Add CLI to existing pyproject.toml (Option A)**
- [ ] Add `[project.scripts]` entry for cihub
- [ ] Add CLI dependencies to `[project.optional-dependencies]`
- [ ] Set up CLI module structure under `hub-release/cihub/`
- [ ] Ensure CLI-generated configs pass existing validation

---

## Benefits After Full Implementation

| Aspect | Before | After |
|--------|--------|-------|
| Repo workflow size | 300+ lines | ~20 lines (generated) |
| Hub updates | Manual push to all repos | Automatic |
| Version drift | Common problem | Impossible |
| Onboarding time | Hours (read docs, configure) | Minutes (`cihub init`) |
| Testing before push | Push and pray | `cihub preflight` |
| Confidence it works | Low | `cihub verify-github` proves it |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing repos | Phase rollout, test with fixtures first |
| Reusable workflow bugs affect all repos | Use versioned tags (@v1, @v2) not @main |
| Cross-repo permissions | Ensure hub repo is public or properly shared |
| Input schema changes | Document breaking changes, use semantic versioning |
| CLI detection wrong | `--explain` flag, `--dry-run`, always ask on ambiguity |
| CLI complexity creep | Start minimal, iterate based on real usage |

---

## Version Strategy

Use semantic versioning for both workflows and CLI:

```yaml
# Repos can pin to stable versions
uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
```

```bash
# CLI version
cihub --version
# cihub 1.0.0
```

**Tasks:**
- [ ] Create initial release tag (v1.0.0)
- [ ] Document version policy
- [ ] Set up release workflow for CLI

---

## Success Criteria

1. All connected repos use minimal caller workflows
2. Hub orchestrator dispatches work with full data collection
3. Mutation scores, coverage, and all metrics flow back correctly
4. Single hub update propagates to all repos automatically
5. `cihub init` can onboard a new repo in under 5 minutes
6. `cihub preflight` catches 80%+ of issues before push
7. Documentation complete for new repo onboarding

---

## Implementation Priority

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| P0 | Phase 1: Audit reusable workflows | Low | High - fixes current broken state |
| P0 | Phase 2: Minimal caller templates | Low | High - enables migration |
| P1 | Phase 3: Update orchestrator | Low | High - activates new pattern |
| P1 | Phase 4: Migrate repos | Medium | High - proves it works |
| P2 | Phase 6: CLI core commands | Medium | High - enables easy onboarding |
| P2 | Phase 7: Detection engine | Medium | High - automates setup |
| P3 | Phase 8: Config generation | Low | Medium - polishes experience |
| P3 | Phase 9: Local preflight | Medium | Medium - improves confidence |
| P4 | Phase 10: GitHub verification | Medium | Low - nice to have |
| P4 | Phase 5: Deprecate old templates | Low | Low - cleanup |

---

## Existing Tools & Prior Art

Research on existing tools that solve parts of this problem:

### Workflow Generation
| Tool | What It Does | Limitation |
|------|-------------|------------|
| [projen](https://projen.io/) | Synthesizes GitHub workflow files from project config | Opinionated, requires buying into projen ecosystem |
| [Cookiecutter](https://cookiecutter.readthedocs.io/) | Template-based project generation | One-time generation, no ongoing sync |
| GitHub Starter Workflows | Template workflows for common languages | Manual copy, no detection |

### Workflow Validation
| Tool | What It Does | Limitation |
|------|-------------|------------|
| [actionlint](https://github.com/rhysd/actionlint) | Static linter for GitHub Actions YAML | Syntax only, doesn't test execution |
| [act](https://github.com/nektos/act) | Run GitHub Actions locally via Docker | Not 100% GitHub-compatible, secrets tricky |
| `gh workflow run` | Trigger workflows via CLI | No generation, just execution |

### What Doesn't Exist (Our Opportunity)
No single CLI that:
1. Scans any repo and detects project type
2. Generates the right workflow automatically
3. Tests it works end-to-end
4. Syncs with a central hub for updates

**This is exactly what `cihub` will do.**

### Tools to Integrate

Our CLI should leverage these existing tools:

```
cihub preflight
    │
    ├── actionlint          # Validate YAML syntax
    ├── act (optional)      # Local execution test
    └── tool runners        # ruff, pytest, mvn, etc.

cihub verify-github
    │
    └── gh CLI              # Push, trigger, poll, download artifacts
```

---

## Secrets Management

The CLI can help set up required secrets using the GitHub CLI.

### What `gh secret set` Supports

```bash
# Interactive prompt
gh secret set CODECOV_TOKEN

# From stdin (safer - no command history)
printf '%s' "$CODECOV_TOKEN" | gh secret set CODECOV_TOKEN --body -

# Bulk from dotenv file
gh secret set -f .env

# Environment secret
gh secret set AWS_ROLE_ARN --env prod

# Org secret restricted to repos
gh secret set MYSECRET --org myOrg --repos repo1,repo2
```

### CLI Secrets Command

```bash
cihub secrets --repo /path/to/app
```

**Flow:**
1. Scan `.github/workflows/*.yml` for `secrets.*` references
2. Check which secrets are already set via `gh secret list`
3. Prompt only for missing values (hidden input)
4. Ask: "Store in repo, environment, or org?"
5. Apply via `gh secret set`
6. Validate workflows will receive them

### Critical Gotchas

| Issue | Solution |
|-------|----------|
| Secrets not passed to reusable workflows | Must use `secrets: inherit` or explicit mapping |
| Leaking secrets via CLI args/logs | Use stdin or env vars, never command line args |
| Long-lived credentials | Prefer OIDC for cloud access when possible |

### Prefer OIDC Over Static Secrets

For cloud resources (AWS, GCP, Azure), use GitHub OIDC instead of storing static credentials:

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/my-role
      aws-region: us-east-1
```

**CLI could detect cloud usage and suggest OIDC setup.**

### Tasks
- [ ] Add `cihub secrets` command
- [ ] Implement workflow scanning for secret references
- [ ] Integrate with `gh secret set`
- [ ] Add OIDC detection and recommendations

---

## Additional Features from Research

### Golden Path / Platform Engineering

Frame `cihub` as a **Golden Path** - a self-service template for rapid project onboarding.

> "A Golden Path is a templated composition of well-integrated code and capabilities for rapid project development" - CNCF

**Benefits:**
- New developers stop losing first weeks to setup confusion
- One clear route from laptop to first commit
- Standardization simplifies onboarding
- Reduces errors and miscommunication

**Key Principle: Golden Path, Not Golden Cage**
- Provide opinionated defaults that work for 80% of cases
- Allow escape hatches for customization
- Don't force rigid workflows that block innovation

### Quality Monitor Integration

Integrate with [Quality Monitor Action](https://github.com/uhafner/quality-monitor) for:
- Aggregated test results in PR comments
- Code + mutation coverage display
- Static analysis findings inline
- Structured PR comments with metrics table

**Example PR Comment:**
```
## Quality Report

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Coverage | 87% | 80% | PASS |
| Mutation Score | 72% | 70% | PASS |
| Ruff Issues | 0 | 0 | PASS |
| Bandit High | 0 | 0 | PASS |

Merge: APPROVED
```

### Gradual Enforcement Strategy

Don't block everything immediately - phase in quality gates:

| Phase | Coverage | Mutation | Security | Behavior |
|-------|----------|----------|----------|----------|
| 1. Advisory | Any | Any | Any | Report only, never block |
| 2. New Code | 80%+ new | 60%+ new | 0 new high | Block on new issues |
| 3. Full | 80% total | 70% total | 0 high | Block on any violation |

**CLI Flag:**
```bash
cihub init --enforcement-level advisory  # Phase 1
cihub init --enforcement-level new-code  # Phase 2
cihub init --enforcement-level strict    # Phase 3
```

### Branch Protection Integration

CLI can configure GitHub branch protection rules:

```bash
cihub protect --repo /path/to/app

# Configures:
# - Require status checks to pass
# - Require PR reviews
# - Require conversation resolution
# - Block force pushes
```

Uses `gh api` to set branch protection:
```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Hub: Python CI"]}' \
  --field enforce_admins=true
```

### Self-Service Dashboard

Future enhancement - web dashboard for:
- View all connected repos and their status
- Trigger builds manually
- View aggregated metrics across repos
- Onboard new repos (calls CLI under the hood)

### GitOps Approach

Make Git the single source of truth:
- All config in `.ci-hub.yml` (repo) or `config/repos/*.yaml` (hub)
- All workflows generated from templates
- Changes auditable via git history
- Easy rollback via git revert

### Tasks from Research
- [ ] Add Golden Path framing to docs
- [ ] Integrate Quality Monitor action for PR comments
- [ ] Implement gradual enforcement levels
- [ ] Add `cihub protect` for branch protection
- [ ] Consider web dashboard for future roadmap

---

## Known Limitations We Cannot Solve Automatically

| Limitation | Our Approach |
|------------|--------------|
| Secrets/tokens/private deps | Document requirements, `cihub secrets` helps set them |
| Matrix logic across languages | Ask user to confirm when ambiguous |
| "Correct" thresholds | Provide sensible defaults, let user override via enforcement levels |
| 100% GitHub runner parity | `act` for local, `verify-github` for real test |
| Private registries | Detect and prompt for auth setup |
| Team buy-in | Start with advisory mode, prove value before enforcing |

---

## References

### Core GitHub Actions
- [GitHub: Reusable Workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusable-workflows)
- [GitHub Well-Architected: Scaling Actions Reusability](https://wellarchitected.github.com/library/collaboration/recommendations/scaling-actions-reusability/)
- [DRY in GitHub Actions with Reusable Workflows](https://rnd.ultimate.ai/blog/central-workflows)
- [GitHub OIDC for Cloud Auth](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

### CLI & Tooling
- [Typer CLI Framework](https://typer.tiangolo.com/)
- [actionlint - GitHub Actions Linter](https://github.com/rhysd/actionlint)
- [act - Run GitHub Actions Locally](https://github.com/nektos/act)
- [projen - Project Generator](https://projen.io/)
- [gh CLI - Secrets](https://cli.github.com/manual/gh_secret_set)
- [GH Actions Workflow Builder](https://michaelcurrin.github.io/workflow-builder/)

### Quality & Testing
- [Quality Monitor Action](https://github.com/uhafner/quality-monitor)
- [Graphite: Enforce Code Quality Gates](https://graphite.com/guides/enforce-code-quality-gates-github-actions)
- [CI/CD Best Practices](https://graphite.dev/guides/in-depth-guide-ci-cd-best-practices)

### Platform Engineering
- [Golden Paths - Red Hat](https://www.redhat.com/en/topics/platform-engineering/golden-paths)
- [Golden Paths - Google Cloud](https://cloud.google.com/blog/products/application-development/golden-paths-for-engineering-execution-consistency)
- [Platform Engineering Tools 2025](https://platformengineering.org/blog/top-10-platform-engineering-tools-to-use-in-2025)
- [Centralizing CI/CD for Microservices](https://evoila.com/blog/centralizing-ci-cd-pipeline-logic-for-microservices-architecture/)
- [Multi-Project CI/CD with GitHub Actions](https://multiprojectdevops.github.io/tutorials/1_github_actions/)

---

---

## Part 3: Test Fixtures Expansion

Expand `https://github.com/jguida941/ci-cd-hub-fixtures` to cover all project variations. Use branch-based testing to validate everything works before merging.

### Current Fixtures

```
ci-cd-hub-fixtures/
├── python-passing/      # Simple Python, all tests pass
├── python-failing/      # Simple Python, one failing test
├── java-passing/        # Simple Java Maven, all tests pass
└── java-failing/        # Simple Java Maven, one failing test
```

### Proposed Fixtures to Add

#### Python Variations
| Fixture | Description | Tests |
|---------|-------------|-------|
| `python-poetry/` | Poetry-based project with pyproject.toml | Dependency management, lock files |
| `python-uv/` | uv-based project | Modern Python tooling |
| `python-src-layout/` | src/ layout pattern | Different source structure |
| `python-no-tests/` | No test directory | Edge case handling |
| `python-hypothesis/` | Property-based tests | Hypothesis integration |
| `python-docker/` | Python + Dockerfile | Docker build detection |

#### Java Variations
| Fixture | Description | Tests |
|---------|-------------|-------|
| `java-gradle/` | Gradle-based project | Gradle detection vs Maven |
| `java-multi-module/` | Multi-module Maven project | Module discovery |
| `java-spring-boot/` | Spring Boot app | Common framework |
| `java-docker/` | Java + Dockerfile | Docker build detection |

#### Monorepo Variations
| Fixture | Description | Tests |
|---------|-------------|-------|
| `monorepo-python-apps/` | Multiple Python apps | Subdir detection, multiple configs |
| `monorepo-java-modules/` | Multiple Java modules | Multi-module handling |
| `monorepo-mixed/` | Python + Java in same repo | Language detection per subdir |
| `monorepo-nested/` | Deeply nested project structure | Path handling |

#### Edge Cases
| Fixture | Description | Tests |
|---------|-------------|-------|
| `empty-repo/` | No code, just README | Graceful failure |
| `no-config/` | Code but no pyproject/pom | Detection fallbacks |
| `legacy-python/` | setup.py only, no pyproject | Legacy support |
| `private-deps/` | Private dependencies | Auth handling |

### Proposed Fixture Structure

```
ci-cd-hub-fixtures/
├── .github/
│   └── workflows/
│       ├── hub-ci.yml              # Minimal caller (NEW)
│       └── test-all-fixtures.yml   # CI for the fixtures repo itself
│
├── python/
│   ├── simple-passing/
│   ├── simple-failing/
│   ├── poetry-project/
│   ├── uv-project/
│   ├── src-layout/
│   ├── with-docker/
│   └── hypothesis-tests/
│
├── java/
│   ├── maven-passing/
│   ├── maven-failing/
│   ├── gradle-project/
│   ├── multi-module/
│   ├── spring-boot/
│   └── with-docker/
│
├── monorepo/
│   ├── python-apps/
│   │   ├── app1/
│   │   └── app2/
│   ├── java-modules/
│   │   ├── module1/
│   │   └── module2/
│   ├── mixed-languages/
│   │   ├── python-api/
│   │   └── java-worker/
│   └── nested-deep/
│       └── level1/
│           └── level2/
│               └── app/
│
├── edge-cases/
│   ├── empty/
│   ├── no-config/
│   └── legacy-setup-py/
│
└── README.md
```

### Branch-Based Testing Strategy

```
main (stable)
  │
  ├── test/reusable-workflow-v1     # Test new reusable workflow
  │     └── Push → triggers hub-ci.yml → validates all fixtures
  │
  ├── test/cli-detect               # Test CLI detection on all variations
  │     └── Run cihub detect on each fixture, verify output
  │
  ├── test/cli-init                 # Test CLI init generates correct configs
  │     └── Run cihub init, commit results, trigger CI
  │
  └── test/full-integration         # Full end-to-end test
        └── Orchestrator dispatches to all fixtures, verify reports
```

**Workflow:**
1. Create feature branch (e.g., `test/reusable-workflow-v1`)
2. Add/modify fixtures as needed
3. Push branch → CI runs on all fixtures
4. Verify all reports have correct data (coverage, mutation, etc.)
5. If passing, merge to main
6. Tag release (v1.0.0, etc.)

### Hub Config for Fixtures

Each fixture should have a corresponding config in the hub:

```yaml
# hub-release/config/repos/fixtures-python-poetry.yaml
repo:
  owner: jguida941
  name: ci-cd-hub-fixtures
  language: python
  default_branch: main
  subdir: python/poetry-project
  run_group: fixtures

python:
  version: "3.12"
  tools:
    pytest: { enabled: true }
    ruff: { enabled: true }
    mutmut: { enabled: true }
```

### Fixture Validation Checklist

For each fixture, verify:
- [ ] `cihub detect` correctly identifies language/tools
- [ ] `cihub init` generates valid config
- [ ] `cihub preflight` passes locally
- [ ] Hub dispatch triggers workflow correctly
- [ ] `report.json` contains all expected fields
- [ ] Coverage/mutation scores are accurate (not 0% when they shouldn't be)
- [ ] Artifacts are uploaded and downloadable

### Tasks

- [ ] Restructure existing fixtures into new layout
- [ ] Add Python variations (poetry, uv, src-layout, docker)
- [ ] Add Java variations (gradle, multi-module, spring-boot)
- [ ] Add monorepo examples (mixed languages, nested)
- [ ] Add edge case fixtures
- [ ] Create hub configs for each fixture
- [ ] Set up branch-based testing workflow
- [ ] Document expected results for each fixture

---

## Implementation Checklist

### Key Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| `coverage_min` | `70` | Match `defaults.yaml` and workflow code |
| ADR-0013 handling | Keep in place + superseded banner | Preserve history, avoid link breakage |
| CLI priority | P0/P1 first, P2/P3 after v1 | Prevent scope creep |

---

### Hard Requirements (Blocks v1 Release)

These items MUST be completed before tagging v1.0.0:

| Requirement | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **schema_version in reports** | Both `python-ci.yml` and `java-ci.yml` must add `schema_version: "2.0"` to `report.json` | `jq '.schema_version' report.json` returns `"2.0"` |
| **Metadata block in reports** | Reports must include `workflow_version` and `workflow_ref` | Aggregator can parse version info |
| **Full report schema** | 12+ fields including test counts, tool metrics | All fields present and non-null |
| **Caller templates created** | `hub-python-ci.yml` and `hub-java-ci.yml` exist | Templates pass actionlint |
| **ADR-0014 written** | Documents the reusable workflow decision | ADR exists and is indexed |
| **Test matrix locked** | Fixtures cover Python 3.10/3.11/3.12, Java 17/21, Maven/Gradle | CI runs all matrix combinations |
| **actionlint gate** | Workflows validated before merge | Pre-commit or CI check passes |

---

### Milestone Validation (Fixtures as Continuous Validation Loop)

Each phase must be validated against the fixtures repo before proceeding:

| Milestone | Validation Task | Acceptance Criteria |
|-----------|-----------------|---------------------|
| **After Phase 1B (Workflow reports)** | Run `python-ci.yml` and `java-ci.yml` against fixtures (python-passing, java-passing) | `report.json` contains `schema_version: "2.0"`, all 12+ fields present |
| **After Phase 2 (Caller templates)** | Add `hub-ci.yml` callers to fixtures, run orchestrator dispatch | Workflows execute, reports collected, no errors |
| **After Phase 1C (Defaults fix)** | Verify no `coverage_min: 80` in generated configs | `grep -r "coverage_min: 80" templates/` returns empty |
| **After CLI detect** | Run `cihub detect` on all fixture types | Output matches expected language/tools for each fixture |
| **After CLI init** | Run `cihub init --dry-run` then `cihub init` on fixtures | Generated `.ci-hub.yml` validates against schema |
| **After CLI preflight** | Run `cihub preflight` on fixtures | Tools run, timeout works, cleanup happens |
| **Before v1.0.0 tag** | Full matrix run: Python 3.10/3.11/3.12, Java 17/21, Maven/Gradle, docker/no-docker, edge cases | All combinations pass |

**Validation Commands:**
```bash
# After workflow changes - verify report schema
gh workflow run python-ci.yml --repo jguida941/ci-cd-hub-fixtures
gh run download <run-id> -n ci-report
jq '.schema_version, .results.tests_passed, .tool_metrics' report.json

# After caller templates - test dispatch
gh workflow run hub-orchestrator.yml
# Verify all repos report back with full data

# CLI validation against fixtures
for fixture in python-vanilla python-poetry java-maven java-gradle; do
  cihub detect --repo fixtures/$fixture --explain
  cihub init --repo fixtures/$fixture --dry-run
  cihub validate --repo fixtures/$fixture
done
```

---

### Defaults Alignment

All examples, templates, and defaults will use `coverage_min: 70` to match `defaults.yaml` and workflow code.

**Files requiring `coverage_min: 80` → `70` change:**
- [ ] `templates/repo/.ci-hub.yml`
- [ ] `templates/hub/config/repos/monorepo-template.yaml`
- [ ] `templates/hub/config/repos/repo-template.yaml`
- [ ] `docs/reference/CONFIG_REFERENCE.md`
- [ ] `config/optional/extra-tests.yaml`
- [ ] Any examples in this migration doc

---

### Caller Templates Deliverable

**Current state:** `templates/repo/` contains only `.ci-hub.yml` - no caller workflows exist yet.

**Required deliverables:**
| File | Status | Description |
|------|--------|-------------|
| `templates/repo/hub-python-ci.yml` | ❌ Missing | Python caller with full 20+ input passthrough |
| `templates/repo/hub-java-ci.yml` | ❌ Missing | Java caller with full input passthrough |
| `templates/repo/.ci-hub.yml` | ⚠️ Needs update | Add `dispatch_workflow: hub-ci.yml` |

**Validation after creation:**
```bash
# Validate syntax
actionlint templates/repo/hub-python-ci.yml
actionlint templates/repo/hub-java-ci.yml

# Validate schema reference
grep "uses:.*python-ci.yml@v1" templates/repo/hub-python-ci.yml
grep "uses:.*java-ci.yml@v1" templates/repo/hub-java-ci.yml
```

---

### Phase 1A: ADR-0014 (Do First - Captures Decision)

| # | Task | Status |
|---|------|--------|
| 1.1 | Create `docs/adr/0014-reusable-workflow-migration.md` superseding ADR-0013 | [x] |
| 1.2 | Update `docs/adr/README.md` index to include ADR-0014 | [x] |

**ADR-0014 Content:**
- Status: Accepted (supersedes ADR-0013)
- Context: Dispatch templates drift, maintenance burden, 0% mutation scores
- Decision: Switch to reusable workflows with `workflow_call`, caller templates, semantic versioning
- Consequences: Repos use minimal callers, hub owns logic, automatic sync

---

### Phase 1B: Workflow Code Changes

| # | Task | File | Status |
|---|------|------|--------|
| 1.3 | Add `schema_version: "2.0"` to report | `python-ci.yml` | [x] |
| 1.4 | Add `tests_passed`, `tests_failed` to report | `python-ci.yml` | [x] |
| 1.5 | Add tool metrics: `ruff_errors`, `bandit_high`, `bandit_medium`, `black_issues`, `isort_issues`, `semgrep_findings`, `trivy_critical`, `trivy_high` | `python-ci.yml` | [x] |
| 1.6 | Mirror same schema for Java: `schema_version`, test counts, `checkstyle_issues`, `spotbugs_issues`, `pmd_violations`, `owasp_critical`, `owasp_high`, `semgrep_findings`, `trivy_critical`, `trivy_high` | `java-ci.yml` | [x] |
| 1.7 | Run `actionlint` locally to validate syntax | Both workflows | [x] |

---

### Phase 1C: Fix Defaults Inconsistency (`coverage_min: 80` → `70`)

| # | Task | File | Status |
|---|------|------|--------|
| 1.8 | Change `coverage_min: 80` → `70` | `templates/repo/.ci-hub.yml` | [ ] |
| 1.9 | Change `coverage_min: 80` → `70` | `templates/hub/config/repos/monorepo-template.yaml` | [ ] |
| 1.10 | Change `coverage_min: 80` → `70` | `templates/hub/config/repos/repo-template.yaml` | [ ] |
| 1.11 | Change `coverage_min: 80` → `70` | `docs/reference/CONFIG_REFERENCE.md` | [ ] |
| 1.12 | Change `coverage_min: 80` → `70` | `config/optional/extra-tests.yaml` | [ ] |
| 1.13 | Verify all examples use `70` | This document | [ ] |

---

### Phase 2: Create Caller Templates

| # | Task | File | Status |
|---|------|------|--------|
| 2.1 | Create Python caller (20+ inputs, pin to `@v1`) | `templates/repo/hub-python-ci.yml` | [x] |
| 2.2 | Create Java caller (all inputs, pin to `@v1`) | `templates/repo/hub-java-ci.yml` | [x] |
| 2.3 | Update existing file: add `dispatch_workflow: hub-ci.yml` | `templates/repo/.ci-hub.yml` | [ ] |
| 2.4 | Document caller usage, @v1 pinning, migration | `templates/README.md` | [ ] |

---

### Phase 3: Docs Debt Cleanup

**CRITICAL:** Many docs reference old `*-ci-dispatch.yml` templates. Update all to use new caller pattern.

**Scope:** All existing documentation that references `python-ci-dispatch.yml`, `java-ci-dispatch.yml`, or the old dispatch workflow pattern will be updated to reference the new `hub-ci.yml` caller + reusable workflow pattern. This includes setup guides, onboarding docs, mode explanations, and ADRs.

| # | Task | File | Changes | Status |
|---|------|------|---------|--------|
| 3.1 | Update dispatch mode section | `README.md` | Old `*-ci-dispatch.yml` → new `hub-ci.yml` caller | [ ] |
| 3.2 | Replace copy instructions | `docs/guides/ONBOARDING.md` | "copy dispatch template" → "copy caller template + .ci-hub.yml" | [ ] |
| 3.3 | Update dispatch explanation | `docs/guides/MODES.md` | Explain reusable workflow pattern | [ ] |
| 3.4 | Full rewrite | `docs/guides/DISPATCH_SETUP.md` | New setup uses caller, not full dispatch template | [ ] |
| 3.5 | Update template descriptions | `docs/guides/TEMPLATES.md` | Remove old dispatch templates, add callers | [ ] |
| 3.6 | Update workflow references | `docs/reference/TOOLS.md` | Any dispatch workflow references | [ ] |
| 3.7 | Update workflow guide | `docs/guides/WORKFLOWS.md` | Update any `*-ci-dispatch.yml` references | [ ] |
| 3.8 | Update roadmap | `docs/development/ROADMAP.md` | Update dispatch template references | [ ] |
| 3.9 | Update outstanding items | `docs/development/OUTSTANDING.md` | Update dispatch template references | [ ] |
| 3.10 | Update research notes | `docs/development/RESEARCH.md` | Update dispatch template references (if exists) | [ ] |
| 3.11 | Add superseded notice | `docs/adr/0013-dispatch-workflow-templates.md` | Header: "**Status: Superseded by [ADR-0014](./0014-reusable-workflow-migration.md)**" | [ ] |
| 3.12 | Update report schema docs | Various guides | Show new 12+ field schema with `schema_version` | [ ] |

**ADR Supersedence Approach:**
- **Decision:** Keep ADR-0013 in place (do NOT move to superseded/ folder)
- **Action:** Add header banner: `**Status: Superseded by [ADR-0014](./0014-reusable-workflow-migration.md)**`
- **Rationale:** Preserves history, avoids breaking links, standard ADR practice
- **ADR Index:** Update `docs/adr/README.md` to show ADR-0013 as superseded and link to ADR-0014

---

### Phase 3.5a: Documentation Walkthrough Validation

**After docs cleanup, before tagging:** Have Claude follow each doc end-to-end to set up a fresh repo and run workflows. Fix any unclear or broken steps immediately.

| # | Task | Doc | Validation |
|---|------|-----|------------|
| 3.13 | Walkthrough ONBOARDING.md | `docs/guides/ONBOARDING.md` | New user can onboard a repo from scratch |
| 3.14 | Walkthrough MODES.md | `docs/guides/MODES.md` | Mode selection is clear, examples work |
| 3.15 | Walkthrough DISPATCH_SETUP.md | `docs/guides/DISPATCH_SETUP.md` | Dispatch setup works with new caller pattern |
| 3.16 | Walkthrough TEMPLATES.md | `docs/guides/TEMPLATES.md` | Template instructions are accurate |
| 3.17 | Walkthrough WORKFLOWS.md | `docs/guides/WORKFLOWS.md` | Workflow setup is clear |
| 3.18 | Walkthrough MIGRATION_PLAYBOOK.md | `docs/guides/MIGRATION_PLAYBOOK.md` | Migration steps work, rollback tested |
| 3.19 | Walkthrough MONOREPOS.md | `docs/guides/MONOREPOS.md` | Monorepo setup works |
| 3.20 | Walkthrough README.md | `README.md` | Quick start works for new users |

**Walkthrough Process:**
```bash
# For each doc:
1. Start with a fresh test repo (or fixture)
2. Follow the doc step-by-step exactly as written
3. Run each command, verify expected output
4. If any step fails or is unclear:
   - Note the issue
   - Fix the doc immediately
   - Re-test the fix
5. Mark doc as validated
```

**Acceptance Criteria:**
- [ ] All 8 docs walked through successfully
- [ ] No broken commands or unclear instructions
- [ ] All examples use new caller pattern (not old `*-ci-dispatch.yml`)
- [ ] All examples use `coverage_min: 70`
- [ ] Screenshots/outputs match current behavior (if any)

---

### Phase 3.5b: Release Pipeline

| # | Task | File | Status |
|---|------|------|--------|
| 3.9 | Create release workflow (actionlint, gh-release, floating tag) | `.github/workflows/release.yml` | [ ] |
| 3.10 | Tag `v1.0.0` after Phase 1-2 complete and tested | Git tag | [ ] |
| 3.11 | Create floating `v1` tag pointing to latest v1.x.x | Git tag | [ ] |

---

### Phase 4: Test & Validate

| # | Task | Status |
|---|------|--------|
| 4.1 | Create feature branch `phase1-reusable-workflows` | [ ] |
| 4.2 | Push all changes to branch | [ ] |
| 4.3 | Update fixture repo to use `@phase1-reusable-workflows` | [ ] |
| 4.4 | Run workflow, download `ci-report` artifact | [ ] |
| 4.5 | Verify `report.json` has all 12+ fields including `schema_version` | [ ] |
| 4.6 | If passing: merge to main, tag v1.0.0 | [ ] |

---

### Phase 5: Orchestrator Update (Safe Rollout)

| # | Task | Status |
|---|------|--------|
| 5.1 | Add per-repo `dispatch_workflow` override support (already in schema) | [x] |
| 5.2 | Keep default as old workflow during migration (smoke-tests use old names) | [x] |
| 5.3 | Migrate fixture repos first (add `hub-ci.yml`, set override) | [x] |
| 5.4 | Migrate remaining repos one-by-one | [ ] |
| 5.5 | After all migrated: change default to `hub-ci.yml` (orchestrator defaults updated) | [x] |

**Note:** Option B (workflow existence check) requires `gh api` or `curl` in the orchestrator job.

**Dependency:** Orchestrator workflow must have `GH_TOKEN` or `GITHUB_TOKEN` with `contents: read` permission.

**Implementation:**
```bash
# Check if caller workflow exists in target repo
gh api repos/{owner}/{repo}/contents/.github/workflows/hub-ci.yml --silent && echo "exists" || echo "missing"

# Alternative with curl (no gh CLI dependency)
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/contents/.github/workflows/hub-ci.yml" | grep -q 200
```

**Fallback behavior:** If check fails or times out, use old dispatch workflow name to avoid breaking existing repos.

---

### Phase 6: Deprecate Old Templates

| # | Task | Status |
|---|------|--------|
| 6.1 | Remove `templates/python/python-ci-dispatch.yml` | [ ] |
| 6.2 | Remove `templates/java/java-ci-dispatch.yml` | [ ] |
| 6.3 | Final docs sweep for any remaining old template references | [ ] |

---

## Complete File List

### New Files to Create

| File | Phase |
|------|-------|
| `docs/adr/0014-reusable-workflow-migration.md` | 1A |
| `templates/repo/hub-python-ci.yml` | 2 |
| `templates/repo/hub-java-ci.yml` | 2 |
| `.github/workflows/release.yml` | 3.5 |
| `.github/workflows/cli-ci.yml` | CLI (P0/P1) |
| `cihub/commands/update.py` | CLI (P0/P1) |
| `tests/__init__.py` | CLI (P0/P1) |
| `tests/test_detect.py` | CLI (P0/P1) |
| `tests/test_init.py` | CLI (P0/P1) |
| `tests/test_update.py` | CLI (P0/P1) |
| `tests/test_validate.py` | CLI (P0/P1) |
| `tests/golden/` | CLI (P0/P1) |
| `docs/guides/MIGRATION_PLAYBOOK.md` | E (Enhancements) |
| `.pre-commit-config.yaml` | E (Enhancements) |
| `renovate.json` or `.github/dependabot.yml` | E (Enhancements) |
| `docs/adr/0015-cli-architecture.md` | CLI (P3) |

### Files to Modify

| File | Phase | Change |
|------|-------|--------|
| `.github/workflows/python-ci.yml` | 1B | Add schema_version, test counts, tool metrics to report |
| `.github/workflows/java-ci.yml` | 1B | Mirror Python schema |
| `templates/repo/.ci-hub.yml` | 1C, 2 | Fix coverage_min, add dispatch_workflow |
| `templates/hub/config/repos/monorepo-template.yaml` | 1C | Fix coverage_min |
| `templates/hub/config/repos/repo-template.yaml` | 1C | Fix coverage_min |
| `templates/README.md` | 2 | Document caller templates |
| `docs/adr/README.md` | 1A | Add ADR-0014 to index |
| `docs/adr/0013-dispatch-workflow-templates.md` | 3 | Add superseded notice |
| `docs/guides/ONBOARDING.md` | 3 | Update to caller pattern |
| `docs/guides/MODES.md` | 3 | Update dispatch explanation |
| `docs/guides/DISPATCH_SETUP.md` | 3 | Full rewrite for callers |
| `docs/guides/TEMPLATES.md` | 3 | Update template list |
| `docs/guides/WORKFLOWS.md` | 3 | Update dispatch references |
| `docs/development/ROADMAP.md` | 3 | Update dispatch references |
| `docs/development/OUTSTANDING.md` | 3 | Update dispatch references |
| `docs/development/RESEARCH.md` | 3 | Update dispatch references (if exists) |
| `docs/reference/CONFIG_REFERENCE.md` | 1C, 3 | Fix coverage_min, update schema docs |
| `docs/reference/TOOLS.md` | 3 | Update workflow references |
| `config/optional/extra-tests.yaml` | 1C | Fix coverage_min |
| `README.md` | 3 | Update dispatch mode section |

### Files to Delete (Phase 6)

| File |
|------|
| `templates/python/python-ci-dispatch.yml` |
| `templates/java/java-ci-dispatch.yml` |

---

## Execution Order

```
Phase 1A: ADR-0014 (decision documentation)
    ↓
Phase 1B: Workflow code (Python CI → Java CI)
    ↓
Phase 1C: Fix defaults (70 everywhere)
    ↓
Phase 2: Create caller templates
    ↓
Phase 3: Docs cleanup (all guides + README)
    ↓
Phase 3.5: Release workflow
    ↓
Phase 4: Feature branch → test → merge → tag v1.0.0
    ↓
Phase 5: Orchestrator rollout
    ↓
Phase 6: Deprecate old templates
```

---

## CLI Quality & Testing Matrix (Production-Grade)

### Priority Levels
- **P0/P1:** Must-add now (blocks v1 release)
- **P2:** Good-to-have (improves robustness)
- **P3:** Future/backlog (extensibility)

---

### P0/P1: Must-Add Now

#### CLI: `cihub update` Command

Add command to re-sync existing repos with latest templates (no copier dependency).

| # | Task | Status |
|---|------|--------|
| CLI.1 | Implement `cihub update --repo <path>` command | [ ] |
| CLI.2 | Diff-aware apply: detect changes, show diff, apply | [ ] |
| CLI.3 | `--dry-run` flag to preview changes without writing | [ ] |
| CLI.4 | Idempotent: running twice produces same result | [ ] |
| CLI.5 | Handle `.ci-hub.yml` + `hub-ci.yml` updates | [ ] |

**Acceptance Criteria:**
- `cihub update --dry-run` shows what would change
- `cihub update` is idempotent (running twice = no diff)
- Preserves user customizations in `.ci-hub.yml` (merge, don't overwrite)

#### CLI: Test Suite + CI Workflow

| # | Task | Status |
|---|------|--------|
| CLI.6 | Create `tests/` directory with pytest structure | [ ] |
| CLI.7 | Unit tests for detection engine (python.py, java.py, docker.py) | [ ] |
| CLI.8 | Unit tests for generators (config.py, workflow.py) | [ ] |
| CLI.9 | E2E tests against fixtures repo | [ ] |
| CLI.10 | Create `.github/workflows/cli-ci.yml` | [ ] |
| CLI.11 | Add `cihub --help` smoke test in CI | [ ] |
| CLI.12 | Add editable install + wheel/sdist build check | [ ] |

**CLI CI Workflow:**
```yaml
name: CLI CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[cli,dev]"
      - run: cihub --help  # Smoke test
      - run: pytest tests/ -v --cov=cihub
      - run: pip wheel . --no-deps  # Build check
```

**Acceptance Criteria:**
- CI runs on every PR to hub-release
- Tests cover detect, init, validate, update commands
- Coverage > 80% for CLI code

#### CLI: E2E Tests Against Fixtures

| # | Task | Status |
|---|------|--------|
| CLI.13 | Clone fixtures repo in CI | [ ] |
| CLI.14 | Run `cihub detect` on each fixture, assert output | [ ] |
| CLI.15 | Run `cihub init --dry-run` on each fixture | [ ] |
| CLI.16 | Run `cihub init` (write mode) on each fixture | [ ] |
| CLI.17 | Validate generated `.ci-hub.yml` against schema | [ ] |
| CLI.18 | Compare generated files against golden files | [ ] |
| CLI.19 | Run `cihub preflight` on each fixture | [ ] |

**Golden File Testing:**
```
tests/golden/
├── python-vanilla/
│   ├── expected.ci-hub.yml
│   └── expected.hub-ci.yml
├── python-poetry/
├── java-maven/
├── java-gradle/
└── monorepo-mixed/
```

#### Test Matrix Expansion (Fixtures Repo)

| Category | Scenarios | Status |
|----------|-----------|--------|
| **Python versions** | 3.10, 3.11, 3.12 | [ ] |
| **Python pkg mgrs** | pip/requirements.txt, poetry, uv | [ ] |
| **Python structures** | flat, src-layout, monorepo subdir | [ ] |
| **Python edge cases** | no-tests, legacy setup.py, private deps placeholder | [ ] |
| **Java versions** | 17, 21 | [ ] |
| **Java build tools** | Maven, Gradle | [ ] |
| **Java structures** | single-module, multi-module, Spring Boot | [ ] |
| **Docker** | dockerfile-only, docker-compose, no-docker | [ ] |
| **Monorepo** | multiple python apps, multiple java modules, mixed languages, nested paths | [ ] |
| **Edge cases** | empty repo, no-config, ambiguous roots, missing tools | [ ] |

**Expanded Fixtures Structure:**
```
ci-cd-hub-fixtures/
├── python/
│   ├── vanilla-3.10/
│   ├── vanilla-3.11/
│   ├── vanilla-3.12/
│   ├── poetry/
│   ├── uv/
│   ├── src-layout/
│   ├── no-tests/
│   ├── legacy-setup-py/
│   ├── private-deps-placeholder/
│   └── with-docker/
├── java/
│   ├── maven-17/
│   ├── maven-21/
│   ├── gradle-17/
│   ├── gradle-21/
│   ├── multi-module/
│   └── spring-boot/
├── monorepo/
│   ├── python-apps/
│   ├── java-modules/
│   ├── mixed-languages/
│   └── nested-deep/
├── edge-cases/
│   ├── empty/
│   ├── no-config/
│   ├── ambiguous-roots/
│   └── missing-tools/
└── docker/
    ├── dockerfile-only/
    ├── docker-compose/
    └── self-hosted-runner-placeholder/
```

#### Preflight Timeout & Cleanup

| # | Task | Status |
|---|------|--------|
| CLI.20 | Add timeout to all preflight tool runs (default 5 min) | [ ] |
| CLI.21 | Add cleanup handler for interrupted runs | [ ] |
| CLI.22 | `--timeout` flag to override default | [ ] |

---

### P2: Good-to-Have

#### Act Integration for Preflight (Optional)

| # | Task | Status |
|---|------|--------|
| P2.1 | Add `cihub preflight --use-act` flag | [ ] |
| P2.2 | Document act limitations (Linux only, secrets tricky) | [ ] |
| P2.3 | Graceful fallback if act not installed | [ ] |

**Usage:**
```bash
# Default: run tools directly
cihub preflight --repo /path/to/app

# With act: run actual workflow locally (requires Docker)
cihub preflight --repo /path/to/app --use-act
```

#### Detection Caching

| # | Task | Status |
|---|------|--------|
| P2.4 | Cache detection results in `.cihub-cache.json` | [ ] |
| P2.5 | Invalidate cache on file changes (mtime check) | [ ] |
| P2.6 | `--no-cache` flag to force re-scan | [ ] |

#### GHES / GitHub.com Dual Testing

| # | Task | Status |
|---|------|--------|
| P2.7 | Add GHES-like runner image test (if applicable) | [ ] |
| P2.8 | Document GHES differences (actions versions, permissions) | [ ] |
| P2.9 | Test with `ubuntu-latest` vs specific versions | [ ] |

#### Network-Restricted Mode

| # | Task | Status |
|---|------|--------|
| P2.10 | Ensure `cihub detect` works fully offline | [ ] |
| P2.11 | `cihub preflight` handles missing network with clear errors | [ ] |
| P2.12 | Document required network access and permissions | [ ] |

---

### P3: Future/Backlog

#### Plugin Architecture for Detection

| # | Task | Status |
|---|------|--------|
| P3.1 | Design simple plugin registry for custom detection rules | [ ] |
| P3.2 | Allow `.cihub-plugins/` directory for custom detectors | [ ] |
| P3.3 | Document plugin API | [ ] |

**Note:** Keep simple for v1. Don't over-engineer.

#### ADR for CLI

| # | Task | Status |
|---|------|--------|
| P3.4 | Create ADR-0015 for CLI architecture decisions | [ ] |

---

### CLI Acceptance Criteria Summary

| Criteria | Requirement |
|----------|-------------|
| `cihub --help` | Returns 0, shows usage |
| `cihub detect` | Works on all fixtures, matches expected output |
| `cihub init --dry-run` | Shows what would be written, no side effects |
| `cihub init` | Generates valid schema-compliant configs |
| `cihub update` | Idempotent, diff-aware, preserves customizations |
| `cihub preflight` | Runs tools, times out gracefully, cleans up |
| `cihub validate` | Catches invalid configs, clear error messages |
| CLI CI | Runs on every PR, passes on all Python versions |
| Test coverage | > 80% for CLI code |
| Golden files | Generated files match expected output |

---

## Additional Enhancements (From Research)

### Compatibility Guardrails

| # | Task | Status |
|---|------|--------|
| E.1 | Test reusable workflows on GitHub.com (and GHES if applicable) | [ ] |
| E.2 | Document any GHES-specific constraints (runner images, Actions versions) | [ ] |
| E.3 | Add action pinning guidance: pin to major versions (`@v4` not `@main`) | [ ] |
| E.4 | Add `actions/cache` usage where safe (dependencies, build artifacts) | [ ] |

### Security & Secrets

| # | Task | Status |
|---|------|--------|
| E.5 | Document OIDC as preferred auth pattern (avoid PATs where possible) | [ ] |
| E.6 | Ensure caller templates use `secrets: inherit` + minimal extra secrets | [ ] |
| E.7 | Create permissions checklist: `actions: write` (orchestrator), `id-token: write` (OIDC only) | [ ] |
| E.8 | Add security hardening notes to caller template docs | [ ] |

### Release Hygiene

| # | Task | Status |
|---|------|--------|
| E.9 | Add Renovate/Dependabot config to track `@v1` → latest `v1.x` in caller templates | [ ] |
| E.10 | Set deprecation timeline for `*-ci-dispatch.yml` (date + removal version) | [ ] |
| E.11 | Document deprecation in plan and user-facing docs | [ ] |

**Deprecation Timeline:**
- **Phase 5 complete:** `*-ci-dispatch.yml` marked deprecated
- **v2.0.0 release:** `*-ci-dispatch.yml` removed from templates
- **Target removal:** 90 days after v1.0.0 release

### Validation & Fixtures

| # | Task | Status |
|---|------|--------|
| E.12 | Expand test matrix: Maven + Gradle, Python 3.10/3.11/3.12 | [ ] |
| E.13 | Add GHES-like environment test (if relevant) | [ ] |
| E.14 | Add `actionlint` as pre-commit hook or CI gate | [ ] |
| E.15 | Create `.pre-commit-config.yaml` with actionlint hook | [ ] |

### Observability

| # | Task | Status |
|---|------|--------|
| E.16 | Add `schema_version: "2.0"` to all report.json outputs | [ ] |
| E.17 | Add metadata block to report.json: `workflow_version`, `workflow_ref` | [ ] |
| E.18 | Document schema versioning strategy for cross-version parsing | [ ] |

**Report Metadata Block:**
```json
{
  "schema_version": "2.0",
  "metadata": {
    "workflow_version": "v1.2.0",
    "workflow_ref": "jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1",
    "generated_at": "2025-01-15T10:30:00Z"
  },
  ...
}
```

### Docs: Migration Playbook

Add a new section to docs with:

| # | Task | Status |
|---|------|--------|
| E.19 | Create `docs/guides/MIGRATION_PLAYBOOK.md` | [ ] |
| E.20 | Document precheck steps (verify caller present) | [ ] |
| E.21 | Document rollout steps (per-repo override) | [ ] |
| E.22 | Document fallback (old workflow name) | [ ] |
| E.23 | Document rollback steps | [ ] |
| E.24 | Create "Known Limitations" list | [ ] |

**Known Limitations to Document:**
- Network-restricted runners
- GHES version differences
- Private registries requiring auth
- Self-hosted runner constraints
- Rate limits on workflow dispatch

---

## References (From Research)

### GitHub Best Practices
- [Scaling GitHub Actions Reusability - GitHub Well-Architected](https://wellarchitected.github.com/library/collaboration/recommendations/scaling-actions-reusability/)
- [Building Organization-Wide Governance - GitHub Blog](https://github.blog/2023-04-05-building-organization-wide-governance-and-re-use-for-ci-cd-and-automation-with-github-actions/)
- [Enforcing Workflows with Repository Rules - GitHub Blog](https://github.blog/enterprise-software/ci-cd/enforcing-code-reliability-by-requiring-workflows-with-github-repository-rules/)
- [DRY in GitHub Actions with Reusable Workflows](https://rnd.ultimate.ai/blog/central-workflows)
- [Multi-Project CI/CD - Reusable Workflows](https://multiprojectdevops.github.io/tutorials/3_reusable_workflows/)

### Platform Engineering
- [Golden Paths - Red Hat](https://www.redhat.com/en/topics/platform-engineering/golden-paths)
- [Golden Paths for Engineering Consistency - Google Cloud](https://cloud.google.com/blog/products/application-development/golden-paths-for-engineering-execution-consistency)
- [How to Build Golden Paths Developers Will Use - Jellyfish](https://jellyfish.co/library/platform-engineering/golden-paths/)
- [Internal Developer Platforms in 2025](https://infisical.com/blog/navigating-internal-developer-platforms)

### Tooling
- [Renovate for GitHub Actions](https://docs.renovatebot.com/modules/manager/github-actions/)
- [GitHub Workflow Templates](https://docs.github.com/en/actions/how-tos/reuse-automations/create-workflow-templates)
- [Actions Template Sync](https://github.com/marketplace/actions/actions-template-sync)

### Key Insights from Research

1. **2025 Updates:** GitHub now supports 10 levels of workflow nesting and 50 workflow calls per run
2. **Enterprise Pattern:** Dedicated `.github` org repo for shared workflows is standard
3. **Golden Path Principle:** Self-service + guardrails, not gatekeeping
4. **Versioning:** Production should always pin to tags, never `@main`
5. **Renovate Integration:** Can auto-update workflow refs when new tags are released

---

## Progress Tracking

**Last Updated:** 2025-12-18

---

## Known Issues & Relaxed Thresholds (TODO: Fix Later)

**Status:** These are temporary workarounds to allow testing to proceed. Must be revisited before production release.

### Mutation Testing Issues

| Fixture | Issue | Relaxation | Root Cause | Status |
|---------|-------|------------|------------|--------|
| `python-passing` | Mutation score always 0% | `mutation_score_min: 0` | `mutmut` not detecting/running tests properly | Still investigating |
| `python-failing` | Cannot run mutation testing | `mutation_score_min: 0` | Tests intentionally fail - mutmut requires green suite | Expected behavior |
| `java-passing` | ✅ **FIXED** - 92% mutation score | Default thresholds | Was using `-DskipTests` with PITest | **RESOLVED 2025-12-18** |
| `java-failing` | Cannot run mutation testing | `mutation_score_min: 0` | Tests intentionally fail - PITest requires green suite | Expected behavior |

**PITest Fix (2025-12-18):**
- **Problem:** PITest was invoked with `-DskipTests`, which skips mutation detection
- **Solution:** Removed `-DskipTests` from PITest invocation, runs in separate job
- **Result:** java-passing now shows 92% mutation score
- **Note:** java-failing cannot run PITest (intentional - "green suite" requirement)

**mutmut Investigation Still Needed:**
- `mutmut run` appears to exit with 0 but shows no mutations
- Likely issue: test discovery not working, or source path detection broken
- May need explicit `--paths-to-mutate` with absolute paths

### Security Scanner Thresholds

| Fixture | Issue | Relaxation | Rationale |
|---------|-------|------------|-----------|
| `java-failing` | Semgrep finds issues | `max_semgrep_findings: 999` | Intentional - failing fixture should have findings, we want to capture them not fail |
| `python-failing` | Semgrep finds issues | `max_semgrep_findings: 999` | Same - allows capturing findings without failing the build |
| `java-failing` | OWASP finds vulnerabilities | `owasp_cvss_fail: 11` | 11 > max possible CVSS score (10), so never fails |
| Both failing | High vulnerability counts | `max_critical_vulns: 999`, `max_high_vulns: 999` | Allow findings to be captured without failing |

### Docker/Trivy Fixtures (Completed 2025-12-18)

**Decision:** Keep non-docker fixtures clean (no Dockerfiles) to validate non-container code quality paths. Created dedicated docker fixtures for Trivy/Docker testing.

**Created:**
- `python-with-docker/` - Python app with minimal Dockerfile
- `java-with-docker/` - Java app with minimal Dockerfile

**Caller workflow jobs added:**
- `ci-docker` job in `hub-python-ci.yml` → `workdir: 'python-with-docker'`
- `ci-docker` job in `hub-java-ci.yml` → `workdir: 'java-with-docker'`

| Fixture | Has Dockerfile | run_trivy | run_docker | Purpose |
|---------|----------------|-----------|------------|---------|
| python-passing | No | skips | skips | Core code quality |
| python-failing | No | skips | skips | Core code quality |
| python-with-docker | Yes | runs | runs | Container scanning |
| java-passing | No | skips | skips | Core code quality |
| java-failing | No | skips | skips | Core code quality |
| java-with-docker | Yes | runs | runs | Container scanning |

### New Inputs Added (Phase 1B)

| Input | Added To | Default | Purpose |
|-------|----------|---------|---------|
| `artifact_prefix` | Java CI, Python CI | `''` | Prevents artifact name collisions when multiple jobs call same reusable workflow |
| `max_semgrep_findings` | Java CI, Python CI | `0` | Configurable threshold for Semgrep findings (previously hardcoded to fail on any) |

### Fixture Caller Workflow Relaxations

**File: `ci-cd-hub-fixtures/.github/workflows/hub-java-ci.yml`**
```yaml
ci-passing:
  # Uses default thresholds except mutation_score_min (mutmut broken)
  artifact_prefix: 'java-passing-'

ci-failing:
  # All thresholds relaxed to capture findings without failing:
  coverage_min: 0
  mutation_score_min: 0
  owasp_cvss_fail: 11
  max_critical_vulns: 999
  max_high_vulns: 999
  max_semgrep_findings: 999
  artifact_prefix: 'java-failing-'
```

**File: `ci-cd-hub-fixtures/.github/workflows/hub-python-ci.yml`**
```yaml
ci-passing:
  # mutation_score_min: 0 because mutmut broken
  mutation_score_min: 0
  artifact_prefix: 'python-passing-'

ci-failing:
  # All thresholds relaxed:
  coverage_min: 0
  mutation_score_min: 0
  max_critical_vulns: 999
  max_high_vulns: 999
  max_semgrep_findings: 999
  artifact_prefix: 'python-failing-'
```

### Action Items After Testing Complete

1. **Debug mutmut** - Get mutation testing working for Python fixtures
2. ~~**Debug PITest**~~ - ✅ FIXED 2025-12-18 (removed `-DskipTests`, now 92%)
3. **Restore thresholds** - Once tools work, set appropriate thresholds for passing fixtures
4. ~~**Create Docker fixtures**~~ - ✅ Done 2025-12-18
5. **Update documentation** - Remove relaxation notes when issues fixed
6. **Fix OWASP** - Upgraded to dependency-check-maven 12.1.9 (testing in progress)

### Documentation Deliverables (Before v1.0.0)

Once workflows are stable, create user-facing documentation:

1. **Quick Start Guide** - Minimal caller workflow example
2. **Tool Versions Reference** - All tools, versions, what they check:
   | Tool | Plugin/Package | Version |
   |------|----------------|---------|
   | OWASP Dependency Check | dependency-check-maven | 12.1.9 |
   | SpotBugs | spotbugs-maven-plugin | 4.8.3.1 |
   | PITest | pitest-maven | 1.15.3 |
   | Checkstyle | maven-checkstyle-plugin | 3.3.1 |
   | PMD | maven-pmd-plugin | 3.21.2 |
   | JaCoCo | jacoco-maven-plugin | 0.8.11 |
   | Trivy | aquasecurity/trivy-action | 0.28.0 |
   | CodeQL | github/codeql-action | v3 |
3. **Threshold Reference** - Default values and how to customize
4. **Troubleshooting Guide** - Common issues (PITest green suite, OWASP rate limiting, etc.)
5. **Upgrade Notes** - When tool versions change

---

## Pending ADR Candidates

These policy decisions should be formalized in ADRs before v1.0.0 release:

| ADR Topic | Current State | Decision Needed |
|-----------|---------------|-----------------|
| **Pinning/versioning strategy** | Callers use `@phase1b-workflow-schema` branch | When to move `@main` → `@v1`, how to handle breaking changes, floating tags policy |
| **Mutation testing policy** | `continue-on-error: true`, failures warn only | Should mutmut/pitest failures block the build or just warn? Default `run_mutmut`/`run_pitest` value? |
| **Docker/Trivy fixture scope** | Dedicated docker fixtures created | Keep non-docker fixtures clean vs add Dockerfiles everywhere |
| **Default tool gates** | Expensive scanners (`semgrep`, `trivy`, `codeql`) opt-in (default: false) | Lock in current defaults or change policy |
| **workflow_version tracking** | Hardcoded in report.json | How to update on release, whether to automate |

### Recommended ADR Actions

1. **ADR-0015: Workflow Versioning & Release Policy**
   - When to tag releases (v1.0.0, v1.1.0)
   - Floating tag strategy (v1 → latest v1.x.x)
   - Breaking change communication
   - Deprecation timeline for old refs

2. **ADR-0016: Mutation Testing Policy**
   - Default enabled/disabled for mutmut/pitest
   - Whether failures block or warn
   - Minimum mutation score thresholds
   - Timeout/performance considerations

3. **ADR-0017: Scanner Tool Defaults**
   - Which scanners on-by-default vs opt-in
   - Rationale for expensive tool gating
   - Guidance for repos enabling optional scanners

4. **ADR-0018: Fixtures & Testing Strategy**
   - Branching: keep fixtures workflows on long-lived test branch (`test-phase1b-schema`), trigger via `--ref`
   - Fixture intent: pass/fail variants per language, dedicated docker fixtures, document expected failures
   - Caller config: pin to hub tag/branch, set workdir per fixture, which tools enabled for each
   - Validation criteria: what to check in ci-report (schema_version, test counts, tool_metrics, acceptable skips)
   - Change control: when to update fixtures, how to avoid breaking default branch

---

### Part 1: Reusable Workflows

| Phase | Status | Notes |
|-------|--------|-------|
| 1A: ADR-0014 | ✅ Complete | 2025-12-17: Created ADR-0014, updated index |
| 1A+: ADRs 0015-0018 | ✅ Complete | 2025-12-18: Versioning, mutation, scanner defaults, fixtures strategy |
| 1B: Workflow Code | 🔄 Active | See detailed status below |
| 1C: Defaults Fix | ⚪ Not Started | `coverage_min: 80` → `70` |
| 2: Caller Templates | ⚪ Not Started | |
| 3: Docs Cleanup | ⚪ Not Started | 12 files to update |
| 3.5a: Docs Walkthrough | ⚪ Not Started | 8 docs to validate end-to-end |
| 3.5b: Release Pipeline | ⚪ Not Started | |
| 4: Test & Validate | 🔄 Active | Running fixture tests |
| 5: Orchestrator Rollout | ⚪ Not Started | |
| 6: Deprecate Old | ⚪ Not Started | |

**Phase 1B Detailed Status (2025-12-18):**

| Fix | Status | Notes |
|-----|--------|-------|
| Report schema 12+ fields | ✅ Done | Both Python CI and Java CI |
| Lint/CodeQL workdir scoping | ✅ Done | Uses `inputs.workdir` |
| Trivy scan-ref and output path | ✅ Done | Fixed paths |
| Maven explicit goal execution | ✅ Done | `checkstyle:checkstyle`, `spotbugs:spotbugs`, etc. |
| Split Maven build phases | ✅ Done | Lifecycle first, then analysis with `-DskipTests` |
| PITest fix | ✅ Done | Removed `-DskipTests`, now 92% mutation score |
| `if: always()` on dependent jobs | ✅ Done | Jobs run even when build-test fails |
| OWASP dependency-check | 🔄 Testing | Upgraded to 12.1.9 |
| Orchestrator artifact matching | ✅ Done | Match `*ci-report` not exact `ci-report` |
| mutmut Python | ❌ Broken | Still showing 0%, needs investigation |

### Part 2: CLI Tool (`cihub`)

| Phase | Status | Notes |
|-------|--------|-------|
| 6: Core Commands | ⚪ Not Started | detect, init, validate |
| 7: Detection Engine | ⚪ Not Started | Python, Java, Docker rules |
| 8: Config Generation | ⚪ Not Started | .ci-hub.yml, hub-ci.yml |
| 9: Local Preflight | ⚪ Not Started | Tool runners, timeout/cleanup |
| 10: GitHub Verification | ⚪ Not Started | verify-github command |
| CLI P0/P1: update command | ⚪ Not Started | Diff-aware sync |
| CLI P0/P1: Test Suite | ⚪ Not Started | pytest, golden files, CI |
| CLI P0/P1: E2E Tests | ⚪ Not Started | Against fixtures repo |
| CLI P2: act integration | ⚪ Not Started | Optional |
| CLI P2: Caching | ⚪ Not Started | Optional |

### Part 3: Test Fixtures Expansion

| Phase | Status | Notes |
|-------|--------|-------|
| Python fixtures | ⚪ Not Started | 3.10/3.11/3.12, pip/poetry/uv |
| Java fixtures | ⚪ Not Started | 17/21, Maven/Gradle |
| Monorepo fixtures | ⚪ Not Started | Mixed languages, nested |
| Edge case fixtures | ⚪ Not Started | Empty, no-config, ambiguous |

### Part 4: Aggregation (from ROADMAP Phase 4)

**Prerequisite:** Part 1 complete (reusable workflows generating correct reports)

**Status:** ✅ Mostly implemented - blocked by Part 1 (bad report.json from old templates)

| Task | Status | Notes |
|------|--------|-------|
| Define `hub-report.json` schema | ✅ Done | In `hub-orchestrator.yml` |
| `aggregate_reports.py` script | ✅ Done | Loads reports, generates summary |
| HTML dashboard generation | ✅ Done | In `aggregate_reports.py` |
| Orchestrator `aggregate-reports` job | ✅ Done | In `hub-orchestrator.yml` |
| Poll for distributed run completion | ✅ Done | 30 min timeout, exponential backoff |
| Download artifacts from distributed runs | ✅ Done | Downloads `ci-report` artifact |
| Parse `report.json` from artifacts | ✅ Done | Extracts metrics |
| Historical data collection | ⚪ Not Started | Store over time |

**How It Works (Already Implemented):**
```
Orchestrator dispatches → Repos run CI → Generate ci-report artifact
     ↓
Orchestrator polls until complete (30 min max)
     ↓
Downloads ci-report artifact from each repo
     ↓
Parses report.json → aggregate_reports.py → hub-report.json
```

**Why It Wasn't Working:**
- Old dispatch templates generated broken `report.json` (4 fields vs 12+)
- Part 1 fixes this - reusable workflows generate correct schema

**What's Missing:**
- Historical trends (store data over time)
- Part 1 completion (to get correct reports)

**Deliverables:**
- [x] `aggregate_reports.py` script
- [x] Orchestrator polling/download
- [x] Basic `hub-report.json` generation
- [ ] Historical data collection

### Part 5: Dashboard (from ROADMAP Phase 5)

**Prerequisite:** Part 4 complete (aggregation working)

**Status:** Partially implemented - HTML generation exists in `aggregate_reports.py`

| Task | Status | Notes |
|------|--------|-------|
| Create dashboard HTML/JS | ✅ Done | In `aggregate_reports.py` |
| Overview with all repos | ✅ Done | Table with status, coverage, mutation |
| Summary cards | ✅ Done | Total repos, avg coverage, avg mutation |
| Configure GitHub Pages | ⚪ Not Started | gh-pages branch |
| Generate metrics.json on each run | ⚪ Not Started | Data for JS charts |
| Publish to gh-pages branch | ⚪ Not Started | Auto-publish workflow |
| Add historical trend charts | ⚪ Not Started | Requires storing history |
| Drill-down per repo | ⚪ Not Started | Detailed view |

**Validation checklist (what to verify after a run):**
- `report.json` exists and parses (`jq . report.json`).
- `schema_version` is "2.0".
- `results.tests_passed`/`tests_failed` are populated (not null).
- `tool_metrics` are populated for enabled tools (ruff/bandit/black/isort/pip_audit/semgrep/trivy for Python; checkstyle/spotbugs/pmd/owasp/semgrep/trivy for Java).
- `tools_ran` matches inputs (true when enabled, false when skipped).
- Threshold gates behave: coverage/mutation/owasp/trivy/semgrep fail when over limits (except fixtures with relaxed thresholds).
- Artifacts exist with expected names (ci-report plus tool artifacts).


**What Works:**
- `aggregate_reports.py --format html` generates dashboard
- Dark theme, responsive layout
- Summary cards (total repos, avg coverage, avg mutation)
- Table with per-repo status

**What's Missing:**
- GitHub Pages publishing workflow
- Historical trend charts
- Per-repo drill-down

**Deliverables:**
- [x] Static dashboard HTML generation
- [ ] GitHub Pages deployment
- [ ] Historical trends
- [ ] Accessible via public URL

**Validation checklist (what to verify after a run):**
- `report.json` exists and parses (`jq . report.json`).
- `schema_version` is `"2.0"`.
- `results.tests_passed`/`tests_failed` are populated (not null).
- `tool_metrics` are populated for enabled tools (ruff/bandit/black/isort/pip_audit/semgrep/trivy for Python; checkstyle/spotbugs/pmd/owasp/semgrep/trivy for Java).
- `tools_ran` matches inputs (true when enabled, false when skipped).
- Threshold gates behave: coverage/mutation/owasp/trivy/semgrep fail when over limits (except fixtures with documented relaxed thresholds).
- Artifacts exist with expected names (ci-report plus tool artifacts).

**Production validation approach:**
- Keep failing fixtures confined to the fixtures repo (not production callers); they exist to assert detection paths with relaxed thresholds.
- Use passing fixtures (strict thresholds) as the reference for production templates.
- ✅ **Reusable validation script:** `scripts/validate_report.sh` (see ADR-0019)
- Production callers should use strict thresholds; do not copy relaxed fixture thresholds.
- Plan to upstream the report validation checks into production CI once fixture validation is stable.

**Validation script usage:**

```bash
# Passing fixture - strict (zero issues expected)
./scripts/validate_report.sh --report ./report/report.json --stack python --expect-clean

# Failing fixture - must detect issues
./scripts/validate_report.sh --report ./report/report.json --stack java --expect-issues --verbose
```

**Script features:**
- `--stack python|java` selects appropriate metrics
- `--expect-clean` validates zero issues (passing fixtures)
- `--expect-issues` validates issue detection (failing fixtures)
- `--coverage-min <n>` sets coverage threshold (default: 70)
- `--verbose` shows all checks, not just failures
- GitHub Actions annotation format (`::error::`, `::warning::`)
- Exit 0 (pass) or 1 (fail) for CI integration

### Part 6: Polish & Release (from ROADMAP Phase 8)

| Task | Status | Notes |
|------|--------|-------|
| Update existing docs with tool versions | ⚪ Not Started | TOOLS.md, TROUBLESHOOTING.md |
| Create CHANGELOG.md | ⚪ Not Started | All changes since start |
| Update README.md | ⚪ Not Started | Current state |
| Tag and publish v1.0.0 | ⚪ Not Started | First stable release |

### Part 7: PyQt6 GUI (Future - P3)

**Intent:** Optional GUI wrapper over the CLI. The GUI calls the existing `cihub` commands; it does not replace the CLI.

| Task | Status | Notes |
|------|--------|-------|
| Define GUI scope (editor, validator, preview) | ⚪ Not Started | Keep scope thin: call CLI, render results |
| Build YAML editor/viewer (QTextEdit + syntax) | ⚪ Not Started | Read-only preview + optional edits |
| Wire CLI calls (`cihub detect/init/validate`) | ⚪ Not Started | Shell out to CLI; reuse logic |
| Result preview (reports, dashboard embed) | ⚪ Not Started | Render artifacts/HTML produced by CLI |
| Packaging | ⚪ Not Started | Optional; not required for v1 |

**Notes:**
- Priority P3: only after Parts 1–6 and CLI are stable.
- GUI must be a thin layer; CLI remains the source of truth and CI-compatible interface.
- No additional DSL/transpilation; YAML continues to be generated by the CLI/templates.

### Enhancements

| Enhancement | Status | Notes |
|-------------|--------|-------|
| Compatibility Guardrails | ⚪ Not Started | GHES, action pinning |
| Security & Secrets | ⚪ Not Started | OIDC docs, permissions |
| Release Hygiene | ⚪ Not Started | Renovate, deprecation timeline |
| Observability | ⚪ Not Started | schema_version, metadata |
| Migration Playbook | ⚪ Not Started | Precheck, rollout, rollback |
