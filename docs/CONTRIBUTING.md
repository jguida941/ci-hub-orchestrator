# Contributing Guide

## Environment Setup

1. Use Python `3.12` (matches GitHub Actions runners).

2. Install tooling deps:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements-dev.txt
   # Optional: ingest helpers
   python -m pip install google-cloud-bigquery
   ```

3. For scripts that call container tooling (`cosign`, `oras`, `syft`, `kyverno`), run `./scripts/install_tools.sh` or install pinned versions manually.

## Branch & PR Expectations

- Prefix feature branches with the subsystem (`feature/mutation-*`, `docs/runbooks-*`, etc.).

- Keep PRs focused on one module/pillar; include before/after context and testing evidence in the description.

- Follow commit prefixes:
  - `feat:<module>` new functionality
  - `fix:<module>` bug fixes
  - `docs:<module>` documentation-only
  - `ops:<module>` runbook or infra changes

## Definition of Done / Checklist

1. Run the suites listed in [Testing](./TESTING.md) that apply to your change (`pytest`, `opa test -v --ignore 'kyverno*' policies`, `scripts/validate_schema.py`, ingest dry runs, etc.).

2. Update module README/runbook if user-facing flows change (e.g., add new flags to `tools/mutation_observatory.py` or new Kyverno steps).

3. Regenerate artifacts/config fixtures when schema contracts shift.

4. Lint markdown: `markdownlint '**/*.md'`.

5. Ensure pipelines remain reproducible (Dockerfile inputs pinned, scripts keep `set -euo pipefail`).

## Documentation Workflow

1. Edit the relevant Markdown/diagrams.

2. Update `docs/mkdocs.yml` navigation if you add/move pages (keep relative paths working locally).

3. Preview locally: `pip install mkdocs-material && cd docs && mkdocs serve`.

4. Commit with the `docs:` prefix when the PR only changes docs/runbooks.

## Code Style

- Python: standard library preferred; format with `ruff format` or `black` (pending tool lock-in). Keep functions small and add targeted docstrings when behavior is non-obvious.

- Bash: always `set -euo pipefail`, prefer POSIX sh where possible, keep shellcheck clean (`shellcheck script.sh`).

- Rego: `opa fmt` before committing.

## Raising Issues / Questions

- Use GitHub Discussions for architecture questions.

- Tag `@ci-intel/ops` for runbook/policy escalations, `@ci-intel/analytics` for schema/dbt topics.

## Changelog

- 2025-10-26: Documentation framework initialized.

- 2025-11-14: Added environment/test workflow + MkDocs guidance.
