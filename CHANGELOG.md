# Changelog

All notable changes to this project will be documented in this file.

## 2025-12-15 (Evening)

### Bug Fixes
- Fixed SpotBugs, Checkstyle, PMD not running on repos without `mvnw` - added `mvn` fallback
- Fixed mutmut 0% mutation score - tools now properly detect mutations

### Hub Self-Check Workflow
- Added `hub-self-check.yml` workflow that runs on push/PR to validate hub integrity
- Jobs: syntax-check, unit-tests, validate-templates, validate-configs, verify-matrix-keys
- Runs automatically when scripts, tests, templates, config, or schema files change

### Test Coverage
- Added `tests/test_templates.py` with 70 tests validating all templates against schema
- Tests verify profile merging, dispatch template validity, and no stale repo name references
- Total test count: 109 (39 original + 70 new)

### Tool Defaults
- Enabled ALL tools by default in Java dispatch template (pitest, semgrep, trivy, codeql)
- Enabled ALL tools by default in Python dispatch template (mypy, mutmut, semgrep, trivy, codeql)
- Updated fixture dispatch workflows to match with comprehensive tool status in summaries

### Fixture Enhancements
- Added `requirements.txt` to Python fixtures for pip-audit scanning
- Updated workflow summaries to show all 12 tools with status indicators (✅ Ran / ⏭️ Skipped)
- Temporarily disabled contact-suite-spring config (900 tests, too slow for testing)

### Cross-Repo Authentication
- Added HUB_DISPATCH_TOKEN support for downloading artifacts from dispatched workflow runs
- Required for orchestrator to aggregate reports across repositories

---

## 2025-12-15

### Repository Rename
- Renamed repository from `ci-hub-orchestrator` to `ci-cd-hub`
- Updated all workflow files, documentation, and scripts with new repo name
- Updated git remote URLs and documentation cross-references

### Fixture Enhancement (Comprehensive Tool Testing)
- Enhanced all Python fixtures (`python-passing`, `python-failing`) with rich, mutable code including 20+ math functions with conditionals, loops, type hints
- Enhanced all Java fixtures (`java-passing`, `java-failing`) with comprehensive Calculator classes
- Enabled ALL tools in fixture configs: pytest, ruff, black, isort, bandit, pip-audit, mypy, mutmut, hypothesis, semgrep (Python); checkstyle, spotbugs, owasp, pmd, pitest, semgrep (Java)
- Added intentional bugs and security issues to `*-failing` fixtures for tool detection validation

### Mutmut 3.x Compatibility
- Fixed mutmut invocation for 3.x CLI (removed deprecated `--paths-to-mutate` and `--runner` flags)
- Added `[tool.mutmut]` configuration to fixture `pyproject.toml` files with `paths_to_mutate` and `tests_dir` settings
- mutmut 3.x now uses config file instead of command-line arguments

### Workflow Improvements
- Fixed "Invalid format" errors in GitHub Actions output parsing
- Replaced `grep ... || echo 0` patterns with `${VAR:-0}` default value fallbacks
- Used lookahead regex patterns (`\d+(?= passed)`) for more robust test count extraction
- Added `tail -1` to ensure only final summary line is captured

### Documentation Cleanup
- Removed stale `docs/analysis/scalability.md` (old brainstorm doc)
- Fixed duplicate Kyverno entries in `docs/README.md`
- Added `docs/development/audit.md` to `.gitignore`

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
