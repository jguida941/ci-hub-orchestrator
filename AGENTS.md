# AGENTS.md - CI/CD Hub Release

AI agent context for the hub-release project.
**Last Updated:** 2025-12-26
**Developer:** Justin Guida


**Primary docs:**<br>
Status: `docs/development/status/STATUS.md`, <br>
Technical Details: `docs/development/architecture/ARCHITECTURE_PLAN.md`

## Project Context

You are working on **hub-release**, a production CI/CD hub that includes:
- Central and distributed GitHub Actions workflows
- Reusable workflows + caller templates
- Config/schema + profiles + validation scripts
- CLI (`cihub`) + wizard + diagnostics
- Aggregation/reporting + dashboard outputs
- Fixtures + smoke/integration testing
- Security/compliance tooling (scorecard, zizmor, pip-audit)
- Docs/ADRs that define system behavior

## Product Intent

This is a production-grade system intended for commercial use. Prioritize safety, scalability, maintainability, SDLC best practices, and thorough testing (including mutation testing when practical). Do not cut corners for speed.

## Source of Truth and Drift Policy

- Repo-level workflow files are generated caller stubs and must not be edited to change tool toggles or inputs.
- Per-repo customization must be done via config hierarchy only: `.ci-hub.yml` (repo) → `config/repos/<repo>.yaml` → `config/defaults.yaml`.
- If repo caller workflows need updates, regenerate them via `python -m cihub sync-templates` instead of editing repo workflows directly.

## ADR Governance (required)

- Major architectural decisions require an ADR (new or updated) before implementation.
- When editing an ADR, add a `Last Reviewed: YYYY-MM-DD` line near the top.
- Audit ADRs on milestone boundaries or when a change touches their domain; avoid daily churn.
- If an ADR is superseded, mark it clearly with the replacement ADR and date.

## Legacy Archive Docs (read-only)

- `docs/development/archive/audit.md` and `docs/development/archive/OUTSTANDING.md` are legacy snapshots.
- These files are retained for historical context only and must not be used as current guidance.

## Project Overview

**hub-release** is a user-friendly CI/CD template repository that runs pipelines for Java and Python projects with boolean toggles for tools. Central execution is the default mode (hub clones repos and runs tests directly).

**Tech Stack:** GitHub Actions, Python 3.11+, YAML configs, Pydantic validation

**Key Principle:** Repos stay clean - target repos don't need workflow files.

## Commands

```bash
# Preferred: Makefile wrappers
make help
make lint
make format
make test
make typecheck
make actionlint
make sync-templates-check
make mutmut

# CLI (preferred)
python -m cihub validate --repo .
python -m cihub config --repo <repo> show --effective

# Validate configs
python scripts/validate_config.py config/repos/<repo>.yaml

# Apply a profile to a repo config (creates/merges)
python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/<repo>.yaml

# Load merged config for a repo
python scripts/load_config.py <repo-name>

# Run hub locally (requires act)
act -W .github/workflows/hub-run-all.yml

# Lint Python scripts
ruff check .
ruff format scripts/ --check

# Type check
mypy cihub/ scripts/

# Tests
pytest tests/

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/defaults.yaml'))"
```

## Caller/Template Sync (critical)

- Run `python -m cihub sync-templates --check` after changing `.github/workflows/java-ci.yml`, `.github/workflows/python-ci.yml`, or `templates/repo/hub-*.yml` to spot drift.
- Run `python -m cihub sync-templates` (or trigger `.github/workflows/sync-templates.yml`) to regenerate/push caller workflows; use `--repo owner/name` to scope when testing.
- Keep thresholds/tool inputs aligned by syncing whenever defaults or reusable workflow inputs change.
- PR checklist to avoid drift: (1) run `python -m cihub sync-templates --check`, (2) if there is drift, run `python -m cihub sync-templates --repo owner/name` to verify the fix, (3) if templates changed in the PR, ensure the sync-templates workflow ran or note that it must run after merge. The nightly `template-guard.yml` also checks drift but do not rely on it for PRs.

## Current Focus / Scope

- Target is v1.0 per `docs/development/status/STATUS.md`; current blockers are `hub-orchestrator` and `hub-security` failures—prioritize distributed mode stability and security workflow fixes.
- Thresholds live in config (`.ci-hub.yml` / repo config / defaults) with a single override input; keep dispatch inputs to booleans only (see ADR-0024, migration doc).
- When adding or changing workflow inputs, update reusable workflows, caller templates, docs (CONFIG_REFERENCE, ONBOARDING), and keep schema/contracts in sync to prevent drift.

## Project Structure

```
hub-release/
├── .github/workflows/     # GitHub Actions workflows
│   ├── hub-run-all.yml    # Central execution (DEFAULT)
│   ├── hub-orchestrator.yml  # Distributed execution
│   ├── hub-security.yml   # Security scanning
│   ├── java-ci.yml        # Reusable Java workflow
│   └── python-ci.yml      # Reusable Python workflow
├── config/
│   ├── defaults.yaml      # Global defaults (CRITICAL)
│   ├── repos/             # Per-repo overrides
│   └── optional/          # Optional feature configs
├── docs/
│   ├── guides/            # User guides (ONBOARDING, WORKFLOWS, etc.)
│   ├── reference/         # Reference docs (CONFIG_REFERENCE, TOOLS)
│   ├── development/       # Internal docs (architecture, status, execution, research, specs)
│   └── adr/               # Architecture Decision Records
├── templates/             # Copy-paste templates for users (see templates/README.md)
├── scripts/               # Python utilities
├── schema/                # JSON Schema definitions
└── cihub/                 # CLI tool package
```

## Key Files to Understand

| File | Purpose | Read First? |
|------|---------|-------------|
| `docs/README.md` | Documentation index | **YES** |
| `docs/development/status/STATUS.md` | Current status and checklists | **YES** |
| `docs/development/architecture/ARCHITECTURE_PLAN.md` | Technical implementation details | YES |
| `docs/development/specs/` | P0/P1/nonfunctional checklists | YES |
| `config/defaults.yaml` | Global config with all toggles | For config changes |
| `.github/workflows/hub-run-all.yml` | Central mode workflow | For workflow changes |
| `.github/workflows/python-ci.yml` | Reusable Python workflow | For distributed mode |
| `.github/workflows/java-ci.yml` | Reusable Java workflow | For distributed mode |
| `docs/development/research/RESEARCH_LOG.md` | Research and best practices | Reference |

## Config Hierarchy (Highest Wins)

```
1. Repo's .ci-hub.yml (if exists)  ← Highest priority
2. Hub's config/repos/<repo>.yaml
3. Hub's config/defaults.yaml      ← Lowest priority
```

## Code Style

**Python (scripts/):**
- Python 3.11+
- Ruff for linting and formatting
- Type hints required
- Docstrings for public functions

**YAML (config/, workflows/):**
- 2-space indent
- Comments above keys (not inline)
- Section headers with `# ====` separators
- Document available options in comments

**Markdown (docs/):**
- ATX headers (`#` not underlines)
- Tables for structured data
- Code blocks with language tags

## Testing

**~243 tests** across the suite in `tests/` (update counts as they change).

```bash
pytest tests/                    # Run all tests
pytest tests/ --cov=scripts      # With coverage
```

When adding tests:
- Use pytest for Python scripts
- Use fixture repos (`ci-cd-hub-fixtures`) for integration testing
- Test config loading, validation, and merging
- Mutation testing is required when practical (see ADR-0016)

## Git Workflow

**Branches:**
- `master` - Main branch
- `feature/<description>` - New features
- `fix/<description>` - Bug fixes
- `docs/<description>` - Documentation

**Commits:**
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Reference issues: `fix: resolve #123`

**Pull Requests:**
- Require description of changes
- Update relevant docs
- Test with at least one fixture repo

## Pre-Push Checklist (REQUIRED)

**Before every push, run these checks:**

```bash
# 1. Lint Python code
make lint                    # or: ruff check .

# 2. Type check
make typecheck               # or: mypy cihub/ scripts/

# 3. Run tests
make test                    # or: pytest tests/

# 4. Lint GitHub Actions workflows (CRITICAL)
make actionlint              # or: actionlint

# 5. Check template drift
make sync-templates-check    # or: python -m cihub sync-templates --check

# 6. Validate YAML configs
for f in config/repos/*.yaml; do python3 -c "import yaml; yaml.safe_load(open('$f'))"; done
```

**Quick one-liner:**
```bash
make lint && make typecheck && make test && make actionlint && make sync-templates-check
```

**Why this matters:**
- CI will fail if these checks fail
- Catching errors locally is faster than waiting for CI
- actionlint catches workflow syntax errors that break all CI jobs
- Template drift causes caller workflow mismatches

## Current Status (2025-12-26)

> **See:** `docs/development/status/STATUS.md` for full details

### What's Working ✅
- Central mode (`hub-run-all.yml`) - **PASSING**
- Reusable workflows (`python-ci.yml`, `java-ci.yml`, `kyverno-ci.yml`)
- Caller templates (`hub-python-ci.yml`, `hub-java-ci.yml`)
- CLI tool (`cihub`) v0.2.0 with 11 commands (plus subcommands)
- Tests: 240+ unit tests
- ADRs: 28 total
- Report schema 2.0
- Orchestrator input passthrough complete

### What's Broken ❌
- Hub Orchestrator workflow - **FAILING** (needs investigation)
- Hub Security workflow - **FAILING**
- Hub Production CI - **FAILING** (coverage gate, scorecard env, pip-audit, zizmor flags)

### Quick Status

| Part | Description | Status |
|------|-------------|--------|
| Part 1 | Reusable Workflows | ✅ Done |
| Part 2 | CLI Tool (`cihub`) | 🟡 Partial (v0.2.0) |
| Part 3 | Test Fixtures | 🟡 Partial (expanded matrix pending fixtures repo) |
| Part 4 | Aggregation | ✅ Done |
| Part 5 | Dashboard | 🟡 Partial (needs GH Pages) |
| Part 6 | Polish & Release | 🔴 Blocked (workflow failures) |

### Blockers for v1.0.0
1. Fix hub-orchestrator.yml failures
2. Fix hub-security.yml failures
3. Fix hub-production-ci.yml gates (coverage, scorecard, pip-audit, zizmor)

## MoSCoW Priorities

**Must Have (MVP):**
- Central execution for Java/Python
- Boolean toggles (`enabled: true/false`)
- Config hierarchy working
- Basic documentation

**Should Have:**
- Comprehensive docs for all tools
- Heavily commented templates
- ADRs for key decisions
- CLI tool for config management

**Could Have:**
- GitHub Pages dashboard
- Fixture repos for testing
- Distributed mode improvements

**Planned (post‑v1):**
- PyQt6 GUI wrapper (see `docs/development/architecture/ARCHITECTURE_PLAN.md`, Phase 9)
- Additional languages beyond Java/Python (planned, not in current scope)

## Boundaries

### Always OK (No Permission Needed)
- Read any file
- Edit files in `docs/`
- Edit files in `templates/`
- Run validation scripts
- Add new documentation
- Fix typos and formatting

### Ask First
- Modify `config/defaults.yaml` (affects all repos)
- Modify workflow files in `.github/workflows/`
- Add new Python dependencies
- Delete any file
- Change schema files
- Modify `STATUS.md`

### Never Do
- Commit secrets, tokens, or API keys
- Force push to master
- Remove or rename `config/defaults.yaml`
- Delete `docs/development/research/RESEARCH_LOG.md` or `docs/development/status/STATUS.md`
- Modify files outside `hub-release/` directory
- Create `.env` files with real credentials
- Push directly to master without review

## Tool Reference Quick Links

**Java Tools:** JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, CodeQL
**Python Tools:** pytest, Ruff, Black, Bandit, pip-audit, mypy, mutmut
**Universal:** Semgrep, Trivy, CodeQL

See `docs/development/research/RESEARCH_LOG.md` sections 9-12 for full tool details.

## Common Tasks

**Add a new repo:**
1. Create `config/repos/<repo>.yaml`
2. Set `repo.owner`, `repo.name`, `repo.language`
3. Override any tool toggles as needed
4. Validate: `python scripts/load_config.py <repo>`

**Toggle a tool:**
```yaml
# In config/repos/<repo>.yaml or config/defaults.yaml
python:
  tools:
    mypy:
      enabled: true  # or false
```

**Add documentation:**
1. Follow Diátaxis framework (Tutorial, How-To, Reference, Explanation)
2. Link from `docs/guides/ONBOARDING.md`
3. Update `docs/README.md` index if needed

## CLI Tool (`cihub`)

```bash
# Detect repo language
python -m cihub detect --repo .

# Initialize a new repo
python -m cihub init --repo . --language python

# Update existing config
python -m cihub update --repo .

# Validate config
python -m cihub validate --repo .

# Setup dispatch secrets (with verification)
python -m cihub setup-secrets --hub-repo jguida941/ci-cd-hub --verify

# Setup NVD API key for Java OWASP scans
python -m cihub setup-nvd --verify
```

**6 commands:** detect, init, update, validate, setup-secrets, setup-nvd

## Related Files

- `CLAUDE.md` - Points to this file for Claude Code compatibility
- `docs/README.md` - Documentation index
- `docs/development/status/STATUS.md` - Current status and checklists
- `docs/development/architecture/ARCHITECTURE_PLAN.md` - Technical implementation
- `docs/development/research/RESEARCH_LOG.md` - Comprehensive research (31 sections)
