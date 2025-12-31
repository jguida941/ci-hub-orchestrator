# AGENTS.md - CI/CD Hub

## Project Overview

CI/CD Hub is a CLI tool and workflow wrapper for running CI across many repos. The CLI is the execution engine; workflows are thin wrappers.

## Source of Truth Hierarchy

1. **Code** (`cihub/`, `.github/workflows/`) overrides docs on conflicts.
2. **CLI --help** is authoritative CLI documentation.
3. **Schema** (`schema/ci-hub-config.schema.json`) is the config contract.
4. **Plan** (`docs/development/PLAN.md`) is the canonical execution plan.

## Commands

- Test: `make test`
- Lint: `make lint`
- Format: `make format`
- Typecheck: `make typecheck`
- Workflow lint: `make actionlint`
- Generate docs: `python -m cihub docs generate`
- Check docs drift: `python -m cihub docs check`
- Smoke test: `python -m cihub smoke --full`
- Local check (fast): `python -m cihub check`
- Local check (full): `python -m cihub check --full`
- Local check (all): `python -m cihub check --all`
- Template sync (check): `python -m cihub sync-templates --check`
- Repo init: `python -m cihub init`
- Detect language: `python -m cihub detect`
- Config tooling: `python -m cihub config ...`
- Single tool run: `python -m cihub run <tool>`
- Report aggregation: `python -m cihub report ...`

### Check Tiers

```
cihub check              # Fast: lint, format, type, test, actionlint, docs, smoke (~30s)
cihub check --audit      # + links, adr, configs (~45s)
cihub check --security   # + bandit, pip-audit, trivy, gitleaks (~2min)
cihub check --full       # + templates, matrix, license, zizmor (~3min)
cihub check --mutation   # + mutmut (~15min)
cihub check --all        # Everything
```

## Testing Notes

- Run `pytest tests/` for CLI and config changes.
- After CLI or schema changes, regenerate reference docs.
- Use `cihub scaffold` + `cihub smoke` for local verification.

## Required After Changes

- CLI or schema changes: `python -m cihub docs generate` and `python -m cihub docs check`.
- Template callers or hub workflow changes: `python -m cihub sync-templates --check` (requires GH auth) and `pytest tests/test_templates.py`.
- Local validation before push: `python -m cihub check --all`.

## Project Structure

- `cihub/` — CLI source and command handlers
- `config/` — Defaults and repo configs
- `schema/` — JSON schema for .ci-hub.yml
- `templates/` — Workflow/templates and scaffold assets
- `templates/legacy/` — Archived dispatch templates (do not use)
- `docs/` — Documentation hierarchy
- `tests/` — pytest suite
- `.github/workflows/` — CI workflows

## Documentation Rules

- Do not duplicate CLI help text in markdown. Generate reference docs from the CLI.
- Do not hand-write config field docs. Generate from schema.
- If code and docs conflict, update docs to match code.

## Scope Rules

### Always

- Update `docs/development/PLAN.md` checkboxes when scope changes.
- Update `docs/development/CHANGELOG.md` for user-facing changes.
- Regenerate docs after CLI or schema changes.

### Ask First

- Modifying `.github/workflows/`.
- Changing `schema/` or `config/repos/`.
- Archiving/moving docs or ADRs.
- Changing CLI command surface or defaults.

### Never

- Delete docs (archive instead).
- Commit secrets or credentials.
- Change workflow pins without explicit approval.

### CI Parity Rule

- If `hub-production-ci.yml` fails on something that can be reproduced locally, add it to `cihub check` or document why it's CI-only.
- Run `cihub check --all` before pushing to catch issues early.

### CI Parity Map

**Categories:**
- **Exact**: Same tool, same flags, same behavior
- **Partial**: Same tool, different flags/scope
- **CI-only**: Only runs in CI (requires GitHub context)
- **Local-only**: Only runs locally (not in CI workflow)

#### Exact Match
| Check | Local | CI | Notes |
|-------|-------|-----|-------|
| validate-configs | `cihub hub-ci validate-configs` | `cihub hub-ci validate-configs` | Same command |
| validate-profiles | `cihub hub-ci validate-profiles` | `cihub hub-ci validate-profiles` | Same command |
| validate-templates | `pytest tests/test_templates.py -v --tb=short` | Same | Same test |
| verify-matrix-keys | `python scripts/verify_hub_matrix_keys.py` | Same | Same script |
| license-check | `cihub hub-ci license-check` | `cihub hub-ci license-check` | Same command |

#### Partial Match
| Check | Local | CI | Difference |
|-------|-------|-----|------------|
| ruff lint | `ruff check .` | `cihub hub-ci ruff --path . --force-exclude` | CI adds force-exclude + GitHub output |
| ruff format | `ruff format --check .` | `ruff format --check . --force-exclude` | Flag differs |
| mypy | `mypy cihub/ scripts/` | `mypy cihub/ --ignore-missing-imports --show-error-codes` | Scope/flags differ |
| pytest | `pytest tests/` | `pytest --cov --cov-fail-under=70` | Coverage gate only in CI |
| actionlint | All workflows | Only `hub-production-ci.yml` + reviewdog | Scope/annotations differ |
| yamllint | `config/ templates/` | Specific paths + custom rules | Paths/rules differ |
| bandit | `bandit -r cihub scripts -f json -q` | `cihub hub-ci bandit --paths cihub scripts --output ...` | Flags/output differ |
| pip-audit | `pip-audit -r ...` | `cihub hub-ci pip-audit --format json --output ...` | Format/output differ |
| gitleaks | `gitleaks detect --no-git` (skip if missing) | GitHub Action with history | No history locally |
| trivy | `trivy fs .` | FS + config scans | CI has more scans |
| zizmor | `zizmor .github/workflows/` | SARIF + `cihub hub-ci zizmor-check` | Output format differs |
| mutmut | `cihub hub-ci mutmut --min-score 70` | `cihub hub-ci mutmut --min-score 70 --output-dir . --github-output --github-summary` | Output/summary differ |

#### CI-Only (Requires GitHub Context)
| Step | Why |
|------|-----|
| SARIF upload | GitHub Security API |
| Reviewdog | PR comments |
| dependency-review | GitHub dependency graph |
| OpenSSF Scorecard | GitHub repo context |
| harden-runner | GitHub Action |
| badge updates | GitHub token |
| GH Step Summary | `$GITHUB_STEP_SUMMARY` |
| hub-ci summary/enforce | Requires CI result env vars |

#### Local-Only (Not in CI)
| Step | Purpose |
|------|---------|
| docs-check | Drift detection for CLI.md/CONFIG.md |
| docs-links | Broken link checking (lychee) |
| adr-check | ADR validation |
| preflight | Environment setup checks |
| smoke | Scaffold + validate test |

## Key Architecture

- Entry point workflow is `hub-ci.yml` (wrapper that routes to language-specific workflows).
- Fixtures repo is CI/regression only; local dev uses `cihub scaffold` + `cihub smoke`.
- Generated refs: `docs/reference/CLI.md` and `docs/reference/CONFIG.md` (don't edit by hand).

## Key Files

- `cihub/cli.py` (CLI commands)
- `schema/ci-hub-config.schema.json` (config contract)
- `config/defaults.yaml` (defaults)
- `docs/development/PLAN.md` (active plan)
