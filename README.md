# CI/CD Hub

[![Hub Production CI](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml/badge.svg)](https://github.com/jguida941/ci-cd-hub/actions/workflows/hub-production-ci.yml)
[![License: Elastic 2.0](https://img.shields.io/badge/license-Elastic%202.0-blue)](LICENSE)

Centralized CI/CD for Java and Python repos with config-driven toggles, reusable workflows, and a single hub that runs pipelines across many repositories.

## Quick Start

### Central mode (default)
```bash
# Run all repos
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub

# Run by group
gh workflow run hub-run-all.yml -R jguida941/ci-cd-hub -f run_group=fixtures
```

### Distributed mode (optional)
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
- [Architecture Plan](docs/development/architecture/ARCHITECTURE_PLAN.md)
- [Current Status](docs/development/status/STATUS.md)
- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)
- [Smoke Test Guide](docs/development/execution/SMOKE_TEST.md)

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](.github/SECURITY.md).

## License

Elastic License 2.0. See [LICENSE](LICENSE).
