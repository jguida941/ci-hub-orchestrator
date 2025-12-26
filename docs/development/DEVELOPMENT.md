# Development Quick Reference

## Goal

**hub-release** is a centralized CI/CD orchestrator that runs quality pipelines for Java and Python repositories. Repos stay clean - they don't need workflow files. The hub clones repos and runs all tools (coverage, linting, security, mutation testing) with simple boolean toggles.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            HUB-RELEASE                                  │
│                                                                         │
│  1. CONFIG LAYER                                                        │
│     config/defaults.yaml  ←── Global tool toggles & thresholds          │
│            ↓                                                            │
│     config/repos/*.yaml   ←── Per-repo overrides (24 repos)             │
│            ↓                                                            │
│     Target repo .ci-hub.yml (optional) ←── Repo can override            │
│                                                                         │
│  2. WORKFLOW LAYER                                                      │
│     hub-run-all.yml      ←── Central mode: hub clones & runs tools      │
│     hub-orchestrator.yml ←── Distributed mode: dispatches to repos      │ 
│            ↓                                                            │
│     java-ci.yml / python-ci.yml ←── Reusable tool workflows             │
│                                                                         │
│  3. OUTPUT LAYER                                                        │
│     reports/*.json       ←── Per-repo results                           │
│     hub-report.json      ←── Aggregated dashboard data                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Config precedence (highest wins):**
```
1. Repo's .ci-hub.yml           ← Highest (repo developer controls)
2. Hub's config/repos/<repo>.yaml  ← Hub admin overrides
3. Hub's config/defaults.yaml      ← Lowest (global defaults)
```

---

## CLI Tool (`cihub`)

The CLI manages configs, initializes repos, and syncs templates.

### Core Commands

| Command    | Purpose                           | Example                                            |
|------------|-----------------------------------|----------------------------------------------------|
| `detect`   | Auto-detect repo language         | `cihub detect --repo . --explain`                  |
| `init`     | Generate .ci-hub.yml + hub-ci.yml | `cihub init --repo . --language python --apply`            |
| `update`   | Refresh existing configs          | `cihub update --repo . --fix-pom --apply`                  |
| `validate` | Check config against schema       | `cihub validate --repo . --strict`                 |
| `new`      | Create hub-side repo config       | `cihub new my-repo --language java --profile fast` |
| `config`   | Manage repo configs               | `cihub config --repo my-repo show --effective`     |

### Setup Commands

| Command          | Purpose                        | Example                              |
|------------------|--------------------------------|--------------------------------------|
| `setup-secrets`  | Set HUB_DISPATCH_TOKEN         | `cihub setup-secrets --all --verify` |
| `setup-nvd`      | Set NVD_API_KEY for OWASP      | `cihub setup-nvd --verify`           |
| `fix-pom`        | Add missing Maven plugins      | `cihub fix-pom --repo . --apply`     |
| `fix-deps`       | Add missing dependencies       | `cihub fix-deps --repo . --apply`    |
| `sync-templates` | Push caller workflows to repos | `cihub sync-templates --check`       |

### Config Subcommands

```bash
cihub config --repo <name> show              # Show raw config
cihub config --repo <name> show --effective  # Show merged with defaults
cihub config --repo <name> enable jacoco     # Enable a tool
cihub config --repo <name> disable pitest    # Disable a tool
cihub config --repo <name> set repo.branch develop  # Set a value
```

---

## Scripts

Located in `scripts/` - standalone utilities.

| Script                        | Purpose                       | Usage                                                                                           |
|-------------------------------|-------------------------------|-------------------------------------------------------------------------------------------------|
| `load_config.py`              | Load & display merged config  | `python scripts/load_config.py --repo fixtures-python-passing`                                  |
| `validate_config.py`          | Validate against schema       | `python scripts/validate_config.py config/repos/fixtures-python-passing.yaml`                   |
| `apply_profile.py`            | Merge profile onto config     | `python scripts/apply_profile.py templates/profiles/python-fast.yaml config/repos/my-repo.yaml` |
| `aggregate_reports.py`        | Build dashboard from reports  | `python scripts/aggregate_reports.py --output dashboard.html`                                   |
| `run_aggregation.py`          | Orchestrator aggregation (CI) | Used by hub-orchestrator.yml                                                                    |
| `run_cli_integration.py`      | CLI integration tests         | `python scripts/run_cli_integration.py --fixtures-path /path/to/ci-cd-hub-fixtures`             |
| `check_quarantine_imports.py` | Ensure no quarantine imports  | CI guardrail                                                                                    |
| `verify_hub_matrix_keys.py`   | Validate workflow matrices    | CI guardrail                                                                                    |

---

## Workflows

Located in `.github/workflows/` - what actually runs.

### Hub Workflows (run on hub-release itself)

| Workflow                | Purpose                                    | Trigger          |
|-------------------------|--------------------------------------------|------------------|
| `hub-production-ci.yml` | Full CI for the hub (lint, test, security) | Push/PR to main  |
| `hub-run-all.yml`       | **Central mode** - clone repos & run tools | Manual dispatch  |
| `hub-orchestrator.yml`  | **Distributed mode** - dispatch to repos   | Manual dispatch  |
| `hub-security.yml`      | Security scanning (SBOM, scorecard)        | Push/PR          |
| `config-validate.yml`   | Validate config files                      | Config changes   |
| `smoke-test.yml`        | Quick integration check                    | PR               |
| `sync-templates.yml`    | Push templates to repos                    | Manual/scheduled |
| `template-guard.yml`    | Check for template drift                   | Nightly          |
| `release.yml`           | Create releases                            | Tag push         |

### Reusable Workflows (called by other repos)

| Workflow         | Purpose                      | Inputs                                             |
|------------------|------------------------------|----------------------------------------------------|
| `java-ci.yml`    | Java pipeline (Maven/Gradle) | `run_jacoco`, `run_checkstyle`, `run_pitest`, etc. |
| `python-ci.yml`  | Python pipeline              | `run_pytest`, `run_ruff`, `run_bandit`, etc.       |
| `kyverno-ci.yml` | Kubernetes policy validation | Policy paths                                       |

---

## Directory Structure

```
hub-release/
├── .github/workflows/     # All GitHub Actions workflows
├── cihub/                 # CLI tool source code
│   ├── cli.py             # Main CLI entry point
│   ├── commands/          # Individual command implementations
│   ├── config/            # Config loading, merging, validation
│   └── wizard/            # Interactive setup wizard
├── config/
│   ├── defaults.yaml      # MASTER CONFIG - all defaults
│   ├── repos/             # Per-repo configs (24 files)
│   └── optional/          # Optional features (chaos, canary, etc.)
├── docs/
│   ├── guides/            # User guides (ONBOARDING, WORKFLOWS, etc.)
│   ├── reference/         # Reference docs (CONFIG_REFERENCE, TOOLS)
│   ├── development/       # Internal docs
│   │   ├── status/        # STATUS.md - current state
│   │   ├── specs/         # P0.md, P1.md - requirements
│   │   ├── architecture/  # ARCH_OVERVIEW, SUMMARY_CONTRACT
│   │   └── archive/       # Old/superseded docs
│   └── adr/               # 27 Architecture Decision Records
├── schema/
│   ├── ci-hub-config.schema.json  # Config validation schema
│   └── ci-report.v2.json          # Report output schema
├── scripts/               # Standalone utilities
├── templates/
│   ├── profiles/          # Pre-built configs (fast, quality, security)
│   ├── repo/              # Templates for target repos
│   └── hub/               # Hub-side templates
├── tests/                 # pytest test suite (80+ tests)
├── policies/kyverno/      # Kubernetes admission policies
└── fixtures/              # Test fixtures (empty placeholders)
```

---

## Key Files

### Status & Planning
| File | What It Is |
|------|------------|
| [STATUS.md](docs/development/status/STATUS.md) | Current blockers, v1.0 progress, what's broken |
| [P0.md](docs/development/specs/P0.md) | MVP requirements checklist (must ship) |
| [P1.md](docs/development/specs/P1.md) | Should-have features |
| [AGENTS.md](AGENTS.md) | Full context for AI assistants and developers |

### Configuration
| File | What It Is |
|------|------------|
| [defaults.yaml](config/defaults.yaml) | **Master config** - all tool toggles, thresholds |
| [config/repos/](config/repos/) | Per-repo overrides (24 repos configured) |
| [ci-hub-config.schema.json](schema/ci-hub-config.schema.json) | JSON Schema that validates all configs |
| [templates/profiles/](templates/profiles/) | Pre-built profiles (fast, quality, security) |

### Workflows
| File | What It Is |
|------|------------|
| [hub-run-all.yml](.github/workflows/hub-run-all.yml) | **Central mode** - hub clones repo, runs all tools |
| [hub-orchestrator.yml](.github/workflows/hub-orchestrator.yml) | **Distributed mode** - dispatches to repo's workflow |
| [java-ci.yml](.github/workflows/java-ci.yml) | Reusable Java workflow (JaCoCo, Checkstyle, SpotBugs, PITest, OWASP) |
| [python-ci.yml](.github/workflows/python-ci.yml) | Reusable Python workflow (pytest, Ruff, Bandit, mutmut, pip-audit) |
| [hub-production-ci.yml](.github/workflows/hub-production-ci.yml) | CI for the hub itself |

### Architecture
| File | What It Is |
|------|------------|
| [ARCH_OVERVIEW.md](docs/development/architecture/ARCH_OVERVIEW.md) | System design with diagrams |
| [SUMMARY_CONTRACT.md](docs/development/architecture/SUMMARY_CONTRACT.md) | Report schema, workflow outputs |
| [docs/adr/](docs/adr/) | 27 Architecture Decision Records |

### Reference
| File | What It Is |
|------|------------|
| [CONFIG_REFERENCE.md](docs/reference/CONFIG_REFERENCE.md) | Every config field explained |
| [TOOLS.md](docs/reference/TOOLS.md) | All 24+ quality tools documented |
| [example.ci-hub.yml](docs/reference/example.ci-hub.yml) | Example repo-side config |

### Governance
| File | What It Is |
|------|------------|
| [CONTRIBUTING.md](.github/CONTRIBUTING.md) | How to contribute, PR process |
| [SECURITY.md](.github/SECURITY.md) | Vulnerability reporting policy |
| [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md) | Community standards |

---

## Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=scripts --cov=cihub

# Specific test file
pytest tests/test_config_module.py -v

# Run CLI integration tests
python scripts/run_cli_integration.py --verbose
```

### Test Files
| File | What It Tests |
|------|---------------|
| `test_commands.py` | All CLI commands |
| `test_config_module.py` | Config loading, merging, validation |
| `test_aggregate_reports.py` | Report aggregation |
| `test_templates.py` | Template rendering |
| `test_pom_tools.py` | Maven POM parsing |
| `test_contract_consistency.py` | Schema contracts |

---

## Quick Commands

```bash
# Prefer the root Makefile for repeatable tasks:
make help
make lint
make format
make test
make typecheck
make actionlint
make sync-templates-check
make mutmut

# === VALIDATION ===
cihub validate --repo .                    # Validate config
ruff check scripts/ cihub/                 # Lint Python
pytest tests/                              # Run tests

# === CONFIG ===
cihub config --repo my-repo show --effective  # See merged config
python scripts/load_config.py my-repo         # Same via script

# === TEMPLATES ===
cihub sync-templates --check               # Check for drift
cihub sync-templates --repo owner/name     # Sync specific repo

# === SETUP ===
cihub init --repo . --language python --apply      # Initialize a repo
cihub setup-secrets --all --verify         # Setup dispatch token
```

---

## Execution Modes

| Mode            | How It Works                          | Workflow               | When to Use                     |
|-----------------|---------------------------------------|------------------------|---------------------------------|
| **Central**     | Hub clones repo, runs tools directly  | `hub-run-all.yml`      | Default, simplest, most control |
| **Distributed** | Hub dispatches to repo's own workflow | `hub-orchestrator.yml` | When repo needs custom steps    |

---

## Tool Matrix

| Category            | Java Tools             | Python Tools       |
|---------------------|------------------------|--------------------|
| **Coverage**        | JaCoCo                 | pytest-cov         |
| **Linting**         | Checkstyle, PMD        | Ruff, Black, isort |
| **Static Analysis** | SpotBugs               | mypy               |
| **Security (code)** | CodeQL, Semgrep        | Bandit, Semgrep    |
| **Security (deps)** | OWASP Dependency-Check | pip-audit          |
| **Mutation**        | PITest                 | mutmut             |
| **Property-Based**  | jqwik                  | Hypothesis         |
| **Container**       | Trivy                  | Trivy              |

---

## Current Status

**Target:** v1.0.0

| Component                                 | Status        |
|-------------------------------------------|---------------|
| Central mode (`hub-run-all.yml`)          | ✅ Working     |
| Reusable workflows (java-ci, python-ci)   | ✅ Working     |
| CLI tool (`cihub`)                        | ✅ 11 commands |
| Unit tests                                | ✅ 80+ tests   |
| Distributed mode (`hub-orchestrator.yml`) | ❌ Failing     |
| Security workflow (`hub-security.yml`)    | ❌ Failing     |

**Blockers for v1.0:**
1. Fix `hub-orchestrator.yml` failures
2. Fix `hub-security.yml` failures

---

## See Also

- [Full Docs Index](docs/README.md)
- [Onboarding Guide](docs/guides/ONBOARDING.md)
- [Config Reference](docs/reference/CONFIG_REFERENCE.md)
- [Tools Reference](docs/reference/TOOLS.md)
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)
- [ADR Index](docs/adr/README.md)
