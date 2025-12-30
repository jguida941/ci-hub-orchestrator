# ADR-0032: PyQt6 GUI Wrapper for Full Automation

**Status**: Accepted  
**Date:** 2025-12-26  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The project goal is zero-manual setup: users should not edit YAML, pom.xml,
or GitHub settings by hand. The CLI (`cihub`) already contains the logic to
detect repos, generate configs, and enforce policies. The planned PyQt6 GUI
must expose the same capabilities without duplicating logic.

## Decision

The **PyQt6 GUI is a thin wrapper around the CLI** and must provide full
automation for onboarding and managing repos. The GUI never reimplements
business logic; it only calls CLI commands (via QProcess) and renders JSON
responses.

### Rationale

- One source of truth for behavior (CLI) avoids drift and duplication.
- The GUI should be a presentation layer, not a second implementation.
- Full automation requires authenticated GitHub actions; the CLI already
  integrates with `gh` and git.

### Required Capabilities (Must Support)

**Repo lifecycle**
- Create repo via `gh repo create` (new) or open existing repo.
- Clone/init repos and set default branch.
- Support monorepo subdir configuration and multiple sub-configs per repo.
- Support multi-language setups (multiple subdirs, python + java).

**Config + workflow generation**
- Generate `.ci-hub.yml` and thin caller workflow (`.github/workflows/ci.yml`).
- Central vs Distributed mode toggle:
  - Central: no workflow files, hub-run-all executes.
  - Distributed: thin caller + reusable workflow.
- Basic/Advanced modes:
  - Basic: boolean toggles + profile defaults.
  - Advanced: numeric threshold overrides and custom commands.
- Import and merge existing `.ci-hub.yml` with diff preview.

**GitHub automation**
- Set secrets via `gh secret set` (NVD_API_KEY, Semgrep, Docker/registry, etc).
- Configure branch protection via `gh api`.
- Push changes with default branch + PR workflow (opt-in direct push).
- Sync templates and detect drift (update repo workflows/configs).

**Tooling + build**
- Run `cihub validate`, `cihub preflight`, and `cihub ci` from the GUI.
- Java support includes pom.xml scanning and auto-fix commands.
- Python support includes dependency detection and custom test commands.

**Extensibility**
- If a required capability is missing, implement it in `cihub` as a new command
  or script and expose it in the GUI. The GUI must not bypass the CLI.

### CLI Command Map (GUI Uses)

**Existing commands**
- `cihub detect`
- `cihub init`
- `cihub update`
- `cihub validate`
- `cihub new`
- `cihub config` (edit/show/set/enable/disable)
- `cihub fix-pom`
- `cihub fix-deps`
- `cihub setup-secrets`
- `cihub setup-nvd`
- `cihub sync-templates`

**Required commands (plan)**
- `cihub ci` (run all enabled tools, produce report + summary)
- `cihub run <tool>` (single tool execution + JSON output)
- `cihub report build`
- `cihub report summary`
- `cihub preflight`
- `cihub verify-github`
- `cihub repo create|clone|attach`
- `cihub secrets set|list|verify`
- `cihub protect`
- `cihub push` (PR-first, opt-in direct push)
- `cihub migrate` (optional CI migration)

### Dependency Strategy

- Base install is minimal (`pyyaml`, `jsonschema`, `defusedxml`).
- Optional extras provide tool runners: `cihub[ci]`.
- Python tool extras include pytest/pytest-cov, ruff, black, isort, mypy,
  bandit, pip-audit, mutmut, hypothesis.
- Custom commands (e.g., Makefile targets) are supported via config and
  captured in `report.json`.

### CLI Contract (Non-Negotiable)

All CLI commands used by the GUI must support `--json` output with a stable
response envelope (see ADR-0029 and architecture plan). The GUI is not allowed
to parse logs for state.

## Consequences

**Positive:**
- Users can fully onboard and manage repos without manual edits.
- Consistent behavior across CLI, GUI, and workflows.
- Changes are testable and centralized in the CLI.

**Negative:**
- CLI distribution and version pinning are required for workflows.
- Requires `gh` authentication for GitHub automation.

## Alternatives Considered

1. **GUI implements business logic directly**
   - Rejected: duplicates logic, breaks consistency, harder to test.

2. **Manual setup steps remain**
   - Rejected: violates the zero-manual goal.

3. **Web app instead of desktop GUI**
   - Rejected for now: higher operational overhead and auth complexity.

## References

- ADR-0031: CLI-Driven Workflow Execution (Thin Workflows)
- ADR-0029: CLI Exit Code Registry
- `docs/development/archive/ARCHITECTURE_PLAN.md`
- `pyqt/planqt.md`
