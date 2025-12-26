# Contributing

Thanks for helping improve CI/CD Hub. This project is production-grade; changes must be deliberate and well-tested.

## Getting Started

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

## Development Workflow

- Run tests:
  ```bash
  cd "$(git rev-parse --show-toplevel)"
  pytest tests/
  ```
- Lint and format:
  ```bash
  cd "$(git rev-parse --show-toplevel)"
  ruff check .
  ruff format .
  ```

## Command Matrix (What to Run and When)

Use these commands from anywhere in the repo (they auto-jump to root):

| Task | When to Run | Command |
|------|-------------|---------|
| Unit tests | Any Python/CLI change | `cd "$(git rev-parse --show-toplevel)" && pytest tests/` |
| Lint | Any Python change | `cd "$(git rev-parse --show-toplevel)" && ruff check .` |
| Format | Before PR | `cd "$(git rev-parse --show-toplevel)" && ruff format .` |
| Type check | CLI/config/script changes | `cd "$(git rev-parse --show-toplevel)" && mypy cihub/ scripts/` |
| Validate repo config | Editing `config/repos/*.yaml` | `cd "$(git rev-parse --show-toplevel)" && python scripts/validate_config.py config/repos/<repo>.yaml` |
| Load merged config | Debug config merges | `cd "$(git rev-parse --show-toplevel)" && python scripts/load_config.py <repo-name>` |
| Apply profile | Creating/merging repo config | `cd "$(git rev-parse --show-toplevel)" && python scripts/apply_profile.py templates/profiles/<profile>.yaml config/repos/<repo>.yaml` |
| Workflow lint | After workflow edits | `cd "$(git rev-parse --show-toplevel)" && actionlint .github/workflows/*.yml` |
| Template drift check | After workflow/template edits | `cd "$(git rev-parse --show-toplevel)" && python -m cihub sync-templates --check` |
| Template sync (scoped) | When drift found | `cd "$(git rev-parse --show-toplevel)" && python -m cihub sync-templates --repo owner/name` |
| Hub run (local) | Debug central workflow | `cd "$(git rev-parse --show-toplevel)" && act -W .github/workflows/hub-run-all.yml` |
| Mutation testing (optional) | Before release | `cd "$(git rev-parse --show-toplevel)" && mutmut run` |

Notes:
- Java/Python tool suites (JaCoCo, PITest, Checkstyle, SpotBugs, Bandit, pip-audit, Semgrep, Trivy, CodeQL) run inside workflows; validate by running workflows or `act` where feasible.
- `actionlint`, `mutmut`, and `act` require local installs.

## Workflow/Template Changes

If you change reusable workflows or caller templates, you must run:
```bash
python -m cihub sync-templates --check
```
Follow the template sync checklist in `AGENTS.md`.

## Documentation

Update docs when behavior changes. Use `docs/README.md` as the master index.

## Pull Requests

- Keep changes scoped and explain intent.
- Add tests for behavior changes.
- Link related ADRs or create a new ADR for major design changes.
