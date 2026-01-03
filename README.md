# CI/CD Hub

[![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://github.com/jguida941/ci-cd-hub)
[![Java](https://img.shields.io/badge/java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)](https://github.com/jguida941/ci-cd-hub)
[![codecov](https://img.shields.io/codecov/c/github/jguida941/ci-cd-hub?style=for-the-badge&logo=codecov&logoColor=white)](https://codecov.io/gh/jguida941/ci-cd-hub)
[![mutmut](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/mutmut.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/ruff.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![bandit](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/bandit.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![pip-audit](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/pip-audit.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![zizmor](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jguida941/ci-cd-hub/main/badges/zizmor.json&style=for-the-badge)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![License: Elastic 2.0](https://img.shields.io/badge/license-Elastic%202.0-blue?style=for-the-badge)](LICENSE)

Centralized CI/CD for Java and Python repos with config-driven toggles, reusable workflows, and a single hub that runs pipelines across many repositories.

## Execution Modes

- Central mode: the hub clones repos and runs pipelines directly from a single workflow.
- Distributed mode: the hub dispatches workflows to each repo via caller templates and reusable workflows.

## Toolchains

- Java: JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, jqwik, Semgrep, Trivy, CodeQL, Docker.
- Python: pytest, Ruff, Black, isort, Bandit, pip-audit, mypy, mutmut, Hypothesis, Semgrep, Trivy, CodeQL, Docker.

## Quick Start

### Central mode
```bash
# Run all repos
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub

# Run by group
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub -f run_group=fixtures
```

### Distributed mode 
1) Create a PAT with `repo` + `workflow` scopes.
2) Set `HUB_DISPATCH_TOKEN` via CLI:
   ```bash
   python -m cihub setup-secrets --all
   ```
3) In each target repo:
   ```bash
   python -m cihub init --repo . --apply
   ```
4) Set `dispatch_enabled: true` in `config/repos/<repo>.yaml`.

## Prerequisites

- Python 3.11+
- GitHub Actions for workflow execution
- GitHub CLI (`gh`) recommended for dispatching workflows

## Installation (local development)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/requirements-dev.txt
```

## Documentation

- [Full Docs Index](docs/README.md)
- [Architecture Overview](docs/development/architecture/ARCH_OVERVIEW.md)
- [Current Status](docs/development/status/STATUS.md)
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)
- [Smoke Test Guide](docs/development/execution/SMOKE_TEST.md)

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](.github/SECURITY.md).

## License

Elastic License 2.0. See [LICENSE](LICENSE).
