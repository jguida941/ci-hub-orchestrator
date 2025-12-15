# Changelog

All notable changes to this project will be documented in this file.

## 2025-12-14
- Added requirements/ with P0, P1, and nonfunctional checklists.
- Replaced plan.md with a concise execution checklist linking to requirements.
- Added doc stubs extracted from the old plan: WORKFLOWS, CONFIG_REFERENCE, TOOLS, TEMPLATES, MODES, TROUBLESHOOTING, ADR index.
- Updated AGENTS to reflect current focus on P0 execution.
- Linked ROADMAP to requirements and noted planned phases.
- Hardened `hub-orchestrator.yml`: pass computed inputs, honor `default_branch`, set dispatch permissions, attempt run-id capture, emit dispatch metadata artifacts, and generate a hub summary/report from dispatch results.
- Added schema validation in orchestrator config load (jsonschema) to fail fast on bad repo configs; compiled scripts to ensure Python syntax.
- Captured dispatch metadata as artifacts for downstream aggregation; summaries now include per-repo dispatch info.
- Implemented aggregation pass to poll dispatched runs, fail on missing/failed runs, download `ci-report` artifacts when present, and roll up coverage/mutation into `hub-report.json`.
- Added schema validation to `scripts/load_config.py`; added `jsonschema` dependency to `pyproject.toml`.
- Added copy/paste templates: `templates/repo/.ci-hub.yml` and `templates/hub/config/repos/repo-template.yaml`.
- Added `config-validate` workflow to run schema validation on config/schema changes and PRs.
- Added ADR-0001 (Central vs Distributed) and expanded docs (CONFIG_REFERENCE, TOOLS, MODES, TROUBLESHOOTING, TEMPLATES).
- Fixed orchestrator config validation indentation bug and added dispatch run-id polling backoff/timeout.
- Added ADRs 0002-0005 (config precedence, reusable vs dispatch, aggregation, dashboard).
- Rewrote ADRs 0003-0006 to match actual implementation: ADR-0003 now accurately documents github-script dispatch mechanism; ADR-0004 now shows actual hub-report.json schema (runs[] array, not object); ADR-0005 added for Dashboard Approach (GitHub Pages); ADR-0006 added for Quality Gates and Thresholds.
