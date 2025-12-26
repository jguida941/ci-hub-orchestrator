# Integration Smoke Test Guide

## Purpose

Validate the CLI and config pipeline against fixture repos using the same
boolean toggles and templates used in production.

## Prerequisites

- Local clone of `hub-release`
- Local clone of `ci-cd-hub-fixtures`
- Python 3.11+ with dependencies installed

```bash
python -m pip install -e ".[dev]"
```

## Fixture Coverage

See `docs/development/execution/SMOKE_TEST.md` for the fixture matrix and subdir list.

## CLI Integration Runner (Recommended)

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

## Manual CLI Walkthrough (One Fixture)

Example for `java-maven-pass`:

```bash
FIXTURES=/path/to/ci-cd-hub-fixtures
WORKDIR=$(mktemp -d)
cp -R "$FIXTURES" "$WORKDIR/java-maven-pass"
cd "$WORKDIR/java-maven-pass"

# Detect language from fixture subdir
python -m cihub detect --repo "$WORKDIR/java-maven-pass/java-maven-pass"

# Initialize config (subdir-aware)
python -m cihub init \
  --repo "$WORKDIR/java-maven-pass" \
  --language java \
  --owner fixtures \
  --name java-maven-pass \
  --branch main \
  --subdir java-maven-pass \
  --apply

# Update config/workflow
python -m cihub update \
  --repo "$WORKDIR/java-maven-pass" \
  --language java \
  --owner fixtures \
  --name java-maven-pass \
  --branch main \
  --subdir java-maven-pass \
  --apply \
  --force

# Validate config
python -m cihub validate --repo "$WORKDIR/java-maven-pass"
```

## Expected Outputs

- `.ci-hub.yml` exists in the repo root with:
  - `repo.subdir` set to the fixture subdir
  - `repo.language` set correctly
- `.github/workflows/hub-ci.yml` exists and matches the template
- `cihub validate` returns exit code 0 for valid config schema (both pass and fail fixtures should pass config validation)

> **Note:** `cihub validate` only checks config schema and structure. It does NOT run tests or linters. "Fail fixtures" are designed to fail at **runtime** (failing tests, lint violations, security findings), not at config validation. To verify fail behavior, run the workflow in GitHub Actions.

## Distributed Mode (Caller Workflow)

If you want to validate repo-side execution:

1. Run `cihub init --apply` or `cihub update --apply --force` against the fixture.
2. Confirm `.github/workflows/hub-ci.yml` was generated.
3. Trigger the workflow in the fixture repo (GitHub Actions UI) and verify tool
   outputs and artifacts match `docs/reference/TOOLS.md`.
