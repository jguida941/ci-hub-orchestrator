# AGENTS.md - CI/CD Hub Release

> AI agent context for the hub-release project. See also: `docs/RESEARCH.md`, `docs/ROADMAP.md`

## Project Overview

**hub-release** is a user-friendly CI/CD template repository that runs pipelines for Java and Python projects with boolean toggles for tools. Central execution is the default mode (hub clones repos and runs tests directly).

**Tech Stack:** GitHub Actions, Python 3.11+, YAML configs, Pydantic validation

**Key Principle:** Repos stay clean - target repos don't need workflow files.

## Commands

```bash
# Validate configs
python scripts/validate_config.py config/repos/<repo>.yaml

# Apply a profile to a repo config (creates/merges)
python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/<repo>.yaml

# Load merged config for a repo
python scripts/load_config.py <repo-name>

# Run hub locally (requires act)
act -W .github/workflows/hub-run-all.yml

# Lint Python scripts
ruff check scripts/
ruff format scripts/ --check

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/defaults.yaml'))"
```

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
│   ├── RESEARCH.md        # Research findings (1700+ lines)
│   ├── ROADMAP.md         # Phased implementation plan
│   ├── ONBOARDING.md      # User guide
│   └── adr/               # Architecture Decision Records
├── templates/             # Copy-paste templates for users (see templates/README.md)
├── scripts/               # Python utilities
├── schema/                # JSON Schema definitions
└── plan.md                # Execution checklist (links to requirements)
```

## Key Files to Understand

| File | Purpose | Read First? |
|------|---------|-------------|
| `docs/ROADMAP.md` | Phased implementation plan | YES |
| `docs/RESEARCH.md` | Research and best practices | YES |
| `requirements/` | P0/P1/nonfunctional checklists | YES |
| `plan.md` | Execution checklist (links to requirements) | YES |
| `config/defaults.yaml` | Global config with all toggles | For config changes |
| `.github/workflows/hub-run-all.yml` | Main workflow | For workflow changes |
| `docs/SMOKE_TEST_REPOS.md` | Smoke/fixtures repo mapping (`ci-cd-hub-fixtures`) | For testing |

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

Currently no automated tests. When adding:
- Use pytest for Python scripts
- Use fixture repos in `fixtures/` directory
- Test config loading and validation
- Test workflow behavior with `act`

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

## Current Focus: P0 Execution

- Follow `plan.md` and `requirements/P0.md` for must-haves.
- Dispatch is now wired to pass computed inputs, honor `default_branch`, add permissions, and attempt run-id capture (needs verification).
- Next: real aggregation (download/poll downstream results), schema validation, templates, smoke test.
- Fixtures repo: `https://github.com/jguida941/ci-cd-hub-fixtures` (configs: `config/repos/fixtures-*.yaml`).
- Reference: `requirements/` for checklists; `docs/ROADMAP.md` for phases.

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

**Won't Have (Yet):**
- PyQt6 GUI
- Languages beyond Java/Python

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
- Modify `plan.md`

### Never Do
- Commit secrets, tokens, or API keys
- Force push to master
- Remove or rename `config/defaults.yaml`
- Delete `docs/RESEARCH.md` or `docs/ROADMAP.md`
- Modify files outside `hub-release/` directory
- Create `.env` files with real credentials
- Push directly to master without review

## Tool Reference Quick Links

**Java Tools:** JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, CodeQL
**Python Tools:** pytest, Ruff, Black, Bandit, pip-audit, mypy, mutmut
**Universal:** Semgrep, Trivy, CodeQL

See `docs/RESEARCH.md` sections 9-12 for full tool details.

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
2. Link from ONBOARDING.md
3. Update table of contents if needed

## Related Files

- `CLAUDE.md` - Points to this file for Claude Code compatibility
- `docs/RESEARCH.md` - Comprehensive research (31 sections)
- `docs/ROADMAP.md` - 9-phase implementation plan
- `plan.md` - Original planning document
