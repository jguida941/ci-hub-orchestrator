# Workflows Reference

> Extracted from plan.md. TODO: Verify against actual workflow files.

**Templates & Profiles:** For ready-made repo configs and tool profiles, see `templates/README.md` (apply via `python scripts/apply_profile.py ...`).

---

## Hub: Run All Repos (Central Execution)

**File:** `.github/workflows/hub-run-all.yml`

Clones each configured repository and runs build, tests, and quality tools in the hub run. This is the primary workflow for the "repos stay clean" design.

### Triggers
- `workflow_dispatch` (manual)
- `schedule` (nightly)
- `push` to hub repo when `config/repos/*.yaml` changes

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `repos` | string | Comma-separated repo names to run. Empty means all repos in `config/repos/`. |
| `skip_mutation` | boolean | If true, skip mutation testing steps for faster execution. |

### Outputs and Artifacts
- Per-repo artifacts such as test reports and coverage reports
- GitHub Step Summary with a per-repo metrics table (coverage, mutation, lint, security counts where applicable)
- Per-repo JSON report under `reports/<repo>/report.json` (used by aggregation)

### Notes
- Central execution is the recommended default mode
- For deterministic results, configure tool versions in the hub workflow or in a lockfile

---

## Hub: Security & Supply Chain

**File:** `.github/workflows/hub-security.yml`

Runs security scanning across repos. Intended for periodic checks and higher cost scans like CodeQL and optional DAST.

### Triggers
- `workflow_dispatch` (manual)
- `schedule` (weekly)

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `repos` | string | Comma-separated repo names to scan. Empty means all repos. |
| `run_zap` | boolean | If true, run OWASP ZAP DAST scan (requires a running app or reachable endpoint). |

### Outputs and Artifacts
- `security-events` uploaded via CodeQL (SARIF)
- SBOM and vulnerability scan artifacts (where enabled)

### Notes
- Permissions are explicitly set to `contents: read` and `security-events: write`
- DAST typically requires environment setup. Keep it off by default.

---

## Hub: Orchestrator (Distributed Execution)

**File:** `.github/workflows/hub-orchestrator.yml`

Dispatches workflows inside target repos. This mode requires target repos to have a dispatchable workflow and requires elevated permissions or a token that can trigger actions in those repos.

### Triggers
- `workflow_dispatch` (manual)

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `force_all_tools` | boolean | Intended to force-enable all tools for every repo in the run (implementation depends on hub version). |
| `repos` | string | Comma-separated repo names to dispatch. Empty means all repos. |

### Outputs and Artifacts
- Dispatch events triggered in target repos, if permissions and `workflow_dispatch` are correctly configured
- A hub-side summary showing dispatch status per repo
- Dispatch metadata artifacts (`dispatch-<repo>.json`) containing repo, branch, workflow, run_id, and status
- Aggregated hub-report.json with per-repo status, conclusions, and rolled coverage/mutation (when artifacts exist)

### Notes
- Keep this workflow separate from central execution so it cannot break the "repos stay clean" promise
- If you want hub config toggles to control downstream runs, the orchestrator must pass computed inputs into the dispatch request
- Uses each repo's `default_branch` from config when dispatching (no hard-coded `main`)

### Known Gaps (TODO)
- [ ] Run ID capture is best-effort and not correlated to artifacts yet
- [~] Aggregation downloads `ci-report` artifact when present; vuln rollup still TBD
- [~] Hub-run fails on missing/failed dispatches; still best-effort for run-id lookup and artifact presence

---

## Hub: Config Validation

**File:** `.github/workflows/config-validate.yml`

Validates all hub repo configs against the JSON schema on config/schema/script changes or manual dispatch.

### Triggers
- `push` to config/**, schema/**, scripts/load_config.py, or the workflow itself
- `pull_request` touching those paths
- `workflow_dispatch`

### Steps (summary)
- Install dependencies (`pip install -e .`)
- Iterate `config/repos/*.yaml` and run `scripts/load_config.py --repo <name>` (schema validation)
- Validate defaults via load_config

---

## Smoke Test

**File:** `.github/workflows/smoke-test.yml`

Docs: see `docs/development/SMOKE_TEST.md` and `docs/development/SMOKE_TEST_REPOS.md`

Quick validation test using minimal Java and Python repos to verify hub functionality before release. Runs core tools only (heavy tools like mutation testing and OWASP disabled for speed).

### Triggers
- `workflow_dispatch` (manual)
- `pull_request` on smoke test config or workflow changes

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `skip_mutation` | boolean | Skip mutation testing for faster execution (default: true) |

### Outputs and Artifacts
- Per-language smoke test results with metrics
- Artifacts from both Java and Python test runs (7-day retention)
- Step summaries showing pass/fail status and core metrics
- Overall smoke test summary with validation status

### Notes
- Only runs against repos matching `config/repos/smoke-test-*.yaml`
- Requires at least 2 smoke test repos (Java + Python)
- Uses relaxed thresholds (50% coverage vs 70% default)
- Validates repository discovery, tool execution, artifact generation, and summary creation
- See [docs/development/SMOKE_TEST.md](../development/SMOKE_TEST.md) for detailed guide

---

## Reusable Workflow: Java CI Pipeline

**File:** `.github/workflows/java-ci.yml`

Reusable workflow that a repo can call via `workflow_call`. Useful for distributed execution and for repo-local pipelines that still want hub-standard checks.

### Triggers
- `workflow_call` (called from another workflow)

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `java_version` | string | JDK version for builds |
| `build_tool` | string | `maven` or `gradle` |
| `run_jacoco` | boolean | Enable JaCoCo coverage extraction |
| `run_checkstyle` | boolean | Enable Checkstyle |
| `run_spotbugs` | boolean | Enable SpotBugs |
| `run_pmd` | boolean | Enable PMD |
| `run_owasp` | boolean | Enable OWASP Dependency-Check |
| `run_pitest` | boolean | Enable PITest mutation testing |
| `run_codeql` | boolean | Enable CodeQL analysis |
| `run_docker` | boolean | Enable Docker build and health checks |
| `coverage_min` | number | Coverage minimum (warn or fail, depending on policy) |
| `mutation_score_min` | number | Mutation score minimum (warn or fail) |
| `owasp_cvss_fail` | number | Fail threshold for CVSS scores |
| `retention_days` | number | Artifact retention period |

### Outputs and Artifacts
- Artifacts: test reports, coverage reports, and tool-specific outputs
- Job outputs: `build_status`, `coverage`, `mutation_score`

### Notes
- Some tools require Maven or Gradle plugins configured in the repo (especially JaCoCo and PITest)

---

## Reusable Workflow: Python CI Pipeline

**File:** `.github/workflows/python-ci.yml`

Reusable workflow that a repo can call via `workflow_call`. Runs lint, tests with coverage, and dependency scanning.

### Triggers
- `workflow_call` (called from another workflow)

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `python_version` | string | Python version to use |
| `run_pytest` | boolean | Enable pytest and coverage report generation |
| `run_ruff` | boolean | Enable Ruff lint |
| `run_bandit` | boolean | Enable Bandit security scan |
| `run_pip_audit` | boolean | Enable pip-audit dependency scan |
| `run_mypy` | boolean | Enable mypy type checking |
| `run_codeql` | boolean | Enable CodeQL analysis |
| `coverage_min` | number | Coverage minimum (warn or fail) |
| `retention_days` | number | Artifact retention period |

### Outputs and Artifacts
- Artifacts: `coverage.xml`, `htmlcov/`, `bandit-report.json`, pip-audit output
- Job outputs: `build_status`, `coverage`

### Notes
- The workflow installs dependencies from `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` if present

---

## Dashboards and Output Data

The hub produces JSON intended for dashboards and for custom visualization.

| Artifact | Produced By | Contents |
|----------|-------------|----------|
| `reports/<repo>/report.json` | hub-run-all and reusable workflows | Per-repo metrics: tool outcomes, coverage, mutation, vulnerability counts |
| `reports/hub-report.json` | `aggregate_reports.py` (hub job) | Hub-wide summary: totals, pass/fail counts, timestamps |
| `dashboards/overview.json` | static file | Dashboard definition for an aggregated overview across repos |
| `dashboards/repo-detail.json` | static file | Dashboard definition for per-repo deep dive |

### Aggregation Notes
If you use distributed execution (dispatching workflows in other repos), aggregation requires correlation and artifact collection:
- Prefer reusable workflows (`workflow_call`) to keep results in the same run where possible
- If cross-repo dispatch is required, pass a `hub_correlation_id` input and require child workflows to upload artifacts containing that id
- Poll the GitHub Actions API for run completion and download artifacts before aggregating

## Gating and run groups
- Tool execution is driven by config run_* flags.
- Use run_group (full/fixtures/smoke/...) to filter hub runs.
- Central mode: hub-run-all merges defaults + config/repos + repo-local .ci-hub.yml.
- Dispatch mode (current): hub config is the source of truth; repo-local .ci-hub.yml is ignored unless we later add a safe checkout+merge path.
