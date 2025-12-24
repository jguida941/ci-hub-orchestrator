# Workflows Reference

> Verified against `.github/workflows/*.yml`. Update this doc when workflow triggers or inputs change.

**Templates & Profiles:** For ready-made repo configs and tool profiles, see `templates/README.md` (apply via `python scripts/apply_profile.py ...`).

---

## Hub: Run All Repos (Central Execution)

**File:** `.github/workflows/hub-run-all.yml`

Clones each configured repository and runs build, tests, and quality tools in the hub run. This is the primary workflow for the "repos stay clean" design.

### Triggers
- `workflow_dispatch` (manual)
- `schedule` (daily at 02:00 UTC)
- `push` to main/master on `config/**` or `.github/workflows/hub-orchestrator.yml` changes
- `schedule` (daily at 02:00 UTC)
- `push` to main/master when `config/repos/*.yaml` changes

### Inputs

| Input | Type | Meaning |
|-------|------|---------|
| `repos` | string | Comma-separated repo names to run. Empty means all repos in `config/repos/`. |
| `run_group` | string | Filter by run group (`full`, `fixtures`, `smoke`, or comma-separated). |
| `skip_mutation` | boolean | If true, skip mutation testing steps for faster execution. |

### Outputs and Artifacts
- Per-repo artifacts such as test reports and coverage reports
- GitHub Step Summary with a per-repo metrics table (coverage, mutation, lint, security counts where applicable)
- Per-repo JSON report under `reports/<config_basename>/report.json` (used by aggregation)
- Per-repo summary snapshot under `reports/<config_basename>/summary.md`

### Notes
- Central execution is the recommended default mode
- For deterministic results, configure tool versions in the hub workflow or in a lockfile

---

## Hub: Security & Supply Chain

**File:** `.github/workflows/hub-security.yml`

Runs security scanning across repos. Intended for periodic checks and higher cost scans like CodeQL and optional DAST.

### Triggers
- `workflow_dispatch` (manual)
- `schedule` (weekly, Sunday 03:00 UTC)

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
- Repo-level override `repo.force_all_tools: true` (in config) force-enables all tools for that repo; default is `false`.

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
- Install dependencies from `requirements-dev.txt` or `requirements.txt` (fallback to `pyyaml` + `jsonschema`)
- Iterate `config/repos/*.yaml` and run `scripts/load_config.py --repo <name> --output workflow-inputs` (schema validation)
- Validate defaults via `scripts/load_config.py --repo dummy --hub-root . --output workflow-inputs`

---

## Hub: Self-Check

**File:** `.github/workflows/hub-self-check.yml`

Validates hub scripts, tests, templates, and config integrity.

### Triggers
- `push` to main/master on `scripts/**`, `tests/**`, `templates/**`, `config/**`, `schema/**`, `pyproject.toml`, `requirements*.txt`, or the workflow file
- `pull_request` touching the same paths
- `workflow_dispatch`

### Steps (summary)
- Python syntax check (`scripts/*.py`)
- Unit tests (`pytest tests/`)
- Template validation (`tests/test_templates.py`)
- Config validation (schema + defaults)
- Matrix key verification
- Combined summary

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

## Kyverno: Validate Policies (Internal)

**File:** `.github/workflows/kyverno-validate.yml`

Validates Kyverno policy and template syntax for the hub repository. For external repos, use the reusable `kyverno-ci.yml` workflow.

### Triggers
- `push`/`pull_request` on `policies/kyverno/**` or `templates/kyverno/**`
- `workflow_dispatch`

### Outputs
- Step summary with validated counts and failures

---

## Release

**File:** `.github/workflows/release.yml`

Creates GitHub releases and updates floating major tags (e.g., `v1`).

### Triggers
- `push` to tags matching `v*.*.*`

### Steps (summary)
- Validate reusable workflows with actionlint
- Run tests
- Create a GitHub Release with notes
- Update floating major tag

---

## Reusable Workflow: Java CI Pipeline

**File:** `.github/workflows/java-ci.yml`

Reusable workflow that a repo can call via `workflow_call`. Useful for distributed execution and for repo-local pipelines that still want hub-standard checks.

### Triggers
- `workflow_call` (called from another workflow)

### Inputs
See [CONFIG_REFERENCE.md](../reference/CONFIG_REFERENCE.md) for the full config field list, and `.github/workflows/java-ci.yml` for the authoritative workflow inputs. Categories include:

- Environment: `java_version`, `build_tool`, `workdir`, `artifact_prefix`, `retention_days`
- Tool flags: `run_*` (jacoco, checkstyle, spotbugs, owasp, pitest, jqwik, pmd, semgrep, trivy, codeql, docker)
- Thresholds: `coverage_min`, `mutation_score_min`, `owasp_cvss_fail`, `max_*` (vulns, checkstyle errors, spotbugs bugs, pmd violations, semgrep findings)
- Docker: `run_docker`, `docker_compose_file`, `docker_health_endpoint`

### Outputs and Artifacts
- Artifacts: test reports, coverage reports, and tool-specific outputs
- Job outputs: `build_status`, `coverage`, `mutation_score`

### Notes
- Some tools require Maven or Gradle plugins configured in the repo (especially JaCoCo and PITest)
- **Docker testing**: `run_docker`, `docker_compose_file`, `docker_health_endpoint` are available in the reusable workflow but removed from caller templates (GitHub's 25 input limit). Separate `hub-*-docker.yml` templates planned for Docker integration testing.

---

## Reusable Workflow: Python CI Pipeline

**File:** `.github/workflows/python-ci.yml`

Reusable workflow that a repo can call via `workflow_call`. Runs lint, tests with coverage, and dependency scanning.

### Triggers
- `workflow_call` (called from another workflow)

### Inputs
See [CONFIG_REFERENCE.md](../reference/CONFIG_REFERENCE.md) for the full config field list, and `.github/workflows/python-ci.yml` for the authoritative workflow inputs. Categories include:

- Environment: `python_version`, `workdir`, `artifact_prefix`, `retention_days`
- Tool flags: `run_*` (pytest, mutmut, hypothesis, ruff, black, isort, mypy, bandit, pip_audit, semgrep, trivy, codeql, docker)
- Thresholds: `coverage_min`, `mutation_score_min`, `max_*` (vulns, ruff errors, black issues, isort issues, semgrep findings)

### Outputs and Artifacts
- Artifacts: `coverage.xml`, `htmlcov/`, `test-results.xml`, `ruff-report.json`, `black-output.txt`, `isort-output.txt`, `mypy-output.txt`, `bandit-report.json`, `pip-audit-report.json`, `mutmut-run.log`, `hypothesis-output.txt` (plus `semgrep-report.json` and `trivy-report.json` when enabled)
- Job outputs: `build_status`, `coverage`

### Notes
- The workflow installs dependencies from `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` if present

---

## Dashboards and Output Data

The hub produces JSON intended for dashboards and for custom visualization.

| Artifact | Produced By | Contents |
|----------|-------------|----------|
| `reports/<config_basename>/report.json` | hub-run-all and reusable workflows | Per-repo metrics: tool outcomes, coverage, mutation, vulnerability counts |
| `reports/<config_basename>/summary.md` | hub-run-all | Per-repo summary snapshot used for validation |
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
- Central mode: hub-run-all currently uses defaults + config/repos (repo-local merge planned).
- Dispatch mode: hub config is merged with repo-local `.ci-hub.yml` (repo wins).
