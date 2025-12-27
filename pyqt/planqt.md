## Plan for Simplified Workflow + PyQt6 GUI

  - Wrapper uses embedded defaults and fromJson() when passing values (so booleans/numbers behave correctly).
  - Update tests/docs so CI doesn’t fail.
  - Orchestrator dispatches only minimal inputs.

Additions to include (automation + zero-code setup):
- Support two modes in GUI/CLI: Central (no workflow files, hub-run-all) and Distributed (thin caller).
- GUI/CLI can automate GitHub setup via gh CLI (repo create, secrets, branch protection, push).
- Secrets setup step is mandatory when enabling tools that require tokens (NVD_API_KEY, Semgrep, Docker/registry).
- Changes should default to branch + PR flow with diff preview (no direct push unless user opts in).
- Import/merge existing `.ci-hub.yml` and show a diff before overwrite.
- Basic/Advanced UI toggle: Basic = booleans + profile; Advanced = numeric overrides.
- Monorepo + multi-language support: multiple subdir configs in one repo.
- Workflow size reduction: reusable workflows should be thin wrappers; `cihub` replaces inline scripts.

Explicit scope + constraints (must be in plan):
- Thin workflows only: caller ~5-10 lines; reusable workflows small and consistent.
- No inline parsing/scraping in YAML. Parsing, gating, and summaries live in `cihub`.
- `cihub ci` (or `cihub run <tool>`) reads `.ci-hub.yml`, runs tools, applies thresholds,
  produces `report.json`, and renders the unified summary.
- No `config_override` workflow inputs (avoid extra config layers). `.ci-hub.yml` is the only source of truth.
- PyQt6 GUI is a strict wrapper around CLI (QProcess + JSON output). No logic duplication.
- Full automation: create repo, set secrets, branch protection, write configs/workflows,
  push changes (default PR flow; direct push only if user opts in).
- Must support monorepos, multi-language repos, custom test commands, self-hosted runners.
- If capability missing, add a CLI command/script and expose it in GUI (no manual steps).

ADRs to reference in this plan:
- ADR-0031: CLI-Driven Workflow Execution (Thin Workflows)
- ADR-0032: PyQt6 GUI Wrapper for Full Automation
- ADR-0033: CLI Distribution and Automation Enhancements
- ADR-0029: CLI Exit Code Registry (JSON contract)
- ADR-0028: Boolean Config Type Coercion
- ADR-0024: Workflow Dispatch Input Limit

CLI command map (GUI uses):
Existing:
- cihub detect
- cihub init
- cihub update
- cihub validate
- cihub new
- cihub config (edit/show/set/enable/disable)
- cihub fix-pom
- cihub fix-deps
- cihub setup-secrets
- cihub setup-nvd
- cihub sync-templates

Required (plan):
- cihub ci
- cihub run <tool>
- cihub report build
- cihub report summary
- cihub preflight
- cihub verify-github
- cihub repo create|clone|attach
- cihub secrets set|list|verify
- cihub protect
- cihub push (PR-first, opt-in direct push)
- cihub migrate (optional)

Dependency strategy:
- Base install stays minimal (pyyaml/jsonschema/defusedxml).
- Add optional extras: cihub[ci] for tool runners.
- Workflows install cihub[ci] (or cihub ci --install-tools).
- Java uses Maven/Gradle wrappers; Python tools come from extras
  (e.g., pytest/pytest-cov, ruff, black, isort, mypy, bandit, pip-audit,
  mutmut, hypothesis).

Versioning strategy (dev workflow):
- Use `v0-dev` tag for development testing. Fixtures point to `@v0-dev`.
- After each push to `simplify-workflows`, update the tag:
  ```bash
  git tag -f v0-dev && git push origin v0-dev --force
  ```
- This avoids updating SHA in every fixture workflow on each commit.
- For production: use semantic version tags (v1.0.0, v1.1.0, etc.)
- Release workflow creates immutable tags; `v0-dev` is mutable for dev only.

Research additions (explicit requirements):
- CLI distribution: PyPI publish + scoped tokens + automated release workflow.
- Custom command parsing modes: exit_code, json, regex.
- Private deps auth: PIP_INDEX_URL with secrets; Maven settings.xml secret.
- PyQt6 CLI wrapper must use QProcess with streamed output (no blocking UI).
- Makefile support is explicit in config (never auto-run); expose GUI toggle.
- Workflow limits documented (10 nesting levels, 50 unique calls).
- Schema validation via check-jsonschema + pre-commit hook.
- POM editing: current approach is fragile; consider pom-tuner patterns.
- Secrets automation: set/list/verify/discover commands.
- CLI framework: keep argparse for base install; revisit Typer later if needed.

Composite actions (optional, post-CLI parity):
- Goal: reduce reusable workflow YAML to ~50 lines without adding new config layers.
- Keep composite actions in hub repo only; target repos still use 5–10 line callers.
- Example action sketch:
  - `.github/actions/setup-python-env/action.yml`
    - uses: actions/setup-python@v5
    - run: python -m pip install --upgrade pip
    - run: pip install cihub[ci]
  - `.github/actions/upload-ci-report/action.yml`
    - uses: actions/upload-artifact@v4
    - path: .cihub/report.json + .cihub/summary.md
- Decision: optional phase; do not implement until CLI outputs are stable.

Makefile integration (CLI-first):
- Add `cihub preflight --use-makefile` and `cihub ci --preflight` to run make targets first.
- Config opt-in:
  python:
    tools:
      makefile: { enabled: true, targets: ["lint", "test"] }
- GUI should expose a toggle + target list; defaults remain off.

Execution order (avoid rework):
- Build CLI core first (`cihub ci`, `cihub run <tool>`, `cihub report build/summary`).
- Pilot on one workflow (python-ci) + fixtures to validate report + summary parity.
- Port java-ci and hub-run-all only after CLI outputs match.
- Do not spend time polishing inline YAML parsing that will be removed.

  Phase A (10 steps):
  - A1: Create simplify-workflows branch
  - A2: Create hub-ci.yml wrapper (with embedded defaults, fromJson() for types)
  - A3: Simplify python-ci.yml
  - A4: Simplify java-ci.yml
  - A5: Update templates (5-line callers)
  - A6: Update hub-orchestrator.yml (minimal dispatch)
  - A7: Remove threshold_overrides_yaml everywhere
  - A8: Handle hub-run-all.yml (deprecate for now)
  - A9: Update tests and docs
  - A10: Test workflows

  Files to modify (11 files):
  - Workflows: hub-ci.yml (create), python-ci.yml, java-ci.yml, hub-orchestrator.yml, hub-run-all.yml
  - Templates: hub-python-ci.yml, hub-java-ci.yml, .ci-hub.yml
  - Tests: test_contract_consistency.py, test_config_pipeline.py
  - Scripts: load_config.py

  Ready to execute Phase A on simplify-workflows branch.

───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 Ready to code?

 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Plan: Simplified Workflow + PyQt6 GUI

 NEW SIMPLIFIED DESIGN (stays under 25 inputs!)

 Input counts:
 - Python: 2 essentials + 13 toggles + 9 thresholds = 24
 - Java: 3 essentials + 12 toggles + 9 thresholds = 24

 Target Repo Files (2 files only!)

 1. .github/workflows/ci.yml (or hub-ci.yml):
 name: CI
 on: [push, pull_request, workflow_dispatch]

 jobs:
   ci:
     uses: jguida941/ci-cd-hub/.github/workflows/hub-ci.yml@main
     secrets: inherit

 2. .ci-hub.yml (simple booleans + thresholds):
 version: "1.0"
 repo:
   owner: myorg
   name: my-service
   language: python
 language: python

 python:
   version: "3.12"
   tools:
     pytest:   { enabled: true, min_coverage: 80 }
     ruff:     { enabled: true, max_errors: 0 }
     black:    { enabled: true }
     mypy:     { enabled: false }
     mutmut:   { enabled: true, min_mutation_score: 70 }

 thresholds:
   max_critical_vulns: 0
   max_high_vulns: 0

 Hub Workflow (NEW: hub-ci.yml wrapper)

 Single wrapper workflow that:
 1. Reads .ci-hub.yml from calling repo
 2. Parses all settings with Python script
 3. Calls python-ci.yml or java-ci.yml with parsed values

 This eliminates:
 - Complex threshold resolution in reusable workflows
 - Multiple config layers
 - The 100-line shell scripts with embedded Python

 ---
 DECISIONS MADE

 | Decision                 | Choice                                                                                          |
 |--------------------------|-------------------------------------------------------------------------------------------------|
 | Source of truth          | .ci-hub.yml is authoritative; hub config (config/repos/*.yaml) used only for repo list/metadata |
 | Shorthand booleans       | Defer to Phase B (requires schema + validation updates)                                         |
 | Caller filename          | hub-ci.yml (keeps orchestrator working)                                                         |
 | Branch                   | simplify-workflows                                                                              |
 | CLI changes              | NOT needed in Phase A - updating templates is enough (CLI "just works")                         |
 | threshold_overrides_yaml | REMOVE everywhere - single source of truth is .ci-hub.yml                                       |

 ---
 Implementation Plan (Ordered by Priority)

 PHASE A: Workflow Simplification (DO FIRST)

 Goal: Fix the mess quickly. Get simple booleans working.

 Step A1: Create branch

 git checkout -b simplify-workflows

 Step A2: Create hub-ci.yml wrapper

 File: .github/workflows/hub-ci.yml
 - Reads .ci-hub.yml from calling repo
 - Parses all settings (Python script)
 - Outputs booleans + thresholds to GITHUB_OUTPUT
 - Calls python-ci.yml or java-ci.yml based on language

 Implementation details:
 - Defaults source: Embed defaults in wrapper (copied from config/defaults.yaml), comment that they must stay in sync. OR require
 .ci-hub.yml to be fully explicit.
 - Type parsing: Outputs are strings in GitHub Actions. Use fromJson() when passing into python-ci.yml/java-ci.yml so booleans and
  numbers work correctly.
 with:
   run_pytest: ${{ fromJson(needs.config.outputs.run_pytest) }}
   coverage_min: ${{ fromJson(needs.config.outputs.coverage_min) }}

 Step A3: Simplify python-ci.yml

 - Remove "Resolve Thresholds" step (lines 196-294)
 - Just use inputs directly
 - Keep tool steps unchanged

 Step A4: Simplify java-ci.yml

 - Same pattern - remove threshold resolution

 Step A5: Update templates

 - templates/repo/hub-python-ci.yml → 5-line caller
 - templates/repo/hub-java-ci.yml → 5-line caller
 - templates/repo/.ci-hub.yml → clean format example

 Step A6: Update hub-orchestrator.yml

 - Stop sending the old input list
 - New flow: dispatch only hub_correlation_id (or minimal essentials)
 - The wrapper reads .ci-hub.yml and passes everything to python-ci.yml/java-ci.yml

 Step A7: Remove threshold_overrides_yaml everywhere

 - Remove from python-ci.yml inputs
 - Remove from java-ci.yml inputs
 - Remove from hub-run-all.yml
 - Remove from load_config.py (if applicable)

 Step A8: Handle hub-run-all.yml

 Decision needed: Either:
 1. Align with new model (use hub-ci.yml wrapper pattern), OR
 2. Mark as deprecated/out-of-scope so it doesn't drift

 For now: Option 2 (mark deprecated) - focus on distributed mode first.

 Step A9: Update tests and docs

 - tests/test_contract_consistency.py - remove threshold_overrides_yaml references
 - tests/test_config_pipeline.py - update for new flow
 - ADR references - update any ADRs that mention threshold_overrides_yaml
 - Confirm WORKFLOW_ONLY_INPUTS set doesn't break with changes

 Step A10: Test workflows

 - Run smoke tests
 - Verify existing repos work
 - Test with fixture repos

 ---
 PHASE B: Shorthand Booleans + Schema Updates (After Workflows Stabilize)

 Goal: Support cleaner config syntax with shorthand booleans.

 Why defer: Requires schema + validation updates. Better to stabilize core workflows first.

 Step B1: Update JSON schema

 - Allow both pytest: true AND pytest: { enabled: true }
 - Add oneOf or anyOf schema patterns

 Step B2: Add config normalization

 - In config loading, normalize pytest: true → pytest: { enabled: true }
 - Keeps downstream code simple (always sees full format)

 Step B3: Update validation

 - Ensure both formats pass validation
 - Add tests for shorthand format

 Step B4: Update documentation

 - Show shorthand examples in docs
 - Keep full format as "canonical" for generated configs

 ---
 PHASE C: PyQt6 GUI (Follow-up - After Workflows Stabilize)

 Goal: GUI as thin layer over CLI. Don't reimplement. Don't destabilize core CI.

 Why defer: Core CI stability is priority. GUI is nice-to-have.

 Approach:
 - GUI collects inputs via checkboxes/fields
 - GUI imports and calls CLI functions - NOT reimplementing logic
 - GUI calls cihub fix-pom / cihub update for POM/pyproject
 - Reuse all CLI logic - zero duplication
 - Isolated in workflow-generator/ subdirectory - doesn't affect existing code

 Step C1: Create workflow-generator/ - FULL GUI APP

 Not just a config generator - a complete all-in-one tool:

 Core Features (everything CLI does, no terminal needed):
 1. Repo Onboarding
   - Enter repo URL or browse local folder
   - Auto-detect language (Java/Python)
   - Configure tools with checkboxes
   - Set thresholds with spinboxes
   - Generate all files (.ci-hub.yml, hub-ci.yml)
   - Push to repo with one button
 2. Repo Management
   - List all configured repos
   - Edit existing configs
   - Enable/disable tools
   - View status
 3. Secret Setup
   - Set HUB_DISPATCH_TOKEN
   - Set NVD_API_KEY
   - GitHub API integration
 4. Java POM Management
   - Load pom.xml
   - Show missing plugins
   - Add plugins with one click
   - Add dependencies
 5. Sync & Push
   - Sync templates to repos
   - Push changes
   - View diffs before pushing
 6. Validation
   - Validate configs
   - Show errors inline
   - Fix suggestions

 UI Layout:
 ┌──────────────────────────────────────────────────────────────────┐
 │  CI/CD Hub Manager                                    [_][□][X]  │
 ├──────────────────────────────────────────────────────────────────┤
 │  [Repos] [Onboard] [Secrets] [Settings]                          │
 ├──────────────────────────────────────────────────────────────────┤
 │  ┌────────────┐ ┌──────────────────────────────────────────────┐ │
 │  │ REPOS      │ │  REPO: myorg/my-service                      │ │
 │  │            │ │  ┌──────────────────────────────────────────┐ │ │
 │  │ ▸ myorg/   │ │  │ Language: [Python ▼]  Version: [3.12]   │ │ │
 │  │   my-svc   │ │  │ Branch: [main    ]    Monorepo: [ ]     │ │ │
 │  │   other    │ │  └──────────────────────────────────────────┘ │ │
 │  │ ▸ fixtures │ │  ┌──────────────────────────────────────────┐ │ │
 │  │   java-pass│ │  │ TOOLS                                    │ │ │
 │  │   py-pass  │ │  │ [x] pytest  [x] ruff   [x] bandit        │ │ │
 │  │            │ │  │ [x] black   [ ] mypy   [ ] mutmut        │ │ │
 │  │            │ │  └──────────────────────────────────────────┘ │ │
 │  │            │ │  ┌──────────────────────────────────────────┐ │ │
 │  │            │ │  │ THRESHOLDS                               │ │ │
 │  │            │ │  │ Coverage: [80]%  Mutation: [70]%         │ │ │
 │  │            │ │  └──────────────────────────────────────────┘ │ │
 │  │            │ │                                               │ │
 │  │ [+ Add]    │ │  [Save] [Push to Repo] [Validate] [Delete]    │ │
 │  └────────────┘ └──────────────────────────────────────────────┘ │
 ├──────────────────────────────────────────────────────────────────┤
 │  Status: Ready                                                   │
 └──────────────────────────────────────────────────────────────────┘

 Step 8: Test

 - Run smoke tests on workflow changes
 - Test PyQt6 app end-to-end
 - Test push to real repo
 - Verify existing repos still work

 ---
 Files to Modify (Phase A)

 | File                                   | Action                                                                        |
 |----------------------------------------|-------------------------------------------------------------------------------|
 | .github/workflows/hub-ci.yml           | CREATE - new wrapper workflow (with embedded defaults, fromJson() for types)  |
 | .github/workflows/python-ci.yml        | SIMPLIFY - remove threshold resolution, remove threshold_overrides_yaml input |
 | .github/workflows/java-ci.yml          | SIMPLIFY - remove threshold resolution, remove threshold_overrides_yaml input |
 | .github/workflows/hub-orchestrator.yml | SIMPLIFY - dispatch only hub_correlation_id, not full input list              |
 | .github/workflows/hub-run-all.yml      | DEPRECATE - add comment, remove threshold_overrides_yaml, or align later      |
 | templates/repo/hub-python-ci.yml       | UPDATE - simple 5-line caller                                                 |
 | templates/repo/hub-java-ci.yml         | UPDATE - simple 5-line caller                                                 |
 | templates/repo/.ci-hub.yml             | UPDATE - new format example                                                   |
 | tests/test_contract_consistency.py     | UPDATE - remove threshold_overrides_yaml from WORKFLOW_ONLY_INPUTS            |
 | tests/test_config_pipeline.py          | UPDATE - adapt to new flow                                                    |
 | scripts/load_config.py                 | UPDATE - remove threshold_overrides_yaml output if present                    |

 NOT modified in Phase A:
 - cihub/cli.py - CLI uses templates, so updating templates = CLI "just works"
 - Schema files - shorthand booleans deferred to Phase B

 workflow-generator/ Structure (Full GUI App)

 workflow-generator/
 ├── main.py                    # Entry point
 ├── requirements.txt           # PyQt6, PyYAML, PyGithub, GitPython
 ├── pyproject.toml
 ├── src/
 │   ├── __init__.py
 │   ├── app.py                 # QApplication setup
 │   ├── windows/
 │   │   ├── main_window.py     # Main window with tabs
 │   │   ├── onboard_dialog.py  # New repo onboarding wizard
 │   │   └── secrets_dialog.py  # Secret setup dialog
 │   ├── widgets/
 │   │   ├── repo_list.py       # Left sidebar repo tree
 │   │   ├── repo_editor.py     # Right side editor panel
 │   │   ├── tool_toggles.py    # Checkboxes for tools
 │   │   ├── threshold_form.py  # Spinboxes for thresholds
 │   │   └── pom_editor.py      # POM plugin manager
 │   ├── services/
 │   │   ├── config_manager.py  # Load/save configs
 │   │   ├── github_api.py      # GitHub API integration
 │   │   ├── git_ops.py         # Git clone/push operations
 │   │   └── validator.py       # Config validation
 │   ├── generator/
 │   │   ├── yaml_writer.py     # Generate YAML files
 │   │   └── workflow_writer.py # Generate workflow files
 │   └── models/
 │       ├── config.py          # Config dataclasses
 │       └── repo.py            # Repo model
 ├── resources/
 │   ├── icons/
 │   └── styles.qss
 └── tests/

 ---
 Audit Summary

 Existing CLI Structure (cihub)

 Location: /Users/jguida941/new_github_projects/hub-release/cihub/

 Commands (11 total):
 - detect - Auto-detect language (java/python) from repo
 - init - Generate .ci-hub.yml + caller workflow in target repo
 - new - Create hub-side config (config/repos/<name>.yaml)
 - update - Refresh existing configs
 - validate - Validate config against JSON schema
 - config - Manage configs (edit/show/set/enable/disable)
 - fix-pom / fix-deps - Fix Maven configs
 - setup-secrets / setup-nvd - Configure secrets
 - sync-templates - Push workflows to repos

 Reusable Components (GUI-friendly):

 | Component                | Location               | Purpose                |
 |--------------------------|------------------------|------------------------|
 | PathConfig               | cihub/config/paths.py  | Path management        |
 | load_defaults()          | cihub/config/io.py     | Load defaults.yaml     |
 | load_repo_config()       | cihub/config/io.py     | Load repo config       |
 | deep_merge()             | cihub/config/merge.py  | Merge config layers    |
 | validate_config()        | cihub/config/schema.py | JSON schema validation |
 | build_repo_config()      | cihub/cli.py:648       | Generate config dict   |
 | render_caller_workflow() | cihub/cli.py:679       | Generate workflow YAML |
 | CommandResult            | cihub/cli.py:44        | Structured output      |

 Existing Wizard System:
 - Location: cihub/wizard/
 - Uses questionary + rich for terminal prompts
 - Already has: WizardRunner, language selection, tool configuration
 - Could be replaced with PyQt6 equivalents

 Config Structure

 3-Layer Hierarchy:
 1. config/defaults.yaml - Global defaults
 2. templates/profiles/*.yaml - 12 profiles (java/python x fast/quality/security/etc.)
 3. config/repos/<repo>.yaml - Per-repo overrides

 Tools Available:
 - Java (11): jacoco, checkstyle, spotbugs, pmd, owasp, pitest, jqwik, semgrep, trivy, codeql, docker
 - Python (11): pytest, ruff, bandit, pip-audit, black, isort, mypy, mutmut, hypothesis, semgrep, trivy, codeql, docker

 Config Format (simple booleans + thresholds):
 language: python
 version: "3.12"
 python:
   tools:
     pytest:
       enabled: true
       min_coverage: 80
     ruff:
       enabled: true
     mypy:
       enabled: false

 ---
 PyQt6 GUI Plan

 Decisions Made

 - Location: New subdirectory workflow-generator/ inside hub-release (isolated, doesn't affect existing code)
 - Goal: Full feature parity with CLI (built incrementally)
 - Distribution: Standalone executable (.app/.exe via PyInstaller)
 - Later: Can be moved to its own repo once working

 ---
 Incremental Build Plan

 Phase 1: Foundation + Proof of Concept

 Goal: Basic window that generates valid YAML

 New repo structure:
 cihub-desktop/
 ├── main.py                    # Entry point
 ├── requirements.txt           # PyQt6, PyYAML, PyInstaller
 ├── pyproject.toml            # Project config
 ├── src/
 │   ├── __init__.py
 │   ├── app.py                # QApplication setup
 │   ├── windows/
 │   │   ├── __init__.py
 │   │   └── main_window.py    # Main QMainWindow
 │   ├── widgets/
 │   │   ├── __init__.py
 │   │   ├── repo_form.py      # Repo settings form
 │   │   ├── tool_toggles.py   # Tool checkboxes
 │   │   └── threshold_form.py # Threshold spinboxes
 │   ├── generator/
 │   │   ├── __init__.py
 │   │   ├── config_builder.py # Build config dict
 │   │   ├── yaml_writer.py    # Generate YAML strings
 │   │   └── workflow_writer.py # Generate workflow files
 │   └── models/
 │       ├── __init__.py
 │       └── config.py         # Config dataclasses
 ├── resources/
 │   ├── icons/
 │   └── styles/
 └── tests/

 Phase 1 Deliverables:
 - Window opens
 - Language dropdown (Python/Java)
 - 5 Python tool checkboxes
 - Generate button → shows YAML in text area
 - Verify YAML is valid

 Phase 2: Full Tool Coverage

 Goal: All tools for both languages

 - All Python tools (11): pytest, ruff, bandit, pip-audit, black, isort, mypy, mutmut, hypothesis, semgrep, trivy, codeql, docker
 - All Java tools (11): jacoco, checkstyle, spotbugs, pmd, owasp, pitest, jqwik, semgrep, trivy, codeql, docker
 - Dynamic form - shows correct tools based on language selection
 - Tool descriptions/tooltips

 Phase 3: Repo Settings

 Goal: Configure repo metadata

 - Owner/Name fields
 - Default branch selector
 - Monorepo checkbox + subdir field
 - Run group selector (full, smoke, fixtures, security, compliance)
 - Execution mode (central vs distributed)

 Phase 4: Thresholds & Profiles

 Goal: Quality gates and quick presets

 - Coverage threshold spinbox (0-100%)
 - Mutation score threshold spinbox
 - Max vulns threshold
 - Profile dropdown (fast, quality, security, minimal, compliance, coverage-gate)
 - Profile applies defaults, user can override

 Phase 5: File Generation & Output

 Goal: Generate all files the CLI does

 - Tabbed output: .ci-hub.yml | workflow | hub config
 - Save to folder button (creates .github/workflows/)
 - Preview before save
 - Syntax highlighting in output

 Phase 6: Java POM Support

 Goal: Maven plugin/dependency management

 - Load existing pom.xml
 - Show missing plugins
 - Generate plugin snippets
 - Generate dependency snippets
 - Merge into pom.xml option

 Phase 7: Load & Edit Existing

 Goal: Edit existing configs

 - Open folder → detect existing .ci-hub.yml
 - Load into form
 - Edit and regenerate
 - Diff view before overwrite

 Phase 8: Standalone Executable

 Goal: Distribute without Python

 - PyInstaller setup
 - macOS .app bundle
 - Windows .exe
 - Linux AppImage
 - GitHub releases with binaries

 ---
 UI Layout (Final Vision)

 ┌─────────────────────────────────────────────────────────────────┐
 │  CI/CD Hub - Config Generator                          [_][□][X]│
 ├─────────────────────────────────────────────────────────────────┤
 │  ┌─────────────────────────────────────────────────────────────┐│
 │  │ REPO SETTINGS                                               ││
 │  │ Owner: [____________]  Name: [____________]                 ││
 │  │ Branch: [main     ▼]   Language: [Python ▼]                 ││
 │  │ [ ] Monorepo   Subdir: [____________]                       ││
 │  │ Run Group: [full ▼]    Mode: [Central ▼]                    ││
 │  └─────────────────────────────────────────────────────────────┘│
 │  ┌─────────────────────────────────────────────────────────────┐│
 │  │ TOOLS                          Profile: [quality ▼]         ││
 │  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             ││
 │  │ │ [x] pytest  │ │ [x] ruff    │ │ [x] bandit  │             ││
 │  │ │ [x] black   │ │ [x] isort   │ │ [ ] mypy    │             ││
 │  │ │ [ ] mutmut  │ │ [ ] semgrep │ │ [ ] trivy   │             ││
 │  │ └─────────────┘ └─────────────┘ └─────────────┘             ││
 │  └─────────────────────────────────────────────────────────────┘│
 │  ┌─────────────────────────────────────────────────────────────┐│
 │  │ THRESHOLDS                                                  ││
 │  │ Min Coverage: [80]%  Min Mutation: [70]%  Max Vulns: [0]    ││
 │  └─────────────────────────────────────────────────────────────┘│
 │  ┌─────────────────────────────────────────────────────────────┐│
 │  │ [.ci-hub.yml] [workflow] [hub config]                       ││
 │  │ ┌───────────────────────────────────────────────────────┐   ││
 │  │ │ language: python                                      │   ││
 │  │ │ version: "3.12"                                       │   ││
 │  │ │ python:                                               │   ││
 │  │ │   tools:                                              │   ││
 │  │ │     pytest:                                           │   ││
 │  │ │       enabled: true                                   │   ││
 │  │ │       min_coverage: 80                                │   ││
 │  │ └───────────────────────────────────────────────────────┘   ││
 │  └─────────────────────────────────────────────────────────────┘│
 │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
 │  │  Generate   │  │ Save Files  │  │ Open Folder │              │
 │  └─────────────┘  └─────────────┘  └─────────────┘              │
 └─────────────────────────────────────────────────────────────────┘

 ---
 Phase 1 Implementation Steps

 1. Create subdirectory in hub-release:
 cd /Users/jguida941/new_github_projects/hub-release
 mkdir -p workflow-generator
 cd workflow-generator
 2. Set up project structure:
 python3 -m venv .venv
 source .venv/bin/activate
 pip install PyQt6 PyYAML
 3. Create file structure:
 workflow-generator/
 ├── main.py              # Entry point
 ├── requirements.txt     # PyQt6, PyYAML
 ├── src/
 │   ├── __init__.py
 │   ├── main_window.py   # Main QMainWindow
 │   └── generator.py     # YAML generation
 └── .gitignore           # Ignore .venv
 4. Build MainWindow with:
   - Language dropdown (Python/Java)
   - 5 checkboxes: pytest, ruff, bandit, black, mypy
   - Generate button
   - QTextEdit output area
 5. Create generator.py:
   - Takes dict of form values
   - Returns valid .ci-hub.yml string
 6. Test: Run python main.py, click generate, verify valid YAML
 7. Add to .gitignore (optional - can exclude from hub-release commits initially)

 ---
 Critical Files to Reference (from hub-release)

 | File                                   | Purpose                           |
 |----------------------------------------|-----------------------------------|
 | config/defaults.yaml                   | Default tool settings & structure |
 | schema/ci-hub-config.schema.json       | Valid config structure            |
 | templates/repo/hub-python-ci.yml       | Workflow template format          |
 | templates/repo/hub-java-ci.yml         | Java workflow template            |
 | templates/profiles/python-quality.yaml | Profile example                   |
 | cihub/config/merge.py                  | Deep merge logic to copy          |
 | cihub/cli.py:648                       | build_repo_config() function      |
 | cihub/cli.py:679                       | render_caller_workflow() function |

 ---
 Next Steps After Phase 1

 Once basic POC works:
 1. Add all Python tools (Phase 2)
 2. Add all Java tools (Phase 2)
 3. Add repo settings form (Phase 3)
 4. Continue through phases...
