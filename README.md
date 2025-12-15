# CI/CD Hub

Centralized CI/CD for Java and Python repos, with optional dispatch to reusable workflows. Repos stay clean; the hub does the work.

## Purpose

Provide one hub that can run full CI/security across many repos (central mode) or trigger reusable workflows in target repos (distributed mode), with predictable fixtures for validation and schema-validated configs.

## Architecture

```mermaid
flowchart TD
    Configs[config/repos/*.yaml<br/>(repo, subdir, toggles)] --> RunAll[hub-run-all.yml<br/>(central)]
    Configs --> Orchestrator[hub-orchestrator.yml<br/>(dispatch)]
    RunAll --> Java[Reusable java-ci.yml]
    RunAll --> Py[Reusable python-ci.yml]
    Orchestrator --> Java
    Orchestrator --> Py
    Fixtures[ci-cd-hub-fixtures<br/>(java/passing, java/failing,<br/>python/passing, python/failing)] --> Configs
```

## Capabilities

- **Languages:** Java, Python
- **Modes:** Central (hub clones and runs CI) and Distributed (dispatch to reusable workflows)
- **Monorepo:** `repo.subdir` supported for projects in subfolders
- **Fixtures:** Deterministic test repos at `https://github.com/jguida941/ci-cd-hub-fixtures`
- **Reporting:** Step summaries, artifacts, aggregation, smoke tests
- **Profiles/Templates:** Fast/quality/security/minimal/coverage/compliance profiles; repo/hub templates
- **Validation:** JSON Schema for configs; `scripts/validate_config.py`
- **Docs:** Guides, reference, development, ADRs under `docs/`

### Java Tools
JaCoCo, Checkstyle, SpotBugs, PMD, OWASP Dependency-Check, PITest, Semgrep, Trivy, CodeQL, Docker (optional)

### Python Tools
pytest-cov, Ruff, Black, isort, Bandit, pip-audit, mypy, mutmut, Semgrep, Trivy, CodeQL, Docker (optional)

## Workflows

- `.github/workflows/hub-run-all.yml` - Central execution over `config/repos/*.yaml` (honors `repo.subdir`)
- `.github/workflows/hub-orchestrator.yml` - Dispatch to reusable workflows (passes `workdir` to subdir projects)
- `.github/workflows/java-ci.yml` - Reusable Java CI (supports `workdir`)
- `.github/workflows/python-ci.yml` - Reusable Python CI (supports `workdir`)
- `.github/workflows/smoke-test.yml` - Smoke validation using fixture configs
- `.github/workflows/config-validate.yml` - Schema validation

## Profiles and Templates

- Profiles (fast, quality, security, minimal, coverage-gate, compliance for Java/Python) live in `templates/profiles/`.
- Apply a profile: `python scripts/apply_profile.py templates/profiles/java-fast.yaml config/repos/my-repo.yaml`
- Validate configs: `python scripts/validate_config.py config/repos/my-repo.yaml`
- Monorepo template: `templates/hub/config/repos/monorepo-template.yaml`

## Getting Started (Central Mode)

1) Add a config: `config/repos/my-repo.yaml`
```yaml
repo:
  owner: your-github-username
  name: your-repo
  language: java   # or python
  default_branch: main
  # subdir: path/inside/monorepo   # optional
```

2) Optionally start from a profile:
```bash
python scripts/apply_profile.py templates/profiles/java-fast.yaml config/repos/my-repo.yaml
python scripts/validate_config.py config/repos/my-repo.yaml
```

3) Run hub-run-all:
```bash
gh workflow run hub-run-all.yml -R jguida941/ci-hub-orchestrator \
  -f repos="fixtures-java-passing,fixtures-python-passing"
```

## Distributed Mode

In a target repo, call the reusable workflow and pass `workdir` if using a subfolder:
```yaml
jobs:
  ci:
    uses: jguida941/ci-hub-orchestrator/.github/workflows/java-ci.yml@main
    with:
      java_version: '21'
      run_jacoco: true
      run_pitest: false
      run_trivy: false
      workdir: .        # set to subdir for monorepo
    secrets: inherit
```

## Monorepo Support

- Set `repo.subdir` in `config/repos/*.yaml`
- Hub central workflow rewrites checkout into that subdir
- Orchestrator passes `workdir` to reusable workflows
- Template: `templates/hub/config/repos/monorepo-template.yaml`
- Guide: `docs/guides/MONOREPOS.md`

## Fixtures and Smoke Tests

- Fixtures repo: `https://github.com/jguida941/ci-cd-hub-fixtures` (subdirs for passing/failing Java/Python)
- Fixture configs: `config/repos/fixtures-*.yaml` (use `subdir`)
- Smoke test guide: `docs/development/SMOKE_TEST.md`
- Smoke repos info: `docs/development/SMOKE_TEST_REPOS.md`

## Documentation Map

- Guides: `docs/guides/` (ONBOARDING, WORKFLOWS, MODES, TEMPLATES, TROUBLESHOOTING, MONOREPOS)
- Reference: `docs/reference/` (CONFIG_REFERENCE, TOOLS, example.ci-hub.yml)
- Development: `docs/development/` (ROADMAP, RESEARCH, SMOKE_TEST*, audit)
- ADRs: `docs/adr/` (0001-0009)

## Repo Structure (top-level)

```
hub-release/
├── .github/workflows/    # hub-run-all, hub-orchestrator, reusable java/python, smoke-test
├── config/               # defaults and per-repo configs (supports subdir)
├── docs/                 # guides, reference, development, adr
├── templates/            # repo/hub configs, profiles, monorepo template
├── scripts/              # apply_profile.py, validate_config.py, load_config.py
├── schema/               # JSON schema (includes repo.subdir)
└── fixtures/             # local fixture source (primary fixtures hosted in ci-cd-hub-fixtures)
```

## Links

- Hub repo: `https://github.com/jguida941/ci-hub-orchestrator`
- Fixtures repo: `https://github.com/jguida941/ci-cd-hub-fixtures`
- Primary docs index: `docs/README.md`
