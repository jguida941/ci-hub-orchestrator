# Developer Commands

Use the root `Makefile` as the single entry point for development tasks.

## Quick Start

```bash
make help
make lint
make format
make test
```

## When to Use Which Target

- `make lint` / `make format`: any Python change
- `make test`: before PRs or behavior changes
- `make typecheck`: CLI/config/script changes
- `make validate-config`: editing `config/repos/*.yaml`
- `make load-config`: debugging merged configs
- `make apply-profile`: creating/merging repo configs
- `make actionlint`: workflow changes
- `make sync-templates-check`: workflow/template changes
- `make hub-run`: local workflow debug (requires `act`)
- `make mutmut`: mutation testing (optional, slower)
- `make aggregate-reports`: dashboard generation

## Notes

- Java/Python tool suites (JaCoCo, PITest, Checkstyle, SpotBugs, Bandit, pip-audit, Semgrep, Trivy, CodeQL) run inside workflows.
- Some tools require local installs (`actionlint`, `act`, `mutmut`).
