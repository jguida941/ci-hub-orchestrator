# Integration Smoke Test Guide

## Purpose

Validate the CLI and config pipeline end-to-end using fixtures and (optionally)
GitHub Actions. This guide is designed for step-by-step verification with
checkpoints after each step.

## How to Use This Guide

- Run one step at a time.
- Compare results to the "Expected" section for that step.
- If anything is off, stop and capture the output so we can review together.

## How the CLI Works (Mental Model)

- **Config precedence:** `config/defaults.yaml` → `config/repos/<repo>.yaml` → repo
  `.ci-hub.yml` (repo wins).
- **Repo-side setup:** `cihub init/update` generate `.ci-hub.yml` and the caller
  workflow `.github/workflows/hub-ci.yml`.
- **Distributed mode:** caller workflow runs `hub-ci.yml` in this repo, which
  installs `cihub`, reads `.ci-hub.yml` via `config-outputs`, then routes to
  `python-ci.yml` or `java-ci.yml`.
- **Central mode:** hub runs tools directly (`hub-run-all.yml`) using hub configs.
- **Local CI:** `cihub ci` runs all enabled tools and writes `.cihub/report.json`
  + `.cihub/summary.md`. `cihub run <tool>` emits a single tool JSON output that
  `cihub report build` can consume later.

## CLI Command Map (Source of Truth: `--help`)

Use `python -m cihub --help` and `python -m cihub <command> --help` for the full
option list. This guide provides tested examples for every command.

## Command Coverage Checklist

Use this table to verify every CLI command has a tested example.

| Command | Where in this guide |
| --- | --- |
| `detect` | Step 2 |
| `init` | Step 3 |
| `update` | Step 4 |
| `validate` | Step 5, Step 13 |
| `fix-pom` | Step 6 (Java Maven only) |
| `fix-deps` | Step 6b (Java Maven only) |
| `ci` | Step 7 |
| `run` | Step 8 (Python-only tools) |
| `report build` | Step 9 |
| `report summary` | Step 10 |
| `report outputs` | Step 11 |
| `config-outputs` | Step 12 |
| `new` | Hub-side: Create a New Repo Config |
| `config show/set/enable/disable/edit` | Hub-side: Show or Update / Edit |
| `sync-templates` | Hub-side: Sync Caller Templates |
| `setup-secrets` | Secrets Setup |
| `setup-nvd` | Secrets Setup |
| `hub-ci *` | Hub Production CI Helpers |

## Prerequisites

- Local clone of `hub-release`
- Local clone of `ci-cd-hub-fixtures`
- Python 3.11+ with dependencies installed

```bash
python -m pip install -e ".[dev]"

# Optional: install CI tool runners (needed for `cihub ci` / `cihub run`)
python -m pip install -e ".[ci]"

# Optional: install wizard deps (needed for `cihub config edit`)
python -m pip install -e ".[wizard]"
```

## Fixture Coverage

See `docs/development/execution/SMOKE_TEST.md` for the full fixture matrix and
subdir list.

## Quick Smoke Matrix (Minimum)

| Case | Fixture | Notes |
| --- | --- | --- |
| Python (pyproject) | `python-pyproject-pass` | Base config + workflow generation |
| Python (requirements) | `python-reqs-pass` | Legacy dependency layout |
| Java (maven) | `java-maven-pass` | POM fixes + dependency add |
| Java (gradle) | `java-gradle-pass` | No POM fixes expected |
| Monorepo | `java-maven-pass` + `--subdir` | Subdir handling |

## Repo Archetype Walkthroughs (Differences vs Base Flow)

Use the Step-by-Step Smoke section as the base, then apply the notes below.

### Python (pyproject)

- Use Steps 1-5 with `--language python`.
- Step 7 should include `--install-deps` to install `pyproject.toml` deps.
- Step 8 (`cihub run`) supports Python tools only; use `ruff`, `pytest`, etc.

### Python (requirements.txt)

- Use Steps 1-5 with `--language python`.
- Ensure `requirements.txt` (and optional `requirements-dev.txt`) exist.
- Step 7 should include `--install-deps`.

### Java (Maven)

- Use Steps 1-6 with `--language java`.
- Step 6/6b apply (plugins + dependencies). Requires `mvn` or `./mvnw`.
- Step 7 runs Maven-based tooling.

### Java (Gradle)

- Use Steps 1-5 with `--language java` and set `java.build_tool: gradle`.
- Skip Step 6/6b (POM fixes are Maven-only).
- Step 7 runs Gradle tooling (requires `gradle` or `./gradlew`).

### Monorepo (subdir)

- Always pass `--subdir <path>` to `init/update`, or set `repo.subdir`.
- Validate that `.ci-hub.yml` includes `repo.subdir`.
- `cihub ci` should use `--workdir` if you want to override subdir at runtime.

## Multi-Repo Smoke (Local, No GitHub)

Use this to validate multiple fixtures in one pass. This is the fastest way to
catch regressions across languages.

```bash
FIXTURES=/path/to/ci-cd-hub-fixtures
JAVA_CASES=(java-maven-pass java-gradle-pass java-multi-module-pass)
PY_CASES=(python-pyproject-pass python-setup-pass python-src-layout-pass)

for case in "${JAVA_CASES[@]}"; do
  WORKDIR=$(mktemp -d)
  cp -R "$FIXTURES" "$WORKDIR/$case"
  python -m cihub init \
    --repo "$WORKDIR/$case" \
    --language java \
    --owner fixtures \
    --name "$case" \
    --branch main \
    --subdir "$case" \
    --apply
  python -m cihub validate --repo "$WORKDIR/$case"
done

for case in "${PY_CASES[@]}"; do
  WORKDIR=$(mktemp -d)
  cp -R "$FIXTURES" "$WORKDIR/$case"
  python -m cihub init \
    --repo "$WORKDIR/$case" \
    --language python \
    --owner fixtures \
    --name "$case" \
    --branch main \
    --subdir "$case" \
    --apply
  python -m cihub validate --repo "$WORKDIR/$case"
done
```

Expected:
- Each fixture gets a valid `.ci-hub.yml` + `hub-ci.yml`
- `cihub validate` reports `Config OK`

## Step-by-Step Smoke (Local Fixtures)

Use one fixture at a time and verify each checkpoint before continuing.

### Step 1: Prepare a Fixture Workspace

```bash
FIXTURES=/path/to/ci-cd-hub-fixtures
WORKDIR=$(mktemp -d)
cp -R "$FIXTURES" "$WORKDIR/java-maven-pass"
cd "$WORKDIR/java-maven-pass"
```

Expected:
- Workspace exists under `$WORKDIR`
- Fixture subdir (e.g. `java-maven-pass/`) is intact

### Step 2: Detect Language

```bash
python -m cihub detect --repo "$WORKDIR/java-maven-pass/java-maven-pass"
```

Expected:
- Output shows `java`

### Step 3: Init (Generate .ci-hub.yml + hub-ci.yml)

```bash
python -m cihub init \
  --repo "$WORKDIR/java-maven-pass" \
  --language java \
  --owner fixtures \
  --name java-maven-pass \
  --branch main \
  --subdir java-maven-pass \
  --apply
```

Expected:
- `.ci-hub.yml` exists and contains `language: java`
- `.github/workflows/hub-ci.yml` exists

### Step 4: Update (Idempotent Refresh)

```bash
python -m cihub update \
  --repo "$WORKDIR/java-maven-pass" \
  --language java \
  --owner fixtures \
  --name java-maven-pass \
  --branch main \
  --subdir java-maven-pass \
  --apply \
  --force
```

Expected:
- Command succeeds (exit code 0)
- Files remain valid and updated

### Step 5: Validate Config

```bash
python -m cihub validate --repo "$WORKDIR/java-maven-pass"
```

Expected:
- `Config OK`

Note: `cihub validate` checks schema and structure only; it does not run tests.

### Step 6: Java-Only POM Fixes

```bash
python -m cihub fix-pom --repo "$WORKDIR/java-maven-pass" --apply
```

Expected:
- Missing Maven plugins are added to the parent POM
- If `jqwik` is enabled, `<artifactId>jqwik</artifactId>` is added

### Step 6b: Java-Only Dependency Fixes (Optional)

```bash
python -m cihub fix-deps --repo "$WORKDIR/java-maven-pass" --apply
```

Expected:
- Missing Java dependencies (e.g., jqwik) are added to module POMs

### Step 7: Run CI Locally (Full Pipeline)

```bash
python -m cihub ci --repo "$WORKDIR/java-maven-pass" --output-dir .cihub
```

Expected:
- `.cihub/report.json` and `.cihub/summary.md` are created
- Nonzero exit if quality gates fail

Note: For Python repos, add `--install-deps` to install repo dependencies.

### Step 8: Run a Single Tool (Python Only)

```bash
python -m cihub run ruff --repo "$WORKDIR/python-pyproject-pass" --output-dir .cihub
```

Expected:
- `.cihub/tool-outputs/ruff.json` exists
- Command exits nonzero if the tool fails

Note: `cihub run` currently supports Python tools only (pytest, ruff, black,
isort, mypy, bandit, pip-audit, mutmut, semgrep, trivy).

### Step 9: Build Reports From Tool Outputs

```bash
python -m cihub report build --repo "$WORKDIR/python-pyproject-pass" --output-dir .cihub
```

Expected:
- `.cihub/report.json` and `.cihub/summary.md` are created

### Step 10: Render Summary From Report

```bash
python -m cihub report summary --report "$WORKDIR/python-pyproject-pass/.cihub/report.json"
```

Expected:
- Summary printed to stdout (or use `--output` to write a file)

### Step 11: Emit Report Outputs (Workflow Outputs)

```bash
python -m cihub report outputs \
  --report "$WORKDIR/python-pyproject-pass/.cihub/report.json" \
  --output "$WORKDIR/python-pyproject-pass/.cihub/report.outputs"
```

Expected:
- Output file contains `build_status`, `coverage`, `mutation_score`

### Step 12: Emit Config Outputs (Workflow Inputs)

```bash
python -m cihub config-outputs --repo "$WORKDIR/python-pyproject-pass"
```

Expected:
- Prints `run_*` flags and thresholds for GitHub Actions inputs

### Step 13: JSON Contract Spot-Check

```bash
python -m cihub validate --repo "$WORKDIR/java-maven-pass" --json
```

Expected:
- JSON includes `exit_code`, `summary`, and `problems` (may be empty)

Repeat Steps 1-6 for each fixture in the smoke matrix. Use Steps 7-13 on the
fixtures you want to validate for CI execution and report generation.

## CLI Integration Runner (Optional)

Run all fixtures via the scripted runner. It copies the fixtures repo into a
temporary directory per case so the source repo is untouched.

```bash
python scripts/run_cli_integration.py \
  --fixtures-path /path/to/ci-cd-hub-fixtures
```

Run a subset:

```bash
python scripts/run_cli_integration.py \
  --fixtures-path /path/to/ci-cd-hub-fixtures \
  --only java-maven-pass \
  --only python-pyproject-pass
```

## Distributed Mode (GitHub Smoke Repo)

Use this when you want to validate the caller workflow and reusable workflow in
real Actions.

1. Create a repo (public or private).
2. Run `cihub init --apply` in that repo.
3. Set repo variables `HUB_REPO` and `HUB_REF` to point at the hub repo/ref.
4. Push and run the workflow from GitHub Actions.

Expected:
- `Parse Config` job succeeds
- Language-specific job runs and uploads artifacts
- `report.json` and summary are generated

## Multi-Repo GitHub Setup (Distributed)

Use this to validate the full hub workflow across multiple repos.

1. Create 3 repos (one Python, one Java, one monorepo).
2. In each repo, run `cihub init --apply` to generate `.ci-hub.yml` + `hub-ci.yml`.
3. In the hub repo, add `config/repos/*.yaml` entries for each.
4. Run template sync:
   ```bash
   python -m cihub sync-templates --check --dry-run --no-update-tag
   ```
5. Set secrets and variables:
   - Repo variables: `HUB_REPO`, `HUB_REF`
   - Secrets: `HUB_DISPATCH_TOKEN`, `NVD_API_KEY` (Java)
6. Trigger `Hub Orchestrator` or run repo workflows directly.

Expected:
- All repos show successful runs in GitHub Actions
- Artifacts include `report.json` and summaries per repo

## Hub-Side Repo Management (Hub Repo Only)

Use these commands in the `hub-release` repo to manage `config/repos/*.yaml`.

### Create a New Repo Config

```bash
python -m cihub new my-repo --owner jguida941 --language python --branch main --yes
```

Expected:
- `config/repos/my-repo.yaml` is created

### Show or Update a Repo Config

```bash
python -m cihub config --repo my-repo show
python -m cihub config --repo my-repo show --effective
python -m cihub config --repo my-repo set python.tools.pytest.min_coverage 80
python -m cihub config --repo my-repo enable ruff
python -m cihub config --repo my-repo disable bandit
```

Expected:
- Config prints or updates successfully

### Edit a Repo Config (Wizard)

```bash
python -m cihub config --repo my-repo edit
```

Expected:
- Wizard opens (requires `cihub[wizard]`)

### Sync Caller Templates

```bash
python -m cihub sync-templates --check --dry-run --no-update-tag
```

Expected:
- Prints drift status without writing

Note: `sync-templates` requires `gh` auth and network access.

## Secrets Setup (GitHub Required)

These commands require `gh` auth and a PAT.

```bash
python -m cihub setup-secrets --hub-repo jguida941/ci-cd-hub --verify
python -m cihub setup-secrets --hub-repo jguida941/ci-cd-hub --all --verify
python -m cihub setup-nvd --verify
```

Expected:
- Secrets are set via `gh secret set`
- `--verify` confirms PAT/NVD key validity

## Hub Production CI Helpers (Hub Repo Only)

These helpers are designed for `.github/workflows/hub-production-ci.yml`.
Some rely on env vars set by the workflow.

```bash
python -m cihub hub-ci validate-configs
python -m cihub hub-ci validate-profiles
python -m cihub hub-ci ruff --path .
python -m cihub hub-ci black --path .
python -m cihub hub-ci bandit --paths cihub scripts
python -m cihub hub-ci pip-audit
python -m cihub hub-ci mutmut --workdir . --output-dir .cihub/mutmut
python -m cihub hub-ci zizmor-check --sarif zizmor.sarif
python -m cihub hub-ci license-check
python -m cihub hub-ci gitleaks-summary --outcome success
python -m cihub hub-ci summary
python -m cihub hub-ci enforce
```

Expected:
- Local helpers run or emit summaries; `summary/enforce` are most useful inside CI

## What to Capture for Review

- CLI output for any failed step
- The generated `.ci-hub.yml` and `.github/workflows/hub-ci.yml`
- JSON output when using `--json`
- GitHub Actions run URL (if testing distributed mode)
