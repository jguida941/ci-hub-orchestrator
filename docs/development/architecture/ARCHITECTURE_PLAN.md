# CI-CD Hub - Complete Architecture Plan

> **Status:** Proposed  
> **Date:** 2025-12-24  
> **Author:** Justin Guida  

## Product Intent

This is a production-grade system intended for commercial use. Prioritize safety, scalability, maintainability, SDLC best practices, and thorough testing (including mutation testing when practical). Do not cut corners for speed.

## MVP Acceptance Checklist

- Hub production CI is green and enforces strict gates (actionlint, zizmor, lint, mypy, yamllint, tests, mutation).
- All GitHub Actions are pinned to commit SHAs.
- Mutation testing meets the defined threshold for `cihub/`.
- Config schema/docs/defaults are aligned for `use_central_runner` and `repo_side_execution`.
- `_quarantine/` content is excluded from linting/formatting gates.
- Reusable workflows always generate and upload `report.json` artifacts (use `if: always()`) so aggregation never shows `-`.
- `hub-orchestrator.yml` and `hub-security.yml` failures are resolved (blockers cleared).
- Hub production CI summary lists every check with pass/fail/skip status and a failed/skipped table.
- Aggregation summaries include failure reasons when jobs fail (no silent `-` without context).

## Reusable Workflow Migration Summary

The hub migrates from per-repo dispatch templates to reusable workflows to prevent drift
and keep reporting consistent. The CLI (`cihub`) generates minimal caller workflows and
hub-side configs only.

Key constraints:
- GitHub `workflow_dispatch` inputs are limited to 25 (see ADR-0024).
- Caller templates are intentionally minimal; reusable workflows remain the source of truth.

Historical execution details are archived in:
`docs/development/architecture/ARCHITECTURE_PLAN.md`.


  # MVP/Phase‑0 (hub‑side only) 12/24/2025

  ## Rules

- Two booleans are distinct: use_central_runner (central vs distributed) and
  repo_side_execution (opt‑in repo writes).
  - Non‑goal: no repo writes unless repo_side_execution is true.
  - After this plan: proceed to the full NEW_PLAN phases in order.

  For each step, use the Execution Checklist to record completion with date, proof,
  and results.

# Execution Checklist (for completion)
 - [ ] Check off each item only after you record the date, proof, and results.

• MVP/Phase‑0 Checklist (Hub‑Side Only)

  - [x] Confirm defaults: use_central_runner: true, repo_side_execution: false (2025-12-25)
  - [x] Update schema: add use_central_runner in schema/ci-hub-config.schema.json (2025-12-25)
  - [x] Update schema: add repo_side_execution in schema/ci-hub-config.schema.json (2025-12-25)
  - [x] Update defaults: add use_central_runner in config/defaults.yaml (2025-12-25)
  - [x] Update defaults: add repo_side_execution in config/defaults.yaml (2025-12-25)
  - [x] Update docs: add use_central_runner in docs/reference/CONFIG_REFERENCE.md (2025-12-25)
  - [x] Update docs: add repo_side_execution in docs/reference/CONFIG_REFERENCE.md (2025-12-25)
  - [x] ADR‑0025 created (modular CLI + wizard, hub‑side only) (2025-12-25)
  - [x] ADR‑0026 placeholder (repo-side execution guardrails) (2025-12-25)
  - [x] Optional deps added: questionary, rich under [project.optional-dependencies].wizard (2025-12-25)

  Phase 2 – Config Module

  - [x] Extract YAML I/O to cihub/config/io.py (2025-12-25)
  - [x] Move deep merge to cihub/config/merge.py (2025-12-25)
  - [x] Add schema loader/validator in cihub/config/schema.py (2025-12-25)
  - [x] Wire config module to existing CLI paths (2025-12-25)

  Phase 3 – Wizard Module

  - [x] wizard/styles.py + wizard/validators.py (2025-12-25)
  - [x] wizard/core.py with run_new/init/config (2025-12-25)
  - [x] wizard/summary.py (2025-12-25)
  - [x] Question modules for language/tools/security/thresholds (2025-12-25)
  - [x] Graceful fallback when deps missing (2025-12-25)

  Phase 4 – Commands Refactor

  - [x] Extract existing command handlers into cihub/commands/* (2025-12-25)
  - [x] Add --wizard path for init (2025-12-25)

  Phase 5 – New Commands

  - [x] cihub new (hub‑side only) (2025-12-25)
  - [x] cihub config (edit/show/set/enable/disable) (2025-12-25)
  - [x] CLI wiring for new subcommands (2025-12-25)

  Guardrails

  - [ ] repo_side_execution remains OFF by default
  - [ ] No repo writes unless repo_side_execution: true (future ADR‑0026)

  If you want, I can turn this into a markdown checklist in docs/development/
  ARCHITECTURE_PLAN.md or docs/development/status/STATUS.md.



 Plan: CLI Modular Restructure with Interactive Wizard

 Context

 The current cihub/cli.py is a 1,688-line monolithic file with 8 commands.
 ARCHITECTURE_PLAN.md defines a comprehensive modular architecture. The user wants to:

 1. Restructure CLI to match ARCHITECTURE_PLAN.md architecture (MVP subset)
 2. Add interactive wizard for cihub new, cihub init, cihub config
 3. Create ADR-0025 documenting this decision
 4. Use questionary + Rich for interactive prompts (soft/optional deps)

 Key Constraints (from code review)

 "Target repos stay clean" - Core principle. Hub-side config only.

 Execution Modes (Existing Architecture)

 The hub already has 2 modes - wizard configures which one to use:

 | Mode        | How it works                                       | Controlled by
              |
 |-------------|----------------------------------------------------|--------------
 -------------|
 | Central     | hub-run-all.yml runs in hub, clones repo, executes |
 use_central_runner: true  |
 | Distributed | hub dispatches to target repo's caller workflow    |
 use_central_runner: false |

 The wizard does NOT create a 3rd mode. It only configures config/repos/*.yaml.

 ESSENTIAL: Two Separate Booleans

 | Boolean             | Purpose                                      | Default |
 |---------------------|----------------------------------------------|---------|
 | use_central_runner  | Switch between central vs distributed        | true    |
 | repo_side_execution | Enable workflow generation INTO target repos | false   |

 Both must be:
 1. Added to schema (schema/ci-hub-config.schema.json)
 2. Added to defaults.yaml (config/defaults.yaml) with defaults
 3. Documented in docs/reference/CONFIG_REFERENCE.md
 4. Wired into wizard - ask user which mode to use
 5. Wired into config commands - cihub config set ...

 repo_side_execution Guardrails

 Default OFF - No writes to target repos unless explicitly enabled.

 1. Default off: repo_side_execution: false by default
 2. Explicit command: cihub generate-workflow --repo <name> only runs when flag is
 true
 3. Dry-run first: --dry-run is default, must explicitly use --apply
 4. Manifest tracking: Hash of generated workflow stored for drift detection
 5. No writes on failure: If validation fails, abort (no partial writes)
 6. Backup before write: Always save .bak before overwriting
 7. Requires ADR: Document this as ADR-0026

 # In config/repos/<repo>.yaml
 repo:
   owner: jguida941
   name: my-repo
   use_central_runner: true      # Central vs distributed toggle
   repo_side_execution: false    # Opt-in to workflow generation (OFF by default)

 Hard Rules

 - Hub-side only: Write to config/repos/*.yaml only
 - No writing to target repos: Don't create .github/workflows/ in target repos
 (that's a separate opt-in feature requiring its own ADR)
 - POM edits are opt-in: Separate phase with dedicated ADR (not in MVP)
 - Soft dependencies: questionary/rich optional for non-interactive use
 - Minimal command set: Only new, init, config, validate in MVP
 - New commands only: Add flags to new commands, not existing ones

 Current State

 - cihub/cli.py - 1,688 lines, all logic in one file
 - cihub/config/paths.py - PathConfig class exists
 - cihub/commands/ - exists but empty
 - cihub/wizard/ - exists but empty
 - 12 profiles in templates/profiles/ (6 Java, 6 Python)
 - scripts/apply_profile.py - deep merge logic exists
 - Existing ADRs in docs/adr/ (verify count before creating ADR-0025)

 Architecture Decisions

 Library Choice: questionary + Rich

 - questionary: Interactive prompts (maintained, cross-platform)
 - Rich: Pretty output (panels, tables, progress)
 - Centralized theme in wizard/styles.py
 - Separation: Rich for output, questionary for input

 Module Structure (from ARCHITECTURE_PLAN.md)

 cihub/
 ├── cli.py                    # Entry point + argparse
 ├── config/                   # Config management
 │   ├── io.py                 # YAML I/O
 │   ├── merge.py              # Deep merge
 │   ├── schema.py             # JSON schema validation
 │   └── paths.py              # PathConfig (exists)
 ├── commands/                 # Command implementations
 │   ├── new.py, init.py, add.py, validate.py, apply.py
 │   ├── pom.py, secrets.py, templates.py
 │   └── config_cmd.py, dispatch.py, registry.py
 ├── wizard/                   # Interactive prompts
 │   ├── core.py               # WizardRunner
 │   ├── styles.py             # Centralized theme
 │   ├── validators.py         # Input validation
 │   ├── summary.py            # Rich summary display
 │   └── questions/            # Per-category questions
 ├── diagnostics/              # Error reporting
 │   ├── models.py, renderer.py
 │   └── collectors/           # yaml, schema, pom validators
 ├── fixers/                   # Auto-fix capabilities
 │   └── base.py, regenerate.py, format.py
 └── runners/                  # External tool execution
     └── base.py, maven.py, yamllint.py

 Checkpoints & Documentation Strategy

 STOP after each phase for user audit. Create ADRs/guides as we go.

 | Phase | Checkpoint                   | Documents Created                  |
 |-------|------------------------------|------------------------------------|
 | 1     | ADR-0025 created, deps added | ADR-0025, pyproject.toml changes   |
 | 2     | Config module working        | docs/guides/CLI_CONFIG.md          |
 | 3     | Wizard module working        | docs/guides/CLI_WIZARD.md          |
 | 4     | Commands extracted           | Update docs/guides/CLI_COMMANDS.md |
 | 5     | New commands added           | Final CLI guide update             |

 Cross-reference to ARCHITECTURE_PLAN.md:
 - This work implements Phase 5: CLI Commands from ARCHITECTURE_PLAN.md
 - Also partially implements Phase 4: Profiles (wizard uses profiles)

 Implementation Phases (MVP: Phases 1-5)

 Scope: MVP first - get wizard working, then iterate. Phases 6-8 deferred.
 Process: STOP after each phase. User audits. Then proceed.

 Phase 1: ADR-0025 + Dependencies

 Files:
 - docs/adr/0025-cli-modular-restructure.md - Document decision (next after 0024)
 - pyproject.toml - add questionary>=2.0.0, rich>=13.0.0 as optional extras

 ADR Content:
 - Decision: Modular CLI with questionary+Rich wizard (hub-side config only)
 - Context: Monolithic cli.py doesn't scale; need interactive onboarding
 - Scope: Hub-side config only (config/repos/*.yaml), NOT target repo workflows
 - Consequences: Better maintainability, testability, user experience
 - Alternatives: Typer/Click (rejected: argparse works); full scaffolding
 (deferred)
 - Soft deps: questionary/rich are extras, graceful fallback for non-interactive

 pyproject.toml changes:
 [project.optional-dependencies]
 wizard = ["questionary>=2.0.0", "rich>=13.0.0"]

 Phase 2: Config Module (Foundation)

 Extract from cli.py to cihub/config/:

 io.py:
 - read_yaml(path) -> dict
 - write_yaml(path, data, dry_run=False)
 - write_text(path, content, dry_run=False)
 - load_defaults(paths: PathConfig) -> dict
 - load_profile(paths: PathConfig, name: str) -> dict
 - load_repo_config(paths: PathConfig, repo: str) -> dict
 - save_repo_config(paths: PathConfig, repo: str, data: dict)
 - list_repos(paths: PathConfig) -> list[str]
 - list_profiles(paths: PathConfig) -> list[str]

 merge.py (from scripts/apply_profile.py):
 - deep_merge(base: dict, overlay: dict) -> dict
 - build_effective_config(defaults, profile, repo_cfg) -> dict

 schema.py:
 - validate_config(config: dict) -> list[str]  # Returns errors
 - get_schema() -> dict  # Load from schema/ci-hub-config.schema.json

 ESSENTIAL - Also update schema:
 - Add use_central_runner: boolean to schema/ci-hub-config.schema.json
 - Add default to config/defaults.yaml: use_central_runner: true (APPROVED -
 central is default)
 - Update docs/reference/CONFIG_REFERENCE.md with documentation

 Phase 3: Wizard Module

 Core files:

 wizard/styles.py:
 - THEME: questionary.Style with consistent colors
 - Colors: SUCCESS, ERROR, WARNING, INFO, PROMPT
 - get_style() -> questionary.Style

 wizard/validators.py:
 - validate_percentage(val: str) -> bool  # 0-100
 - validate_version(val: str) -> bool     # semver-ish
 - validate_package_name(val: str) -> bool
 - validate_repo_name(val: str) -> bool

 wizard/core.py:
 class WizardRunner:
     def __init__(self, console: Console, paths: PathConfig)
     def run_new_wizard(self, name: str, profile: str = None) -> dict
     def run_init_wizard(self, detected: dict) -> dict
     def run_config_wizard(self, existing: dict) -> dict

 wizard/summary.py:
 - print_config_summary(console: Console, config: dict)
 - print_tool_table(console: Console, tools: dict)
 - print_save_confirmation(console: Console, path: str)

 Question modules:
 - questions/language.py: select_language(), select_java_version(),
 select_python_version(), select_build_tool()
 - questions/java_tools.py: configure_java_tools(defaults: dict) -> dict
 - questions/python_tools.py: configure_python_tools(defaults: dict) -> dict
 - questions/security.py: configure_security_tools(language: str) -> dict
 - questions/thresholds.py: configure_thresholds(defaults: dict) -> dict

 Phase 4: Commands Module (Refactor Existing)

 Extract from cli.py - keep same signatures:

 - commands/detect.py: cmd_detect(args) -> int
 - commands/init.py: cmd_init(args) -> int, cmd_update(args) -> int
 - commands/validate.py: cmd_validate(args) -> int
 - commands/pom.py: cmd_fix_pom(args) -> int, cmd_fix_deps(args) -> int
 - commands/secrets.py: cmd_setup_secrets(args) -> int, cmd_setup_nvd(args) -> int
 - commands/templates.py: cmd_sync_templates(args) -> int

 Add wizard integration to init.py:
 if args.wizard:
     from cihub.wizard.core import WizardRunner
     runner = WizardRunner(console, paths)
     config = runner.run_init_wizard(detected_config)

 Phase 5: New Commands + CLI Update

 New command files:

 commands/new.py (hub-side only):
 def cmd_new(args) -> int:
     """Create hub-side config for a new repo.

     Writes to: config/repos/<name>.yaml
     Does NOT write to target repo (hub-side only in MVP).
     """
     # --name (required)
     # --profile security|standard|fast|quality|compliance|minimal
     # --interactive (ask per tool) - requires [wizard] extra
     # --dry-run, --yes (new commands only)

 commands/config_cmd.py:
 def cmd_config(args) -> int:
     """Manage hub-side repo configs.

     All operations on config/repos/*.yaml
     """
     # config (no subcommand) -> wizard (if installed)
     # config edit -> wizard (if installed)
     # config show [--effective] --repo <name>
     # config set <path> <value> --repo <name>
     # config enable <tool> --repo <name>
     # config disable <tool> --repo <name>

 Graceful degradation for wizard deps:
 try:
     from cihub.wizard.core import WizardRunner
     HAS_WIZARD = True
 except ImportError:
     HAS_WIZARD = False

 if args.interactive and not HAS_WIZARD:
     print("Install wizard deps: pip install cihub[wizard]")
     return 1

 Update cli.py:
 - Add new subcommand with argparse
 - Add config subcommand with sub-subparsers
 - Add --wizard flag to init
 - Import handlers from commands/
 - Keep existing commands unchanged (no new flags)

 ---
 DEFERRED (Post-MVP)

 Phase 6: Diagnostics Module

 - diagnostics/models.py: Diagnostic dataclass
 - diagnostics/renderer.py: Pretty console output
 - diagnostics/collectors/: yaml, schema, pom validators

 Phase 7: Fixers + Runners

 - fixers/base.py, fixers/regenerate.py
 - runners/base.py, runners/maven.py

 Phase 8: Full Testing

 - Integration tests
 - Snapshot tests
 - E2E tests

 Critical Files

 | File                                     | Action | Purpose
                        |
 |------------------------------------------|--------|-----------------------------
 -----------------------|
 | docs/adr/0025-cli-modular-restructure.md | Create | Document decision + hub-only
  scope                 |
 | pyproject.toml                           | Modify | Add
 [project.optional-dependencies] wizard = [...] |
 | cihub/config/io.py                       | Create | YAML I/O extracted from
 cli.py                     |
 | cihub/config/merge.py                    | Create | Deep merge from
 scripts/apply_profile.py           |
 | cihub/config/schema.py                   | Create | JSON schema validation
                        |
 | cihub/wizard/__init__.py                 | Create | Graceful import with
 HAS_WIZARD flag               |
 | cihub/wizard/core.py                     | Create | WizardRunner orchestration
                        |
 | cihub/wizard/styles.py                   | Create | Centralized questionary+Rich
  theme                 |
 | cihub/wizard/validators.py               | Create | Input validation functions
                        |
 | cihub/wizard/summary.py                  | Create | Rich config summary display
                        |
 | cihub/wizard/questions/*.py              | Create | Per-category question
 modules                      |
 | cihub/commands/__init__.py               | Create | Command exports
                        |
 | cihub/commands/new.py                    | Create | Hub-side config creation
 (not target repo)         |
 | cihub/commands/config_cmd.py             | Create | Config management
 (show/set/enable/disable)        |
 | cihub/cli.py                             | Modify | Add new/config subcommands,
 import from commands/  |

 Flags for NEW Commands Only (not existing)

 | Flag             | Commands        | Purpose                                 |
 |------------------|-----------------|-----------------------------------------|
 | --dry-run        | new, config set | Preview without changes                 |
 | --yes            | new, config     | Non-interactive mode                    |
 | --profile <name> | new             | Apply preset profile                    |
 | --interactive    | new, init       | Launch wizard (requires [wizard] extra) |
 | --effective      | config show     | Show merged config                      |
 | --repo <name>    | config          | Target specific repo                    |

 Note: Existing commands (detect, init, update, validate, fix-pom, fix-deps, 
 setup-secrets, setup-nvd, sync-templates) keep their existing flags unchanged.

 Exit Codes

 | Code | Meaning                     |
 |------|-----------------------------|
 | 0    | Success                     |
 | 1    | Validation failed (fixable) |
 | 2    | Missing required tools      |
 | 3    | User cancelled              |
 | 4    | Internal error              |

 Backward Compatibility

 - All existing 8 commands continue to work unchanged
 - New commands (new, config, add, apply) are additive
 - Existing flags preserved

 Success Criteria

 1. cihub new myrepo --profile standard creates full project
 2. cihub init --wizard detects and prompts interactively
 3. cihub config edit opens Rich+questionary wizard
 4. cihub config enable jacoco works non-interactively
 5. cihub validate --fast runs offline validation
 6. All 12 profiles work with --profile flag
 7. ADR-0025 documents the decision
 8. Tests pass for all new modules

 Sources

 - https://pypi.org/project/questionary/
 - https://arjancodes.com/blog/rich-python-library-for-interactive-cli-tools/
 - https://brianbraatz.github.io/p/best-python-cli-menu-libraries/

# End of # MVP/Phase‑0 (hub‑side only)



# This is the ARCHITECTURE_PLAN.md file that outlines the complete architecture for 
# the Self-Validating CLI + Central Hub system.
## Executive Summary

This document outlines a comprehensive **Self-Validating CLI + Central Hub** architecture that consolidates all CI/CD tooling into a single, unified system. The CLI becomes the single entry point for project scaffolding, maintenance, validation, and execution.

---

## Current Blockers

> **Fix these before proceeding with later phases.**

| Workflow               | Status  | Notes               |
|------------------------|---------|---------------------|
| `hub-orchestrator.yml` | FAILING | Needs investigation |
| `hub-security.yml`     | FAILING | Needs investigation |
| `hub-run-all.yml`      | PASSING | Central mode works  |

See `_quarantine/` and `docs/development/status/INTEGRATION_STATUS.md` for file graduation tracking.

---

## Core Principles

### Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────┐
│ SOURCE OF TRUTH                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  .ci-hub.yml              ← ONLY human-edited file              │
│                                                                 │
│  .cihub/                  ← CLI metadata (generated)            │
│  └── manifest.json        ← Hashes of all generated files       │
│                                                                 │
│  Everything else          ← Generated, never manually edit      │
│  ├── .github/workflows/ci.yml                                   │
│  ├── pom.xml (owned blocks only)                                │
│  ├── config/checkstyle.xml                                      │
│  └── config/pmd-ruleset.xml                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Rule:** If you allow arbitrary manual edits to generated sections, you will get drift by design.

### Manifest with Hashes (Deterministic Drift Detection)

Every generated file is tracked with a SHA-256 hash:

```json
// .cihub/manifest.json
{
  "schema_version": "1.0",
  "template_version": "1.2.0",
  "cli_version": "0.5.0",
  "generated_at": "2025-12-24T06:00:00Z",
  "source_config": ".ci-hub.yml",
  "source_hash": "sha256:abc123...",
  "generated_files": {
    ".github/workflows/ci.yml": {
      "hash": "sha256:def456...",
      "template": "workflows/java-caller.yml.j2"
    },
    "config/checkstyle.xml": {
      "hash": "sha256:789abc...",
      "template": "config/checkstyle.xml.j2"
    }
  },
  "pom_owned_blocks": {
    "pom.xml": {
      "jacoco_plugin": "sha256:...",
      "pitest_plugin": "sha256:...",
      "checkstyle_plugin": "sha256:..."
    }
  }
}
```

**`cihub verify`** recomputes hashes and fails if outputs differ. No heuristics. No guessing. Just math.

### Validation Modes (Offline vs Online)

```
┌─────────────────────────────────────────────────────────────────┐
│ VALIDATION MODES                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  cihub validate              # defaults to --fast               │
│                                                                 │
│  cihub validate --fast       # OFFLINE (instant)                │
│  ├── yamllint (.ci-hub.yml, workflows)                          │
│  ├── xmllint (pom.xml, config files)                            │
│  ├── schema validation (JSON schemas)                           │
│  ├── actionlint (workflow syntax + semantics)                   │
│  ├── manifest verify (hash comparison)                          │
│  └── consistency check (config ↔ pom ↔ workflow)                │
│                                                                 │
│  cihub validate --full       # ONLINE (slow, needs network)     │
│  ├── All of --fast                                              │
│  ├── mvn validate (resolves plugins/deps)                       │
│  ├── mvn compile (full compilation)                             │
│  ├── NVD database update (OWASP)                                │
│  └── pip-audit DB update (Python)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why?** Developers need fast feedback. `--fast` works on a plane. `--full` runs in CI.

### Drift Detection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ DRIFT DETECTION (Deterministic)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  cihub verify                                                   │
│  ├── 1. Read .cihub/manifest.json                               │
│  ├── 2. Recompute hash of each generated file                   │
│  ├── 3. Compare computed vs stored hash                         │
│  ├── 4. If ANY hash differs:                                    │
│  │      → FAIL with exact file list                             │
│  │      → Show diff of what changed                             │
│  │      → Suggest: cihub update --force                         │
│  └── 5. CI runs this BEFORE tools run                           │
│                                                                 │
│  Example output:                                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ $ cihub verify                                            │  │
│  │ ❌ Drift detected in 2 files:                             │  │
│  │                                                           │  │
│  │   .github/workflows/ci.yml                                │  │
│  │     Expected: sha256:def456...                            │  │
│  │     Actual:   sha256:999888...                            │  │
│  │                                                           │  │
│  │   config/checkstyle.xml                                   │  │
│  │     Expected: sha256:789abc...                            │  │
│  │     Actual:   sha256:111222...                            │  │
│  │                                                           │  │
│  │ Run 'cihub diff' to see changes                           │  │
│  │ Run 'cihub update --force' to regenerate                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Command Separation: new vs init

| Command      | Use Case                 | What It Does                                                                  |
|--------------|--------------------------|-------------------------------------------------------------------------------|
| `cihub new`  | New project from scratch | Full scaffolding: parent/child POMs, folder structure, all configs            |
| `cihub init` | Existing project         | Patches owned blocks in existing pom.xml, adds workflow + .ci-hub.yml         |
| `cihub add`  | Add tool to project      | Updates .ci-hub.yml, then regenerates outputs (never hand-edits random files) |

### Design Decisions (Locked)

| Decision             | Choice                   | Rationale                                                 |
|----------------------|--------------------------|-----------------------------------------------------------|
| POM owned block      | `<profile id="cihub">`   | Clean separation, easy to replace, no collision           |
| Auto-validate timing | After generation only    | No file watchers, explicit `cihub validate` for on-demand |
| User overlays        | Limited in v1            | `*-custom.xml` files imported by generated, user-owned    |
| Manifest write       | Refuse if validate fails | Hard safety - no dirty states                             |
| Editor integration   | VS Code first            | `code -g file:line:col`, fallback to `open`/`xdg-open`    |
| Java full validation | `mvn validate` only      | `mvn test` requires explicit `--full --test`              |

---

## Diagnostics & Developer Experience

### Rich Diagnostics Model

Every command returns structured diagnostics (not raw strings):

```python
@dataclass
class Diagnostic:
    severity: Literal["error", "warning", "info"]
    code: str           # Stable ID: "CIHUB-POM-001", "CIHUB-SCHEMA-003"
    message: str        # Short: "Missing required field"
    details: str        # Long explanation
    file: Path          # /path/to/.ci-hub.yml
    line: int           # 42
    column: int         # 15
    suggestion: str     # "Add 'language: java' to config"
    fix_id: str | None  # "add-language-field" (if auto-fixable)
```

### CLI Output Format

```
$ cihub validate

  2 errors, 1 warning

ERROR [CIHUB-SCHEMA-001] .ci-hub.yml:15:3
  Missing required field 'language'

  14 │ java:
  15 │   tools:
     │   ^
  16 │     jacoco:

  Suggestion: Add 'language: java' at root level
  Fix: cihub fix --apply CIHUB-SCHEMA-001

ERROR [CIHUB-POM-002] pom.xml:87:12
  JaCoCo plugin version mismatch
  Expected: 0.8.11, Found: 0.8.8

  Fix: cihub fix --apply CIHUB-POM-002

WARNING [CIHUB-MANIFEST-001] .cihub/manifest.json
  Manifest out of date (template v1.1.0 → v1.2.0 available)

  Fix: cihub update

Run 'cihub fix --all' to apply all safe fixes
Run 'cihub fix --diff' to preview changes
```

### Editor Integration

```bash
# Print errors in editor-compatible format
cihub validate --format=editor
# Output: .ci-hub.yml:15:3: error: Missing required field 'language' [CIHUB-SCHEMA-001]

# Open file at error location
cihub doctor --open CIHUB-SCHEMA-001
# Runs: code -g .ci-hub.yml:15:3

# Supported editors (auto-detected or via CIHUB_EDITOR):
# - VS Code: code -g file:line:col
# - IntelliJ: idea --line line file
# - Vim: vim +line file
# - Fallback: open (macOS) / xdg-open (Linux)
```

### Auto-Fix Framework

```bash
cihub fix                    # Interactive: show fixes, ask to apply
cihub fix --diff             # Preview all fixes as unified diff
cihub fix --all              # Apply all safe fixes
cihub fix --apply CODE       # Apply specific fix by diagnostic code
```

**Auto-fixers must be:**
- Idempotent (running twice = same result)
- Bounded to owned files/blocks only
- Previewable (`--diff`)
- Safe (never touch user-owned sections)

**Safe auto-fixes:**
| Fix | What It Does |
|-----|--------------|
| Regenerate workflow | Re-render from template |
| Regenerate owned POM block | Re-render `<profile id="cihub">` |
| Update manifest | Recompute hashes |
| Format YAML | Consistent indentation |
| Add missing schema fields | Insert defaults |

### Generation Safety

```
cihub new / init / add / update
    │
    ├── Generate files
    │
    ├── Run validate --fast
    │       │
    │       ├── PASS → Write manifest → Done ✓
    │       │
    │       └── FAIL → Rollback changes → Show diagnostics → Exit 1
    │
    └── Manifest NEVER written if validation fails
```

**Rule:** The CLI refuses to write `.cihub/manifest.json` unless `validate --fast` passes. No dirty states. No "it generated but it's broken."

### CLI Package Structure

```
cihub/
├── diagnostics/
│   ├── models.py           # Diagnostic dataclass
│   ├── renderer.py         # Pretty console output with snippets
│   ├── formatters/
│   │   ├── console.py      # Rich colored output
│   │   ├── editor.py       # file:line:col format
│   │   └── json.py         # Machine-readable
│   └── collectors/
│       ├── yaml.py         # yamllint wrapper
│       ├── schema.py       # JSON schema validation
│       ├── actionlint.py   # GitHub Actions validation
│       ├── pom.py          # Maven POM validation
│       ├── manifest.py     # Hash verification
│       └── report.py       # CI report validation
│
├── fixers/
│   ├── base.py             # Fixer interface
│   ├── regenerate.py       # Re-render from templates
│   ├── format.py           # YAML/XML formatting
│   └── schema.py           # Add missing fields
│
├── runners/
│   ├── base.py             # External command wrapper
│   ├── maven.py            # mvn validate/compile/test
│   ├── yamllint.py         # yamllint runner
│   └── actionlint.py       # actionlint runner
│
└── editors/
    ├── detector.py         # Detect installed editors
    └── opener.py           # Open file at line:col
```

### Optional TUI (Future)

```bash
cihub ui                    # Launch terminal UI
```

```
┌─ Diagnostics ─────────────────────┬─ Preview ──────────────────────────┐
│                                   │                                    │
│ ERROR CIHUB-SCHEMA-001            │  14 │ java:                        │
│    .ci-hub.yml:15:3               │  15 │   tools:                     │
│    Missing 'language' field       │     │   ^                          │
│                                   │  16 │     jacoco:                  │
│ ERRPR CIHUB-POM-002                  │                                 │
│    pom.xml:87:12                  │  + language: java                  │
│    Version mismatch               │                                    │
│                                   │                                    │
│ ⚠️  CIHUB-MANIFEST-001            │                                    │
│    Template update available      │                                    │
│                                   │                                    │
├───────────────────────────────────┴────────────────────────────────────┤
│ [f] Fix selected  [F] Fix all  [r] Revalidate  [q] Quit                │
└────────────────────────────────────────────────────────────────────────┘
```

**Built with:** [Textual](https://textual.textualize.io/) or [Rich](https://rich.readthedocs.io/)

**Rule:** TUI is optional. CLI works fully without it. `cihub ui` is a nice-to-have, not a requirement.

---

## "All Green" Execution Model

### Validation Tiers (Cumulative)

Tiers are cumulative, not exclusive. Higher tiers include all lower tiers.

```bash
cihub apply                    # Default: --fast only
cihub apply --build            # --fast + compile
cihub apply --test             # --fast + compile + tests
```

| Tier               | What Runs                                              | Time  | Network |
|--------------------|--------------------------------------------------------|-------|---------|
| `--fast` (default) | Schema, actionlint, yamllint, xmllint, manifest verify | ~2s   | No      |
| `--build`          | + `mvn compile` / `pip install` / `npm install`        | ~30s  | Yes     |
| `--test`           | + `mvn test` / `pytest` / `npm test`                   | ~2min | Yes     |

**Rules:**
- `cihub apply` NEVER silently escalates tiers
- `--build` and `--test` must be explicit flags
- CI chooses its own tier (usually `--test`)
- Local dev defaults to `--fast` for speed

### Pre-flight Check

Before doing anything, validate the environment:

```
$ cihub apply

   Pre-flight check...
   ✓ Java 21.0.1 (required: 17+)
   ✓ Maven 3.9.6 (required: 3.8+)
   ✓ actionlint 1.6.26 (required: 1.6+)
   ✓ yamllint 1.33.0 (required: 1.28+)
   ⚠ NVD API key not configured (OWASP will use rate-limited API)

All required tools available.
Continue? [Y/n]
```

**Pre-flight rules:**
- Detect once per run, cache in memory
- Don't re-run `mvn -v` or `java -version` repeatedly
- Version-aware detection (not just "is it installed")
- Show warnings for optional tools, errors for required

### Tool Detection (Never Auto-Install)

```
$ cihub apply

ERROR Missing required tools:

  Tool         Required    Found      Install Command
  ────────────────────────────────────────────────────────
  Maven        3.8+        not found  brew install maven
  actionlint   1.6+        1.5.0      brew upgrade actionlint

Run the install commands above, then retry.

Or skip missing tools:
  cihub apply --skip-tools maven,actionlint
```

**Why no auto-install:**
- Security risk (running arbitrary install scripts)
- Different package managers (brew, apt, choco, asdf, sdkman)
- Version pinning is user's responsibility
- Corporate environments block installs

### Skip Flags

For environments where some tools aren't available:

```bash
cihub apply --skip-tools maven      # Skip mvn validate/compile/test
cihub apply --skip-tools owasp      # Skip NVD-dependent checks
cihub apply --skip-full             # Only run --fast, never escalate
cihub apply --no-preflight          # Skip pre-flight (power users, discouraged)
cihub apply --yes                   # Non-interactive, assume yes
```

### Auto-Commit (Opt-in Only)

```bash
cihub apply                     # No commit (default)
cihub apply --commit            # Commit if green
cihub apply --commit --push     # Commit + push if green
cihub apply --commit -m "msg"   # Custom commit message
```

**Default commit message:**
```
chore(cihub): initialize CI/CD configuration

Generated by cihub v0.5.0
Profile: standard
Tools: jacoco, pitest, checkstyle, owasp
Template: v1.2.0
```

**Safety rules:**
- Never commit if validation fails
- Never auto-push without explicit `--push`
- Show what will be committed first (like `git status`)
- Respect `.gitignore`

**Manifest metadata on commit:**
```json
{
  "applied_at": "2025-12-24T06:30:00Z",
  "applied_by": "jguida",
  "apply_mode": "fast",
  "apply_tier": "fast|build|test",
  "commit_sha": "abc123..."
}
```

### JSON Output Mode

For scripting, IDE plugins, and CI integration:

```bash
cihub apply --json
```

```json
{
  "status": "success",
  "tier": "fast",
  "duration_ms": 1842,
  "diagnostics": [],
  "files_generated": [
    ".ci-hub.yml",
    ".github/workflows/ci.yml",
    ".cihub/manifest.json"
  ],
  "files_modified": [
    "pom.xml"
  ],
  "tools_detected": {
    "java": {"version": "21.0.1", "path": "/usr/bin/java"},
    "maven": {"version": "3.9.6", "path": "/usr/local/bin/mvn"}
  }
}
```

```bash
# Example: scripting usage
if cihub apply --json | jq -e '.status == "success"'; then
  echo "Ready to commit"
fi
```

### Exit Codes

For scripting and CI integration:

| Code | Meaning                     | Action                        |
|------|-----------------------------|-------------------------------|
| 0    | All green                   | Continue                      |
| 1    | Validation failed (fixable) | Run `cihub fix` or manual fix |
| 2    | Missing required tools      | Install tools, retry          |
| 3    | User cancelled              | N/A                           |
| 4    | Internal error / crash      | Report bug                    |

**Rules:**
- Exit 1 = fixable config/validation issues
- Exit 4 = actual bugs in cihub itself (should never happen)

### Bulk Updates (sync-templates)

```bash
cihub sync-templates                    # Default: --fast only
cihub sync-templates --build            # Also run compile
cihub sync-templates --dry-run          # Preview only
cihub sync-templates --create-prs       # Open PRs instead of direct push
```

**Default tier for bulk: `--fast` only**

Why:
- Don't block mass updates on one repo's build failure
- CI proves build/test after PR is opened
- Fast feedback on template compatibility

**Recommended flow:**
1. `cihub sync-templates --dry-run` → see what would change
2. `cihub sync-templates --create-prs` → open PRs
3. CI runs `--test` tier on each PR
4. Merge when green

---

## Tool Registry (Pinned Versions)

### Why Not "Latest"

**NEVER use "latest" at runtime.** This breaks:
- Reproducibility (builds differ between runs)
- Debugging (which version caused the bug?)
- Security audits (can't prove what ran)
- Caching (can't cache unpredictable versions)

### Registry Format

```yaml
# hub-release/registry/tools.yaml
schema_version: "1.0"
updated_at: "2025-12-24"

java:
  maven_compiler_plugin: "3.12.1"
  jacoco_maven_plugin: "0.8.11"
  pitest_maven_plugin: "1.15.3"
  maven_checkstyle_plugin: "3.3.1"
  checkstyle: "10.12.5"
  maven_pmd_plugin: "3.21.2"
  pmd: "6.55.0"
  spotbugs_maven_plugin: "4.8.3.0"
  spotbugs: "4.8.3"
  owasp_dependency_check: "9.0.7"
  maven_surefire_plugin: "3.2.3"

python:
  pytest: "7.4.3"
  pytest_cov: "4.1.0"
  ruff: "0.1.8"
  black: "23.12.1"
  isort: "5.13.2"
  mypy: "1.7.1"
  bandit: "1.7.6"
  pip_audit: "2.6.1"
  mutmut: "2.4.4"

node:
  eslint: "8.56.0"
  prettier: "3.1.1"
  jest: "29.7.0"
  typescript: "5.3.3"

security:
  semgrep: "1.52.0"
  trivy: "0.48.0"
  codeql: "2.15.4"

# Hub workflow version (for caller workflow pinning)
hub_workflow_version: "v1.3.0"
```

### How Templates Use Registry

Templates reference registry versions, never hardcoded:

```xml
<!-- templates/pom/plugins/jacoco.xml.j2 -->
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>{{ registry.java.jacoco_maven_plugin }}</version>
  ...
</plugin>
```

```yaml
# templates/workflows/java-caller.yml.j2
jobs:
  ci:
    uses: {{ hub_org }}/ci-cd-hub/.github/workflows/java-ci.yml@{{ registry.hub_workflow_version }}
```

### Registry Update Commands

```bash
# Manual: edit registry/tools.yaml, commit, push
vim registry/tools.yaml && git commit -am "chore: bump spotbugs to 4.8.4"

# Semi-auto: query Maven Central/PyPI for updates
cihub registry check              # Show available updates
cihub registry bump spotbugs      # Bump specific tool
cihub registry bump --all         # Bump all to latest stable
cihub registry bump --pr          # Create PR with all bumps
```

**Registry bump output:**
```
$ cihub registry check

Available updates:

  Tool                    Current   Latest    Breaking?
  ─────────────────────────────────────────────────────
  jacoco_maven_plugin     0.8.11    0.8.12    No
  spotbugs_maven_plugin   4.8.3.0   4.8.4.0   No
  owasp_dependency_check  9.0.7     10.0.0    YES (major)

Run 'cihub registry bump --all --pr' to create update PR
```

---

## Managed Repos Inventory

### Registry Format

```yaml
# hub-release/config/repos.yaml
schema_version: "1.0"

repos:
  - name: contact-suite-spring-react
    owner: jguida941
    language: java
    build_tool: maven
    branch: main
    profile: standard
    hub_workflow_version: v1.3.0
    enabled: true

  - name: ci-cd-bst-demo-github-actions
    owner: jguida941
    language: python
    build_tool: pip
    branch: main
    profile: security
    hub_workflow_version: v1.3.0
    enabled: true

  - name: legacy-app
    owner: jguida941
    language: java
    build_tool: maven
    branch: develop
    profile: fast
    hub_workflow_version: v1.2.0  # Pinned to older version
    enabled: true

  - name: archived-repo
    owner: jguida941
    enabled: false  # Skip in bulk updates
```

### Repo Groups

```yaml
# hub-release/config/groups.yaml
groups:
  pilot:
    - contact-suite-spring-react
    - ci-cd-bst-demo-github-actions

  core:
    - legacy-app
    - another-critical-repo

  all:
    - "*"  # All enabled repos
```

```bash
cihub sync-templates --group pilot     # Update pilot repos only
cihub sync-templates --group core      # Update core repos
cihub sync-templates --all             # Update all enabled repos
```

---

## Bulk Update Strategy

### Design Decisions

| Decision           | Choice                            | Rationale                                 |
|--------------------|-----------------------------------|-------------------------------------------|
| Update strategy    | Tiny caller pinned to hub version | Simpler, less drift, scales best          |
| Auth mechanism     | `gh` CLI                          | Reliable, reduces code, already installed |
| Execution location | Both local + GitHub Action        | Local for dev, Action for production      |
| Default tier       | `--fast` only                     | Let CI prove full build after PR opened   |
| PR creation        | Always (not direct push)          | Safe, reviewable, rollback-friendly       |

### How Bulk Update Works

```
cihub sync-templates --create-prs
    │
    ├── 1. Read registry/tools.yaml (pinned versions)
    ├── 2. Read config/repos.yaml (managed repos)
    │
    ├── For each enabled repo:
    │   ├── Clone to temp dir
    │   ├── Read .ci-hub.yml + repo overrides
    │   ├── Regenerate all owned outputs:
    │   │   ├── .github/workflows/ci.yml (pinned to hub_workflow_version)
    │   │   ├── <profile id="cihub"> in pom.xml
    │   │   ├── config/*.xml files
    │   │   └── .cihub/manifest.json
    │   ├── Run validate --fast
    │   ├── If green:
    │   │   ├── Create branch: cihub/bump-v1.3.0
    │   │   ├── Commit with standard message
    │   │   └── Open PR via `gh pr create`
    │   └── If red:
    │       └── Log error, continue to next repo
    │
    └── Summary: "12/15 PRs created, 3 failed (see errors above)"
```

### The "No Hand-Editing" Guarantee

**You do NOT update repos by editing random files.**

You update repos by:
1. Bumping versions in ONE place (hub registry)
2. Re-rendering generated outputs for each repo
3. Recomputing manifest hashes
4. Running validation
5. Opening PRs

**Result:** Deterministic, reproducible, auditable.

### Staged Rollout

```bash
# Stage 1: Pilot repos (5 repos)
cihub sync-templates --group pilot --create-prs

# Stage 2: Core repos (after pilot is green)
cihub sync-templates --group core --create-prs

# Stage 3: All remaining
cihub sync-templates --all --create-prs
```

### GitHub Action for Production

```yaml
# .github/workflows/sync-all-repos.yml
name: Sync All Managed Repos

on:
  workflow_dispatch:
    inputs:
      group:
        description: 'Repo group to sync'
        default: 'pilot'
        type: choice
        options: [pilot, core, all]
      dry_run:
        description: 'Dry run (no PRs)'
        type: boolean
        default: true

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup cihub
        run: pip install -e .

      - name: Sync templates
        env:
          GH_TOKEN: ${{ secrets.REPO_ADMIN_TOKEN }}
        run: |
          cihub sync-templates \
            --group ${{ inputs.group }} \
            ${{ inputs.dry_run && '--dry-run' || '--create-prs' }}
```

**Required:** `REPO_ADMIN_TOKEN` with `repo` scope for all managed repos.

---

### Caller Workflow Strategy

Each target repo gets a **tiny generated caller** that pins a reusable workflow version:

```yaml
# .github/workflows/ci.yml (GENERATED - do not edit)
# Generated by cihub v0.5.0 from .ci-hub.yml
# Template: workflows/java-caller.yml.j2 @ v1.2.0

name: CI
on: [push, pull_request]

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@v1.2.0
    with:
      run_jacoco: true
      run_pitest: true
      run_checkstyle: true
      # ... inputs derived from .ci-hub.yml
    secrets: inherit
```

**Benefits:**
- Caller is minimal (10-20 lines)
- Version pinned for stability
- `cihub update` bumps the version
- All logic lives in hub's reusable workflow

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    CI-CD HUB - COMPLETE ARCHITECTURE                            │
│                    (Self-Validating CLI + Central Hub)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ CLI TOOL (cihub) - SINGLE ENTRY POINT                                     │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  PROJECT SCAFFOLDING                                                      │  │
│  │  ├── cihub new <name>           # Create new project from scratch         │  │
│  │  │   ├── --profile security     # Use security profile                    │  │
│  │  │   ├── --profile fast         # Use fast profile                        │  │
│  │  │   ├── --profile standard     # Use standard profile                    │  │
│  │  │   └── --interactive          # Ask for each tool                       │  │
│  │  │                                                                        │  │
│  │  ├── cihub init                 # Add hub to existing project             │  │
│  │  │   └── Detects existing pom.xml/requirements.txt                        │  │
│  │  │                                                                        │  │
│  │  ├── cihub add <tool>           # Add tool to project                     │  │
│  │  │   ├── cihub add jacoco       # → Modifies pom.xml                      │  │
│  │  │   ├── cihub add pitest       # → Modifies pom.xml                      │  │
│  │  │   ├── cihub add owasp        # → Modifies pom.xml + workflow           │  │
│  │  │   └── cihub add module api   # → Creates new module folder + pom       │  │
│  │  │                                                                        │  │
│  │  ├── cihub remove <tool>        # Remove tool from project                │  │
│  │  │                                                                        │  │
│  │  MAINTENANCE                                                              │  │
│  │  ├── cihub update               # Update project to latest templates      │  │
│  │  │   └── Like Copier - updates already-generated files                    │  │
│  │  ├── cihub sync-templates       # Sync ALL managed repos                  │  │
│  │  ├── cihub diff                 # Show drift from templates               │  │
│  │  │                                                                        │  │
│  │  VALIDATION (SELF-TESTING)                                                │  │
│  │  ├── cihub validate             # Validate EVERYTHING                     │  │
│  │  │   ├── --config               # Validate .ci-hub.yml                    │  │
│  │  │   ├── --pom                  # Validate pom.xml (mvn validate)         │  │
│  │  │   ├── --workflow             # Validate workflow YAML                  │  │
│  │  │   ├── --report               # Validate report.json                    │  │
│  │  │   └── --all                  # All of the above                        │  │
│  │  │                                                                        │  │
│  │  ├── cihub lint                 # Lint all generated files                │  │
│  │  │   ├── yamllint for YAML                                                │  │
│  │  │   ├── xmllint for XML                                                  │  │
│  │  │   └── jsonschema for JSON                                              │  │
│  │  │                                                                        │  │
│  │  ├── cihub test                 # Test generated project works            │  │
│  │  │   ├── mvn validate           # POM is valid                            │  │
│  │  │   ├── mvn compile            # Project compiles                        │  │
│  │  │   └── mvn test               # Tests pass                              │  │
│  │  │                                                                        │  │
│  │  EXECUTION                                                                │  │
│  │  ├── cihub dispatch             # Trigger CI runs                         │  │
│  │  ├── cihub status               # Check run status                        │  │
│  │  └── cihub aggregate            # Aggregate reports                       │  │
│  │                                                                           │  │
│  │  HUB MANAGEMENT                                                           │  │
│  │  ├── cihub hub update           # Update CLI to latest version            │  │
│  │  ├── cihub hub templates list   # List available templates                │  │
│  │  └── cihub hub profiles list    # List available profiles                 │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Profiles (Prebuilt Configurations)

### Security Profile
All security tools enabled with strict thresholds.

| Tool       | Setting           |
|------------|-------------------|
| JaCoCo     | 80% coverage      |
| PITest     | 80% mutation      |
| Checkstyle | 0 errors          |
| PMD        | 0 violations      |
| SpotBugs   | 0 bugs            |
| OWASP      | fail on CVSS >= 5 |
| Semgrep    | enabled           |
| Trivy      | enabled           |
| CodeQL     | enabled           |

### Standard Profile
Balanced configuration for most projects.

| Tool       | Setting           |
|------------|-------------------|
| JaCoCo     | 70% coverage      |
| PITest     | 70% mutation      |
| Checkstyle | 0 errors          |
| PMD        | 0 violations      |
| SpotBugs   | 0 bugs            |
| OWASP      | fail on CVSS >= 7 |
| Semgrep    | disabled          |
| Trivy      | disabled          |

### Fast Profile
Quick feedback with minimal tools.

| Tool       | Setting      |
|------------|--------------|
| JaCoCo     | 50% coverage |
| PITest     | disabled     |
| Checkstyle | enabled      |
| PMD        | disabled     |
| SpotBugs   | disabled     |
| OWASP      | disabled     |
| Semgrep    | disabled     |

### Custom Profile
Interactive mode where user picks each tool.

---

## Central Hub Repository Structure

```
hub-release/
├── cihub/                        ← CLI TOOL (Python package)
│   ├── __main__.py
│   ├── cli.py                    # Click/Typer CLI
│   ├── commands/
│   │   ├── new.py                # cihub new
│   │   ├── init.py               # cihub init
│   │   ├── add.py                # cihub add
│   │   ├── update.py             # cihub update
│   │   ├── validate.py           # cihub validate
│   │   ├── lint.py               # cihub lint
│   │   ├── dispatch.py           # cihub dispatch
│   │   └── sync.py               # cihub sync-templates
│   ├── generators/
│   │   ├── pom.py                # POM generation logic
│   │   ├── workflow.py           # Workflow generation
│   │   └── config.py             # Config generation
│   ├── validators/
│   │   ├── yaml_validator.py     # yamllint wrapper
│   │   ├── xml_validator.py      # xmllint wrapper
│   │   ├── schema_validator.py   # JSON schema validation
│   │   ├── pom_validator.py      # mvn validate wrapper
│   │   └── workflow_validator.py # GHA workflow validation
│   └── detectors/
│       ├── language.py           # Detect Java/Python/Node
│       ├── build_tool.py         # Detect Maven/Gradle/etc
│       └── existing_tools.py     # Detect tools in pom.xml
│
├── templates/                    ← JINJA2 TEMPLATES
│   ├── pom/
│   │   ├── parent-pom.xml.j2
│   │   ├── child-pom.xml.j2
│   │   └── plugins/
│   │       ├── jacoco.xml.j2
│   │       ├── pitest.xml.j2
│   │       ├── checkstyle.xml.j2
│   │       ├── pmd.xml.j2
│   │       ├── spotbugs.xml.j2
│   │       └── owasp.xml.j2
│   ├── config/
│   │   ├── checkstyle.xml.j2
│   │   ├── pmd-ruleset.xml.j2
│   │   └── spotbugs-exclude.xml.j2
│   ├── workflows/
│   │   ├── java-caller.yml.j2
│   │   ├── python-caller.yml.j2
│   │   └── monorepo-caller.yml.j2
│   ├── python/
│   │   ├── pyproject.toml.j2
│   │   └── setup.cfg.j2
│   └── ci-hub.yml.j2             # .ci-hub.yml template
│
├── profiles/                     ← PROFILE DEFINITIONS
│   ├── security.yaml
│   ├── standard.yaml
│   ├── fast.yaml
│   └── minimal.yaml
│
├── scripts/                      ← PYTHON SCRIPTS (testable)
│   ├── detect_repo.py
│   ├── load_config.py
│   ├── generate_report.py
│   ├── validate_summary.py
│   ├── validate_config.py
│   └── aggregate_reports.py
│
├── .github/
│   ├── actions/                  ← COMPOSITE ACTIONS
│   │   ├── detect-repo/
│   │   ├── generate-report/
│   │   ├── validate-config/
│   │   ├── validate-report/
│   │   └── aggregate-reports/
│   └── workflows/                ← REUSABLE WORKFLOWS
│       ├── java-ci.yml
│       ├── python-ci.yml
│       ├── hub-orchestrator.yml
│       └── hub-run-all.yml
│
├── schema/                       ← SOURCE OF TRUTH
│   ├── ci-hub-config.schema.json
│   ├── ci-report.v2.json
│   ├── profile.schema.json
│   └── pom-plugin.schema.json    # Schema for plugin configs
│
├── config/                       ← CENTRALIZED OVERRIDES
│   ├── defaults.yaml
│   └── repos/
│
└── tests/                        ← CLI + SCRIPT TESTS
    ├── test_cli_new.py           # Test cihub new
    ├── test_cli_init.py          # Test cihub init
    ├── test_cli_add.py           # Test cihub add
    ├── test_cli_validate.py      # Test cihub validate
    ├── test_generators/
    │   ├── test_pom_generator.py
    │   └── test_workflow_generator.py
    ├── test_validators/
    │   ├── test_yaml_validator.py
    │   └── test_pom_validator.py
    ├── test_contract_consistency.py
    ├── fixtures/                 # Test fixtures
    │   ├── sample-java-repo/
    │   ├── sample-python-repo/
    │   └── expected-outputs/
    └── snapshots/                # Snapshot tests for generated files
```

---

## Self-Validation Chain

After ANY generation (`cihub new`, `cihub add`, `cihub update`), the CLI automatically validates:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ SELF-VALIDATION CHAIN (Built into CLI)                                    │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. YAML LINT                                                             │
│     └── yamllint .ci-hub.yml .github/workflows/*.yml                      │
│         ✓ Valid YAML syntax                                               │
│         ✓ Consistent formatting                                           │
│                                                                           │
│  2. XML LINT                                                              │
│     └── xmllint --noout pom.xml */pom.xml                                 │
│         ✓ Valid XML syntax                                                │
│         ✓ Well-formed structure                                           │
│                                                                           │
│  3. SCHEMA VALIDATION                                                     │
│     └── jsonschema validate .ci-hub.yml against schema                    │
│         ✓ Config matches schema                                           │
│         ✓ All required fields present                                     │
│                                                                           │
│  4. POM VALIDATION                                                        │
│     └── mvn validate -f pom.xml                                           │
│         ✓ POM is valid Maven project                                      │
│         ✓ All plugins resolve                                             │
│         ✓ Dependencies available                                          │
│                                                                           │
│  5. WORKFLOW VALIDATION                                                   │
│     └── actionlint .github/workflows/*.yml                                │
│         ✓ Valid GitHub Actions syntax                                     │
│         ✓ All actions exist                                               │
│         ✓ Inputs/outputs correct                                          │
│                                                                           │
│  6. CONSISTENCY CHECK                                                     │
│     └── Compare .ci-hub.yml ↔ pom.xml ↔ workflow                          │
│         ✓ Tools in config match pom plugins                               │
│         ✓ Tools in config match workflow inputs                           │
│         ✓ No drift between sources                                        │
│                                                                           │
│  If ANY validation fails → CLI shows error and does NOT commit            │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Validation Layers (Runtime)

```
┌─────────────────────────────────────────────────────────────────┐
│ VALIDATION CHAIN (runs automatically in workflows)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CONFIG VALIDATION (before tools run)                        │
│     └── uses: ./.github/actions/validate-config                 │
│         - Validates .ci-hub.yml against schema                  │
│         - Checks tool booleans are consistent                   │
│                                                                 │
│  2. TOOL EXECUTION                                              │
│     └── Workflow runs JaCoCo, PITest, OWASP, etc.               │
│         - Each step has an outcome: success/failure/skipped     │
│                                                                 │
│  3. REPORT GENERATION                                           │
│     └── uses: ./.github/actions/generate-report                 │
│         - Creates report.json with:                             │
│           tools_configured: {jacoco: true, pitest: false, ...}  │
│           tools_ran: {jacoco: true, pitest: false, ...}         │
│         - Creates summary.md with Configured | Ran columns      │
│                                                                 │
│  4. REPORT VALIDATION                                           │
│     └── uses: ./.github/actions/validate-report                 │
│         - Validates report.json against schema                  │
│         - Checks summary.md matches report.json                 │
│         - Detects drift: configured=true but ran=false          │
│         - Verifies artifacts exist for tools that ran           │
│                                                                 │
│  5. AGGREGATION (hub orchestrator only)                         │
│     └── uses: ./.github/actions/aggregate-reports               │
│         - Combines all repo reports                             │
│         - Enforces thresholds                                   │
│         - Creates hub-report.json                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Init Flow Example

```
$ cihub init

   Detecting repository structure...
   Found: pom.xml (Maven)
   Found: Dockerfile
   Found: docker-compose.yml
  
   Detected configuration:
   Language: Java
   Build tool: Maven
   Java version: 21 (from pom.xml)
   Has Docker: Yes

 ️ Tool Configuration:
   ✓ JaCoCo (coverage) - detected in pom.xml
   ✓ Checkstyle - detected in pom.xml
   ? PITest (mutation testing) - Enable? [Y/n]
   ? OWASP Dependency-Check - Enable? [Y/n]
   ? Do you have an NVD API key? [y/N]
   ? Semgrep - Enable? [y/N]
   ? Trivy (container scan) - Enable? [Y/n]

    Will create:
   .ci-hub.yml                    (config)
   .github/workflows/ci.yml       (caller workflow)

Proceed? [Y/n]

   Created .ci-hub.yml
   Created .github/workflows/ci.yml
   Added to hub registry: config/repos/my-java-app.yaml

    Running validation...
   ✓ YAML lint passed
   ✓ Schema validation passed
   ✓ Workflow syntax valid

Next steps:
  1. Review .ci-hub.yml and adjust thresholds
  2. Commit and push
  3. Run: cihub dispatch --repo my-java-app
```

---

## CLI New Flow Example (Full Project Scaffolding)

```
$ cihub new contact-suite --profile standard

   Project Setup:
   ? Base package: com.example.contact
   ? Modules (comma-separated): api, core, web, common

   Creating project structure...

contact-suite/
├── pom.xml                          ← Parent POM (all plugins configured)
├── api/
│   ├── pom.xml                      ← Child POM (inherits from parent)
│   └── src/main/java/...
├── core/
│   ├── pom.xml
│   └── src/main/java/...
├── web/
│   ├── pom.xml
│   └── src/main/java/...
├── common/
│   ├── pom.xml
│   └── src/main/java/...
├── config/
│   ├── checkstyle.xml               ← Generated
│   ├── pmd-ruleset.xml              ← Generated
│   └── spotbugs-exclude.xml         ← Generated
├── .ci-hub.yml                      ← CI config
└── .github/workflows/ci.yml         ← Workflow

   All POMs configured with:
   - JaCoCo (70% coverage threshold)
   - PITest (70% mutation threshold)
   - Checkstyle (Google style)
   - PMD (standard rules)
   - SpotBugs (high confidence)
   - OWASP (fail on CVSS >= 7)

   Running validation...
   ✓ YAML lint passed
   ✓ XML lint passed
   ✓ Schema validation passed
   ✓ POM validation passed (mvn validate)
   ✓ Workflow syntax valid

   Project created successfully!
```

---

## Testing Strategy

### Unit Tests
- Test each generator function in isolation
- Test each validator function in isolation
- Test template rendering

### Snapshot Tests (Like Jest snapshots)
- Generate project → snapshot the output
- On change → compare to snapshot
- Intentional changes → update snapshot

### Integration Tests
- `cihub new` → generates valid project → `mvn compile` passes
- `cihub add jacoco` → pom modified → `mvn test` runs jacoco
- `cihub update` → files updated → still valid

### Contract Tests
- Schema keys match workflow inputs
- Profile tools match schema tools
- Template variables match schema properties

### E2E Tests
- Create project → push → workflow runs → passes
- Smoke test repos (already exist)

---

## Implementation Phases

| Phase | What                        | Delivers                                                      |
|-------|-----------------------------|---------------------------------------------------------------|
| **1** | Scripts + Composite Actions | `generate_report.py`, `validate_report.py`, composite actions |
| **2** | Validators                  | `yaml_validator.py`, `xml_validator.py`, `pom_validator.py`   |
| **3** | Generators                  | `pom.py`, `workflow.py` - template rendering                  |
| **4** | Profiles                    | `security.yaml`, `standard.yaml`, `fast.yaml`                 |
| **5** | CLI Commands                | `cihub new`, `cihub init`, `cihub add`, `cihub validate`      |
| **6** | Self-Validation             | Auto-validate after every generation                          |
| **7** | Tests                       | Unit, snapshot, integration, contract, e2e                    |
| **8** | Update Flow                 | `cihub update` like Copier - updates existing projects        |
| **9** | PyQt6 GUI                   | Optional desktop app wrapping CLI (see Phase 9 section below) |

---

## Phase 9: PyQt6 GUI Wrapper (Optional)

### Architecture: CLI as Engine, GUI as Controller

The GUI NEVER implements logic. It is a thin wrapper that:
1. Runs CLI commands via QProcess
2. Parses `--json` output
3. Displays results in tables/lists
4. Opens files in system editor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GUI ARCHITECTURE                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                      ┌─────────────────────────────┐   │
│  │   PyQt6 GUI     │                      │   CLI (cihub)               │   │
│  │                 │                      │                             │   │
│  │  ┌───────────┐  │    QProcess          │  ┌───────────────────────┐  │   │
│  │  │ Repo List │  │ ─────────────────────│  │ All business logic    │  │   │
│  │  └───────────┘  │                      │  │ - Validation          │  │   │
│  │                 │    --json output     │  │ - Generation          │  │   │
│  │  ┌───────────┐  │ ◄────────────────────│  │ - Drift detection     │  │   │
│  │  │ Problems  │  │                      │  │ - Git operations      │  │   │
│  │  │ Table     │  │    streaming logs    │  └───────────────────────┘  │   │
│  │  └───────────┘  │ ◄────────────────────│                             │   │
│  │                 │                      │                             │   │ 
│  │  ┌───────────┐  │                      │                             │   │
│  │  │ Console   │  │                      │                             │   │
│  │  └───────────┘  │                      │                             │   │
│  │                 │                      │                             │   │
│  └─────────────────┘                      └─────────────────────────────┘   │
│                                                                             │
│  KEY RULE: GUI calls CLI. GUI never reimplements CLI logic.                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pre-requisite: CLI JSON Output Contract

Before GUI work begins, ALL commands must support `--json`:

```bash
cihub apply --json
cihub validate --json
cihub verify --json
cihub sync-templates --json
```

**Standard JSON Response Format:**

```json
{
  "command": "apply",
  "status": "success|failure|error",
  "exit_code": 0,
  "duration_ms": 1842,
  "summary": "All validations passed",
  "artifacts": {
    "manifest_path": ".cihub/manifest.json",
    "report_path": "reports/report.json"
  },
  "problems": [
    {
      "severity": "error",
      "code": "CIHUB-POM-001",
      "tool": "pom_validator",
      "file": "pom.xml",
      "line": 87,
      "column": 12,
      "message": "JaCoCo plugin version mismatch",
      "suggestion": "Run 'cihub fix --apply CIHUB-POM-001'"
    }
  ],
  "suggestions": [
    {
      "title": "Regenerate workflow",
      "command": "cihub apply --fast"
    }
  ],
  "files_generated": [".github/workflows/ci.yml"],
  "files_modified": ["pom.xml"]
}
```

**Rule:** Without this contract, the GUI becomes a fragile log parser. JSON output is non-negotiable.

### GUI Scope (Minimal Viable)

| Feature                        | Included | NOT Included              |
|--------------------------------|----------|---------------------------|
| Repo list with status badges   | ✅        | Repo settings editing     |
| Profile dropdown               | ✅        | Profile creation/editing  |
| Tier buttons (Fast/Build/Test) | ✅        | Custom tier creation      |
| Run/Stop buttons               | ✅        | Parallel execution        |
| Problems table                 | ✅        | In-app code editing       |
| Console log (streaming)        | ✅        | Log filtering/search      |
| Click-to-open file at line     | ✅        | In-app file editor        |
| Git stage/commit/push          | ✅        | Merge conflict resolution |
| Open PR via `gh`               | ✅        | PR review/merge           |
| Summary dashboard              | ✅        | Historical trends         |

### Screen Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CI-CD Hub                                              [─] [□] [×]         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Repos ────────────┐  ┌─ Controls ───────────────────────────────────┐  │
│  │                    │  │                                               │  │
│  │  🟢 contact-suite  │  │  Profile: [Standard ▼]   Tier: [Fast] [Build] [Test]  │
│  │  🟢 bst-demo       │  │                                               │  │
│  │  🟡 legacy-app     │  │  [▶ Run]  [⏹ Stop]  [🔄 Refresh]              │  │
│  │  ⚫ archived       │  │                                               │  │
│  │                    │  └───────────────────────────────────────────────┘  │
│  │  [+ Add] [- Remove]│                                                     │
│  │                    │  ┌─ Tabs ────────────────────────────────────────┐  │
│  └────────────────────┘  │  [Problems] [Console] [Changes] [Summary]     │  │
│                          ├───────────────────────────────────────────────┤  │
│                          │                                               │  │
│                          │  Severity │ Code           │ File      │ Line │  │
│                          │  ─────────┼────────────────┼───────────┼──────│  │
│                          │     error │ CIHUB-POM-001  │ pom.xml   │ 87   │  │
│                          │     error │ CIHUB-SCHEMA-3 │ .ci-hub.. │ 15   │  │
│                          │     warn  │ CIHUB-MANIF-1  │ manifest  │ -    │  │
│                          │                                               │  │
│                          │  Double-click to open in editor               │  │
│                          │                                               │  │
│                          └───────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Git ────────────────────────────────────────────────────────────────┐  │
│  │  Branch: main  │  [Stage All] [Commit] [Push] [Open PR]              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Status: Ready │ Last run: 2.3s │ 2 errors, 1 warning                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Sub-Phases

| Sub-Phase | What                | Delivers                                           |
|-----------|---------------------|----------------------------------------------------|
| **9.1**   | CLI `--json` output | All commands support `--json` flag                 |
| **9.2**   | Core GUI shell      | QProcess runner, repo list, console tab            |
| **9.3**   | Problems table      | Click-to-open with `code -g file:line:col`         |
| **9.4**   | Git integration     | Stage/commit/push buttons                          |
| **9.5**   | PR integration      | Open PR via `gh pr create`                         |
| **9.6**   | Polish              | Status badges, progress indicators, error handling |

### Technical Implementation Notes

**QProcess for CLI Execution:**

```python
from PyQt6.QtCore import QProcess

class CliRunner:
    def __init__(self):
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

    def run(self, command: str, args: list[str], json_mode: bool = True):
        if json_mode:
            args = args + ["--json"]
        self.process.start("cihub", [command] + args)

    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        # Stream to console tab
        self.console_output.emit(data)

    def _on_finished(self, exit_code: int):
        if self.json_mode:
            result = json.loads(self.accumulated_output)
            self.problems_updated.emit(result.get("problems", []))
```

**Opening Files in Editor:**

```python
import subprocess
import os

def open_in_editor(file: str, line: int, col: int):
    editor = os.environ.get("CIHUB_EDITOR", "code")

    if editor == "code":
        subprocess.run(["code", "-g", f"{file}:{line}:{col}"])
    elif editor == "idea":
        subprocess.run(["idea", "--line", str(line), file])
    elif editor == "vim":
        subprocess.run(["vim", f"+{line}", file])
    else:
        # Fallback: just open file
        if sys.platform == "darwin":
            subprocess.run(["open", file])
        else:
            subprocess.run(["xdg-open", file])
```

### What GUI Should NOT Do

1. **No YAML/XML editing** - Use VS Code or IDE
2. **No template rendering** - CLI does this
3. **No validation logic** - CLI does this
4. **No direct git commands** - Always through CLI or `gh`
5. **No auto-installing tools** - Just show what's missing
6. **No reimplementing anything** - If CLI can't do it, GUI can't either

### Why This Architecture Works

| Concern           | Solution                                 |
|-------------------|------------------------------------------|
| Logic duplication | Zero - GUI calls CLI                     |
| Testing           | CLI is fully testable, GUI is thin       |
| Headless CI       | Works perfectly - same CLI               |
| Maintenance       | One codebase for logic                   |
| Debugging         | CLI works alone, isolate GUI issues      |
| Onboarding        | Users can click before learning commands |

---

### Desktop App Vision: CI/CD Control Center

The desktop app is what makes this feel "product-y" instead of "another scaffolding CLI". The key principle: **do not become an IDE. Become a CI/CD control center.**

#### Features That Set It Apart

##### 1. Live GitHub Actions Runs Panel (Big Differentiator)

This gives you "I can see CI status without leaving my desktop" which feels like a real tool.

| Action             | How                                                     |
|--------------------|---------------------------------------------------------|
| Select repo        | Show latest workflow runs (queued/running/success/fail) |
| Click a run        | Show jobs/steps + live log tail                         |
| Re-run failed jobs | Button: `gh run rerun --failed`                         |
| Re-run all jobs    | Button: `gh run rerun`                                  |
| Cancel run         | Button: `gh run cancel`                                 |

**Implementation:** GitHub CLI (`gh`) as backend initially.

```bash
# Commands wrapped by GUI
gh run list --repo owner/name --json status,conclusion,workflowName,createdAt,headBranch,headSha
gh run view <id> --json jobs,conclusion,status
gh run watch <id>          # For streaming
gh run rerun <id> --failed
gh run cancel <id>
```

**Why `gh`:** Auth handled, rate limits handled, works everywhere, less code. GUI streams output like a terminal panel. Can swap to pure API later if needed, but keep UI contract.

##### 2. One-Click Git Workflow Buttons

For a selected repo:

| Button  | Action                                                    |
|---------|-----------------------------------------------------------|
| Stage   | Default: only managed files from manifest                 |
| Commit  | Message auto-generated: profile/tools/template versions   |
| Push    | Push to remote                                            |
| Open PR | Via `gh pr create`, auto-creates branch `cihub/update-vX` |

**Key differentiator:** The GUI understands ownership.
- Stages only files listed in `.cihub/manifest.json` unless user toggles "include other changes"
- Prevents accidental commits of unrelated work

##### 3. Drift + Fix Dashboard (Killer UX)

A dedicated page that answers:
- Is repo drifting? (`manifest verify`)
- What broke? (problems table)
- What do I do next? (fix buttons)

**Example Problems Table:**

| Problem             | Fix Button                                 |
|---------------------|--------------------------------------------|
| actionlint missing  | Copy install command                       |
| Schema mismatch     | Open `.ci-hub.yml` location + docs snippet |
| Checkstyle failures | Open report HTML/XML output folder         |

This turns structured diagnostics (`fix_id`) into clickable remediation. Each problem from `cihub validate --json` becomes an actionable row.

##### 4. Multi-Repo Fleet View (This Is How It Becomes a "Hub")

**Left side:** List of repos

**Columns:**
| Column | Description |
|--------|-------------|
| template_version | Current template version |
| cli_version | CLI version used |
| profile | security/standard/fast |
| last apply status | Success/fail/never |
| last GH run status | Green/red/pending |
| drift | yes/no badge |
| needs update | yes/no badge |

**Buttons:**
- Apply to selected
- Apply to all
- Update fleet to latest

This is the "central hub" story made visible. Manage 50 repos from one screen.

##### 5. Report Viewer (Not IDE, Just Artifacts)

**Tabs:**
| Tab | Content |
|-----|---------|
| Coverage | JaCoCo HTML report |
| SpotBugs | SpotBugs report |
| OWASP | Dependency-Check report |
| SARIF | Semgrep/Trivy SARIF viewer |

Open artifacts directly from local `target/` or downloaded from GH run artifacts.

**For GitHub artifacts:**
```bash
gh run download <id>   # Downloads to local
# Then open HTML locally in system browser
```

##### 6. Config Wizard (Safe, Not a Text Editor)

Instead of editing YAML directly:
- Form-based UI for `.ci-hub.yml`
- Dropdowns for profile/tools/thresholds
- Writes YAML deterministically
- Then runs `cihub apply --fast`

This reduces user error and makes onboarding easy. No YAML knowledge required.

#### What NOT to Build (Keeps Scope Sane)

| Avoid                    | Reason                       |
|--------------------------|------------------------------|
| Embedded code editor     | Use VS Code/IntelliJ         |
| YAML IDE features        | Out of scope                 |
| "Autofix code style"     | Not a linter IDE             |
| Filesystem watchers (v1) | Complexity, add later        |
| Auto-install tools       | Security risk, env-dependent |

**Rule:** If VS Code does it better, don't build it.

#### "Set It Apart" Shortlist (Build These First)

If you only build 3 things, build these:

| Priority | Feature                                               | Why It Matters            |
|----------|-------------------------------------------------------|---------------------------|
| 1        | Fleet view (multi-repo) + drift badges                | The "hub" in CI-CD Hub    |
| 2        | GitHub runs page (live status, rerun/cancel)          | Feels like a real CI tool |
| 3        | Safe Git buttons (stage managed only, commit/push/PR) | Reduces friction to zero  |

Those three alone make it feel like a **real CI/CD desktop console**.

#### Updated Screen Layout (With GitHub Runs)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CI-CD Hub                                              [─] [□] [×]         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Repos ────────────┐  ┌─ GitHub Runs ─────────────────────────────────┐  │
│  │                    │  │                                               │  │
│  │     contact-suite  │  │  Run #1234  main     success  2m ago          │  │
│  │     bst-demo       │  │  Run #1233  main     failed   15m ago         │  │
│  │     legacy-app     │  │  Run #1232  feat     running  now             │  │
│  │     archived       │  │                                               │  │
│  │                    │  │  [ Re-run Failed] [ Re-run All] [ Cancel]  │  │
│  │  [+ Add] [- Remove]│  │                                               │  │
│  │                    │  └───────────────────────────────────────────────┘  │
│  └────────────────────┘                                                     │
│                          ┌─ Tabs ────────────────────────────────────────┐  │
│  ┌─ Fleet Status ─────┐  │  [Problems] [Console] [Changes] [Reports]     │  │
│  │                    │  ├───────────────────────────────────────────────┤  │
│  │  Repos: 12         │  │                                               │  │
│  │  Drifting: 2       │  │  Severity │ Code           │ File      │ Fix  │  │
│  │  Needs update: 4   │  │  ─────────┼────────────────┼───────────┼──────│  │
│  │  All green: 6      │  │     error │ CIHUB-POM-001  │ pom.xml   │ [🔧] │  │
│  │                    │  │     error │ CIHUB-SCHEMA-3 │ .ci-hub.. │ [🔧] │  │
│  │  [Apply to All]    │  │     warn  │ CIHUB-MANIF-1  │ manifest  │ [🔧] │  │
│  │  [Update Fleet]    │  │                                               │  │
│  │                    │  │  Double-click to open │ Click 🔧 to fix       │  │
│  └────────────────────┘  │                                               │  │
│                          └───────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Git (Managed Files Only) ─────────────────────────────────────────────┐ │
│  │  Branch: main  │  Staged: 3 files  │  ☑ Include unmanaged changes     │ │
│  │  [Stage] [Commit: "chore(cihub): update to v1.3.0"] [Push] [Open PR]   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Status: Ready │ Last run: 2.3s │ 2 errors, 1 warning │ Profile: standard  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Implementation Decision Points

These decisions should be made before implementation begins:

**Q1: GitHub Integration Backend**

| Option                          | Pros                                              | Cons                        |
|---------------------------------|---------------------------------------------------|-----------------------------|
| `gh` CLI only (Recommended)     | Fastest to implement, auth handled, battle-tested | GitHub only                 |
| Abstract backend (GitLab later) | Multi-platform support                            | More code, delayed delivery |

**Q2: Default Staging Behavior**

| Option                      | Behavior                                   |
|-----------------------------|--------------------------------------------|
| Manifest-only (Recommended) | Stage only files in `.cihub/manifest.json` |
| All files                   | Stage everything, opt-out for exclusions   |

**Q3: Fleet Apply Strategy**

| Option                          | Behavior                             |
|---------------------------------|--------------------------------------|
| Queued one-by-one (Recommended) | Reliable, easier debugging           |
| Parallel execution              | Faster, but harder to track failures |

---

## Phase 10: Enterprise Features

### Product Positioning

> **CI-CD Hub: Compliance-as-Code for CI/CD pipelines.**
> One config, full audit trail, fleet-wide visibility.

The goal is to make this something companies **pay for because it reduces risk and time**, not because it scaffolds files.

### Target Buyers

| Buyer                    | What They Pay For                   | Key Features                                      |
|--------------------------|-------------------------------------|---------------------------------------------------|
| **Platform Engineering** | "Manage 200 repos from one place"   | Fleet dashboard, bulk operations, drift detection |
| **Security/Compliance**  | "Prove we're compliant to auditors" | Attestations, policy enforcement, audit trails    |
| **Dev Productivity**     | "Reduce CI friction and time"       | One-click onboarding, auto-remediation            |

**Primary buyer:** Platform Engineering + Security together. They sign the checks.

### What Sets CI-CD Hub Apart

The unique differentiator is the **end-to-end deterministic chain**:

```
Config (.ci-hub.yml)
  → Generation (templates)
  → Validation (schema + policy)
  → Execution (reusable workflows)
  → Attestation (SLSA/cosign)
  → Aggregation (fleet reports)
  → Drift detection (template-guard)
```

Backstage does catalog. Sigstore does attestation. Copier does templating. CI-CD Hub does **all of it with deterministic drift detection**.

### Enterprise Feature 1: Fleet Dashboard UI

**Value:** Platform teams need visibility across 200 repos without CLI.

**Answers these questions:**
- Which repos are drifting from policy?
- Which repos are on old workflow versions?
- Which repos are failing security scans and why?
- What's the median CI time? Flake rate? Top failure causes?

**Implementation:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Fleet Overview                                                 [Export CSV]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Summary ────────────────────────────────────────────────────────────┐   │
│  │  Total Repos: 47  │  Compliant: 38  │  Drifting: 6  │  Failing: 3   │    │
│  │  Avg Coverage: 74.2%  │  Avg Mutation: 71.8%  │  Critical CVEs: 2   │    │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ Fleet Table ────────────────────────────────────────────────────────┐   │
│  │ Repo              │ Profile  │ Template │ Coverage │ Drift │ Status  │   │
│  │───────────────────┼──────────┼──────────┼──────────┼───────┼─────────│   │
│  │ contact-suite     │ security │ v1.3.0   │ 82%      │ ✓     │ 🟢      │   │
│  │ payment-api       │ security │ v1.3.0   │ 78%      │ ✓     │ 🟢      │   │
│  │ legacy-billing    │ standard │ v1.2.0   │ 65%      │ ⚠️    │ 🟡      │   │
│  │ user-service      │ fast     │ v1.1.0   │ 45%      │ ❌    │ 🔴      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [Select All Drifting] [Apply Updates] [Generate Compliance Report]         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data source:** `aggregate_reports.py` output + `gh run list` status.

**Export options:**
- CSV (for spreadsheets/Jira import)
- JSON (for BI tools)
- PDF (for compliance audits)

### Enterprise Feature 2: Compliance Attestation Bundle

**Value:** Auditors want a **single artifact** that proves a release is allowed to ship.

**What you already have:**
- Cosign keyless signing (OIDC)
- Rekor transparency log
- DSSE envelope parsing
- OCI referrers (SBOM/VEX)
- Provenance verification

**What's missing:** Packaging it as a one-click "compliance bundle."

**Attestation Bundle Contents:**

```json
// attestation-bundle.json
{
  "schema_version": "1.0",
  "bundle_id": "uuid-here",
  "generated_at": "2025-12-24T10:00:00Z",
  "release": {
    "repo": "owner/repo-name",
    "commit_sha": "abc123...",
    "tag": "v2.1.0",
    "branch": "main"
  },
  "ci_run": {
    "run_id": 12345678,
    "run_url": "https://github.com/owner/repo/actions/runs/12345678",
    "workflow_version": "v1.3.0",
    "hub_cli_version": "0.5.0"
  },
  "policy": {
    "profile": "security",
    "policy_version": "v2.0.0",
    "thresholds": {
      "coverage_min": 80,
      "mutation_min": 80,
      "cvss_fail_threshold": 5
    }
  },
  "results": {
    "coverage": 84.2,
    "mutation_score": 81.5,
    "critical_cves": 0,
    "high_cves": 2,
    "checkstyle_errors": 0,
    "spotbugs_bugs": 0
  },
  "attestations": {
    "provenance": {
      "type": "https://slsa.dev/provenance/v1",
      "digest": "sha256:abc123...",
      "rekor_log_id": "uuid-here",
      "rekor_log_index": 12345678
    },
    "sbom": {
      "format": "spdx-json",
      "digest": "sha256:def456...",
      "tool": "syft@1.18.0"
    },
    "signature": {
      "type": "cosign-keyless",
      "issuer": "https://token.actions.githubusercontent.com",
      "subject": "https://github.com/owner/repo/.github/workflows/release.yml@refs/tags/v2.1.0",
      "certificate_digest": "sha256:ghi789..."
    }
  },
  "verification_commands": {
    "verify_signature": "cosign verify --certificate-identity-regexp='...' ghcr.io/owner/repo@sha256:...",
    "verify_sbom": "cosign verify-attestation --type spdxjson ghcr.io/owner/repo@sha256:...",
    "check_rekor": "rekor-cli get --log-index 12345678"
  }
}
```

**CLI command:**

```bash
cihub attestation bundle --run-id 12345678 --output attestation-bundle.json
cihub attestation bundle --run-id 12345678 --sign    # Also signs the bundle itself
```

**GUI integration:**
- "Download Compliance Bundle" button on any green run
- Drag-and-drop to attach to Jira ticket or compliance system

### Enterprise Feature 3: Policy Exception Workflow

**Value:** Governance without humans babysitting every repo.

**The problem:** Sometimes a repo legitimately needs to drop below thresholds temporarily (tech debt sprint, urgent hotfix, etc.). Today this requires editing `.ci-hub.yml` and hoping someone remembers to revert it.

**The solution:** Time-bound exceptions with audit trail.

**Exception Request Format:**

```yaml
# .cihub/exceptions.yaml (in target repo)
schema_version: "1.0"

exceptions:
  - id: "EXC-2025-001"
    created_at: "2025-12-24T10:00:00Z"
    created_by: "jguida941"

    rule: "coverage_min"
    original_value: 80
    requested_value: 60

    reason: "Tech debt sprint - refactoring legacy module"
    jira_ticket: "PLAT-1234"  # Optional but recommended

    expires_at: "2026-01-07T23:59:59Z"  # 14 days

    approvals:
      - approver: "security-lead"
        approved_at: "2025-12-24T11:00:00Z"
        method: "github-review"  # PR approval on exception file

    status: "active"  # active | expired | revoked
```

**Enforcement Logic:**

```python
def get_effective_threshold(repo_config, exceptions):
    base_threshold = repo_config.coverage_min  # 80

    active_exceptions = [
        e for e in exceptions
        if e.rule == "coverage_min"
        and e.status == "active"
        and e.expires_at > now()
        and len(e.approvals) >= 1
    ]

    if active_exceptions:
        exception = active_exceptions[0]
        log_audit(f"Using exception {exception.id}: {base_threshold} -> {exception.requested_value}")
        return exception.requested_value

    return base_threshold
```

**Workflow Integration:**

```yaml
# In reusable workflow
- name: Check policy exceptions
  id: exceptions
  run: |
    cihub policy check-exceptions --json > exceptions.json
    # Outputs: effective thresholds after exceptions applied

- name: Run coverage check
  run: |
    THRESHOLD=$(jq -r '.effective.coverage_min' exceptions.json)
    # Use $THRESHOLD instead of hardcoded value
```

**Exception Lifecycle:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXCEPTION LIFECYCLE                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Developer creates PR adding exception to .cihub/exceptions.yaml         │
│     └── Must include: rule, values, reason, expiry, jira_ticket             │
│                                                                             │
│  2. Required approver reviews PR                                            │
│     └── Approver defined in org policy (e.g., security-lead, tech-lead)     │
│                                                                             │
│  3. On merge, exception becomes active                                      │
│     └── CLI validates: expiry <= max_exception_days (default 30)            │
│                                                                             │
│  4. Every CI run logs exception usage                                       │
│     └── Audit trail in report.json: "exception_applied": "EXC-2025-001"     │
│                                                                             │
│  5. On expiry:                                                              │
│     ├── Status auto-changes to "expired"                                    │
│     ├── Next CI run uses original threshold                                 │
│     └── Optional: auto-create PR to remove expired exceptions               │
│                                                                             │
│  6. Fleet dashboard shows:                                                  │
│     └── "3 repos have active exceptions, 2 expiring this week"              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**CLI commands:**

```bash
cihub policy exception request \
  --rule coverage_min \
  --value 60 \
  --reason "Tech debt sprint" \
  --expires 14d \
  --jira PLAT-1234

cihub policy exception list              # Show all exceptions
cihub policy exception list --expiring   # Show expiring soon
cihub policy exception revoke EXC-2025-001
```

**GUI integration:**
- "Request Exception" button on failing checks
- Exception dashboard showing active/expiring/expired
- One-click extension (adds 7 days, requires re-approval)

### Enterprise Feature 4: Auto-Remediation PRs (Self-Healing)

**Value:** The system maintains itself.

**You already have:**
- `template-guard.yml` detects drift daily
- `sync-templates.yml` can push updates

**What's missing:** Automated PR creation with context.

**Auto-PR Contents:**

```markdown
## CI-CD Hub Auto-Remediation

This PR was automatically generated by CI-CD Hub to fix detected drift.

### Changes
- Updated `.github/workflows/ci.yml` to template v1.3.0
- Regenerated `config/checkstyle.xml` (hash mismatch)

### Why These Changes Are Safe
- Only hub-owned files modified (per `.cihub/manifest.json`)
- No user-owned files touched
- All changes are deterministic template re-renders

### Validation
- [x] `cihub validate --fast` passed
- [x] Schema validation passed
- [x] No drift in user-owned files

### Source
- Hub version: v1.3.0
- Template version: v1.3.0
- Generated at: 2025-12-24T04:00:00Z
- Drift detected by: template-guard.yml run #12345

---
*Auto-merge enabled. Will merge when CI passes.*
```

**Workflow:**

```yaml
# .github/workflows/auto-remediate.yml
name: Auto-Remediation

on:
  schedule:
    - cron: '0 4 * * *'  # Daily at 4 AM
  workflow_dispatch:

jobs:
  remediate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for drift
        id: drift
        run: |
          cihub verify --json > drift.json
          if jq -e '.drifted_files | length > 0' drift.json; then
            echo "has_drift=true" >> $GITHUB_OUTPUT
          fi

      - name: Create remediation PR
        if: steps.drift.outputs.has_drift == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # Create branch
          git checkout -b cihub/auto-remediate-$(date +%Y%m%d)

          # Apply fixes (owned files only)
          cihub apply --force

          # Commit and push
          git add -A
          git commit -m "chore(cihub): auto-remediate drift"
          git push -u origin HEAD

          # Create PR with auto-merge
          gh pr create \
            --title "🔄 Auto-remediate CI-CD Hub drift" \
            --body-file .cihub/remediation-pr-template.md \
            --label "auto-remediation,ci-cd-hub"

          gh pr merge --auto --squash
```

### What We Are Not Building: Phase 10 Scope Control

| Feature             | Defer Until | Reason                                 |
|---------------------|-------------|----------------------------------------|
| Jira integration    | Phase 11    | Integration tax, not differentiation   |
| Slack integration   | Phase 11    | Can use GitHub notifications initially |
| SSO/RBAC            | Phase 11    | Use GitHub teams for now               |
| CI time optimizer   | Phase 12    | Complex, needs data collection first   |
| GitLab/Azure DevOps | Phase 12    | Get 10 paying GitHub customers first   |
| SaaS hosting        | Phase 13    | Enterprises want self-hosted initially |

### Phase 10 Implementation Sub-Phases

| Sub-Phase | Deliverable                                             | Depends On            |
|-----------|---------------------------------------------------------|-----------------------|
| **10.1**  | Fleet dashboard data API (`cihub fleet status --json`)  | Phase 9 CLI           |
| **10.2**  | Fleet dashboard UI (PyQt table + summary)               | 10.1 + Phase 9 GUI    |
| **10.3**  | Attestation bundle command (`cihub attestation bundle`) | Existing cosign/Rekor |
| **10.4**  | Exception schema + validation                           | Schema work           |
| **10.5**  | Exception enforcement in workflows                      | 10.4                  |
| **10.6**  | Auto-remediation workflow                               | Drift detection       |
| **10.7**  | GUI integration (exception request, bundle download)    | 10.3 + 10.5           |

### Decision Points (Phase 10)

**Q1: Exception Approval Method**

| Option                         | Pros                            | Cons                            |
|--------------------------------|---------------------------------|---------------------------------|
| GitHub PR review (Recommended) | Built-in, audit trail, familiar | Requires PR for every exception |
| Separate approval API          | Faster, more flexible           | Custom auth, more code          |

**Q2: Auto-Remediation Merge Strategy**

| Option                              | Behavior                                  |
|-------------------------------------|-------------------------------------------|
| Auto-merge when green (Recommended) | Hands-off, but requires branch protection |
| Require manual merge                | Safer, but defeats "self-healing" goal    |
| Auto-merge with delay (24h)         | Balance: time to review, still automatic  |

**Q3: Attestation Bundle Signing**

| Option                       | Pros                           | Cons                               |
|------------------------------|--------------------------------|------------------------------------|
| Cosign keyless (Recommended) | No key management, GitHub OIDC | Requires Actions environment       |
| GPG signing                  | Works anywhere                 | Key management burden              |
| Unsigned (metadata only)     | Simplest                       | Less trust, auditors may push back |

---

## Phase 11: Operational Excellence (Hub Infrastructure)

These workflows run in the **hub repo itself**, not target repos. They are advanced operational capabilities that prove the hub's reliability and compliance.

### Architecture: Root Repo vs Hub-Release

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ARCHITECTURE: Root Repo vs Hub-Release                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ci-cd-hub/ (root)                      hub-release/                        │
│  ─────────────────                      ────────────                        │
│  OPERATIONAL WORKFLOWS                  CLI + TEMPLATES                     │
│  (Advanced, Hub-internal)               (Distributed to target repos)       │
│                                                                             │
│  ├── chaos.yml          ← Resilience    ├── cihub CLI                       │
│  ├── dr-drill.yml       ← DR testing    ├── templates/                      │
│  ├── cross-time-determinism.yml         ├── profiles/                       │
│  ├── hub-pipeline.yml   ← Fleet CI      ├── .github/workflows/              │
│  ├── kyverno-e2e.yml    ← Policy test   │   ├── java-ci.yml (reusable)      │
│  ├── sign-digest.yml    ← Signing       │   ├── python-ci.yml (reusable)    │
│  ├── update-action-pins.yml             │   └── sync-templates.yml          │
│  └── tools-ci.yml       ← Self-test     └── schema/                         │
│                                                                             │
│  These stay here because:               These distribute because:           │
│  - Hub infrastructure concerns          - Target repo CI needs them         │
│  - BigQuery/Kyverno dependencies        - CLI wraps and validates them      │
│  - Not needed by target repos           - Portable to any repo              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.1 Cross-Time Determinism (SLSA Level 4)

**Value:** Proves builds are reproducible after a time delay. Most companies claim SLSA Level 3. This proves Level 4.

**Auditor pitch:** "Our builds are mathematically reproducible 24 hours later."

**Workflow:** `cross-time-determinism.yml`

**How it works:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CROSS-TIME DETERMINISM                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Original build runs at T=0                                              │
│     └── Artifacts uploaded, checksums recorded                              │
│                                                                             │
│  2. Delayed rebuild triggered at T+24h                                      │
│     ├── Checkout same commit ref                                            │
│     ├── Set SOURCE_DATE_EPOCH to original commit time                       │
│     ├── Set deterministic env (TZ=UTC, LC_ALL=C, LANG=C)                    │
│     └── Run identical build                                                 │
│                                                                             │
│  3. Compare checksums                                                       │
│     ├── If match: "Build IS deterministic"                                  │
│     └── If differ: Auto-create CRITICAL issue, block releases               │
│                                                                             │
│  4. Evidence bundle                                                         │
│     ├── Both checksum files                                                 │
│     ├── Environment metadata                                                │
│     └── Diff (if non-deterministic)                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key techniques:**
- `SOURCE_DATE_EPOCH` pinning
- Deterministic locale settings
- Automatic GitHub issue creation on failure
- 90-day artifact retention for evidence

### 11.2 Chaos Testing

**Value:** Proves CI infrastructure is resilient to failures.

**Enterprise pitch:** "We can prove our CI is resilient to infrastructure failures."

**Workflow:** `chaos.yml`

**Features:**
- Controlled fault injection (network, resource limits, timing)
- NDJSON event streaming for every chaos scenario
- BigQuery ingestion for historical analysis
- Kill switch (`CHAOS_KILL_SWITCH` variable) for emergencies
- Opt-in via PR label (`chaos-opt-in`)

**Event schema:**

```json
{
  "fault": "network-partition",
  "target": "maven-central",
  "seed": 42,
  "rate": 0.3,
  "started_at": "2025-12-24T06:00:00Z",
  "ended_at": "2025-12-24T06:00:15Z",
  "outcome": "recovered",
  "retries": 2
}
```

**Metrics enabled:**
- Mean time to recovery (MTTR)
- Fault tolerance rate
- Retry effectiveness
- Flaky chaos scenario detection

### 11.3 Disaster Recovery Drills

**Value:** Weekly automated DR testing with metrics.

**Compliance pitch:** "We run and prove DR every week, automatically."

**Workflow:** `dr-drill.yml` (weekly schedule: `0 3 * * 1`)

**Features:**
- Deterministic observation time (derived from manifest)
- Metrics capture (`drill-metrics.json`)
- NDJSON event streaming
- BigQuery ingestion for trending
- Evidence bundle upload

**DR event schema:**

```json
{
  "step": "restore-backup",
  "started_at": "2025-12-24T03:00:00Z",
  "ended_at": "2025-12-24T03:05:00Z",
  "status": "success",
  "notes": "Restored 47 repos from backup"
}
```

**Metrics tracked:**
- Recovery Time Objective (RTO) compliance
- Recovery Point Objective (RPO) compliance
- Step-by-step timing
- Failure causes and rates

### 11.4 Kyverno E2E Testing

**Value:** Live cluster policy enforcement testing, not just dry-run.

**Workflow:** `kyverno-e2e.yml`

**How it works:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KYVERNO E2E FLOW                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Spin up Kind cluster (ephemeral Kubernetes)                             │
│                                                                             │
│  2. Deploy Kyverno + policies from policies/kyverno/                        │
│     ├── verify-images.yaml (cosign signature verification)                  │
│     ├── require-referrers.yaml (SBOM/provenance enforcement)                │
│     ├── secretless.yaml (no static secrets)                                 │
│     └── block-pull-request-target.yaml (dangerous trigger blocking)         │
│                                                                             │
│  3. Run enforcement verification                                            │
│     ├── Deploy compliant pods → should succeed                              │
│     ├── Deploy non-compliant pods → should be blocked                       │
│     └── Capture evidence of enforcement                                     │
│                                                                             │
│  4. Cleanup                                                                 │
│     └── Delete Kind cluster (always, even on failure)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Triggers:**
- Changes to `policies/kyverno/**`
- Changes to deployment scripts
- Push to main/master

### 11.5 Hub Self-Testing

**Value:** Dogfooding - the hub tests its own tools.

**Workflow:** `tools-ci.yml`

**Tests run:**
- `test_build_vuln_input` - VEX input generation
- `test_build_issuer_subject_input` - OIDC subject validation
- `test_generate_vex` - VEX document generation
- `test_provenance_io` - DSSE envelope parsing
- `test_mutation_observatory` - Mutation report processing
- `test_kyverno_policy_checker` - Policy validation logic
- Markdown linting for docs

### 11.6 Action Pin Automation

**Value:** Supply chain security without manual maintenance.

**Workflow:** `update-action-pins.yml` (daily: `0 5 * * *`)

**How it works:**
1. Resolve floating tags (e.g., `v4`) to commit SHAs
2. Update all workflow files
3. Run integrity checks
4. Create PR automatically if changes detected

**Example transformation:**
```yaml
# Before (vulnerable to tag mutation)
uses: actions/checkout@v4

# After (immutable)
uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955 # v4
```

### 11.7 Hub Pipeline (Fleet CI Engine)

**Value:** Central orchestration of multi-repo CI.

**Workflow:** `hub-pipeline.yml`

**Capabilities:**
- Dynamic matrix loading from `config/repositories.yaml`
- Workflow integrity guards (pin verification, secret scanning)
- Runner isolation budget validation
- Java and Python detection + execution
- Mutation testing integration
- Per-repo artifact collection
- Aggregated summary generation

**This IS the fleet execution engine** referenced throughout the plan.

### Phase 11 Summary

| Workflow               | Schedule             | Value                      |
|------------------------|----------------------|----------------------------|
| cross-time-determinism | On-demand            | SLSA Level 4 proof         |
| chaos.yml              | Daily + PR opt-in    | Resilience metrics         |
| dr-drill.yml           | Weekly (Monday 3 AM) | DR compliance evidence     |
| kyverno-e2e.yml        | On policy changes    | Runtime policy enforcement |
| tools-ci.yml           | On-demand            | Dogfooding / self-test     |
| update-action-pins.yml | Daily (5 AM)         | Supply chain automation    |
| hub-pipeline.yml       | Push/PR              | Fleet CI orchestration     |

### 11.8 Integration Plan: Consolidate Root Repo Into Hub-Release

All code currently in the root `ci-cd-hub/` repo should be integrated into `hub-release/` to create a single, self-contained distribution.  
Some of this may be in the _quarantine directory right now. We will have to get it from that Repo.

#### Files to Integrate

**1. Core Tools (tools/) → hub-release/cihub/tools/**

| Source                                       | Target                                    | Purpose                     |
|----------------------------------------------|-------------------------------------------|-----------------------------|
| `tools/provenance_io.py`                     | `cihub/tools/provenance_io.py`            | DSSE envelope parsing       |
| `tools/verify_provenance.py`                 | `cihub/tools/verify_provenance.py`        | Provenance verification     |
| `tools/generate_vex.py`                      | `cihub/tools/generate_vex.py`             | VEX document generation     |
| `tools/run_chaos.py`                         | `cihub/tools/chaos/runner.py`             | Chaos test execution        |
| `tools/run_dr_drill.py`                      | `cihub/tools/dr/runner.py`                | DR drill execution          |
| `tools/dr_drill/*.py`                        | `cihub/tools/dr/`                         | DR drill module             |
| `tools/mutation_observatory.py`              | `cihub/tools/mutation/observatory.py`     | Mutation report processing  |
| `tools/kyverno_policy_checker.py`            | `cihub/tools/policy/kyverno.py`           | Policy validation           |
| `tools/predictive_scheduler.py`              | `cihub/tools/scheduler/predictor.py`      | CI optimization             |
| `tools/update_action_pins.py`                | `cihub/tools/supply_chain/action_pins.py` | SHA pinning                 |
| `tools/cache_sentinel.py`                    | `cihub/tools/cache/sentinel.py`           | Cache management            |
| `tools/build_vuln_input.py`                  | `cihub/tools/policy/vuln_input.py`        | Vulnerability input         |
| `tools/build_issuer_subject_input.py`        | `cihub/tools/policy/issuer_subject.py`    | OIDC validation             |
| `tools/verify_rekor_proof.py`                | `cihub/tools/supply_chain/rekor.py`       | Rekor verification          |
| `tools/safe_subprocess.py`                   | `cihub/tools/util/subprocess.py`          | Safe command execution      |
| `tools/ephemeral_data_lab.py`                | `cihub/tools/testing/ephemeral_lab.py`    | Ephemeral test environments |
| `tools/scripts/pitest_to_json.py`            | `cihub/tools/mutation/pitest.py`          | PIT report conversion       |
| `tools/scripts/generate_mutation_reports.py` | `cihub/tools/mutation/reports.py`         | Mutation report generation  |

**2. Shell Scripts → hub-release/cihub/tools/scripts/**

| Source                                  | Target                                     | Purpose                 |
|-----------------------------------------|--------------------------------------------|-------------------------|
| `tools/rekor_monitor.sh`                | `cihub/tools/scripts/rekor_monitor.sh`     | Rekor monitoring        |
| `tools/publish_referrers.sh`            | `cihub/tools/scripts/publish_referrers.sh` | OCI referrer publishing |
| `tools/determinism_check.sh`            | `cihub/tools/scripts/determinism_check.sh` | Build determinism       |
| `scripts/install_tools.sh`              | `cihub/tools/scripts/install_tools.sh`     | Tool installation       |
| `scripts/deploy_kyverno.sh`             | `cihub/tools/scripts/deploy_kyverno.sh`    | Kyverno deployment      |
| `scripts/verify_kyverno_enforcement.sh` | `cihub/tools/scripts/verify_kyverno.sh`    | Kyverno verification    |
| `scripts/sign_evidence_bundle.sh`       | `cihub/tools/scripts/sign_bundle.sh`       | Bundle signing          |

**3. Validation Scripts → hub-release/cihub/validators/**

| Source                                  | Target                                   | Purpose                    |
|-----------------------------------------|------------------------------------------|----------------------------|
| `scripts/check_workflow_integrity.py`   | `cihub/validators/workflow_integrity.py` | Workflow pin/secret checks |
| `scripts/check_runner_isolation.py`     | `cihub/validators/runner_isolation.py`   | Runner budget validation   |
| `scripts/enforce_concurrency_budget.py` | `cihub/validators/concurrency.py`        | Concurrency limits         |
| `scripts/check_schema_registry.py`      | `cihub/validators/schema_registry.py`    | Schema validation          |
| `scripts/validate_schema.py`            | `cihub/validators/schema.py`             | JSON Schema validation     |

**4. Pipeline Scripts → hub-release/cihub/runners/**

| Source                                  | Target                                   | Purpose                 |
|-----------------------------------------|------------------------------------------|-------------------------|
| `scripts/load_repository_matrix.py`     | `cihub/runners/matrix_loader.py`         | Matrix configuration    |
| `scripts/emit_pipeline_run.py`          | `cihub/runners/pipeline_emit.py`         | Pipeline event emission |
| `scripts/build_project_ci_summary.py`   | `cihub/runners/summary_builder.py`       | Summary generation      |
| `scripts/record_job_telemetry.py`       | `cihub/runners/telemetry.py`             | Job telemetry           |
| `scripts/consolidate_telemetry.py`      | `cihub/runners/telemetry_consolidate.py` | Telemetry aggregation   |
| `scripts/generate_scheduler_reports.py` | `cihub/runners/scheduler_reports.py`     | Scheduler analysis      |
| `scripts/capture_canary_decision.py`    | `cihub/runners/canary.py`                | Canary decisions        |

**5. Ingestion Layer → hub-release/cihub/ingestion/**

| Source                      | Target                         | Purpose         |
|-----------------------------|--------------------------------|-----------------|
| `ingest/chaos_dr_ingest.py` | `cihub/ingestion/bigquery.py`  | BigQuery loader |
| `ingest/event_loader.py`    | `cihub/ingestion/warehouse.py` | Local warehouse |

**6. Policies → hub-release/policies/**

| Source                    | Target                 | Purpose           |
|---------------------------|------------------------|-------------------|
| `policies/*.rego`         | `policies/rego/`       | OPA/Rego policies |
| `policies/tests/*.rego`   | `policies/rego/tests/` | Policy tests      |
| `policies/kyverno/*.yaml` | `policies/kyverno/`    | Kyverno policies  |

**7. Schemas → hub-release/schema/**

| Source                                 | Target                          | Purpose               |
|----------------------------------------|---------------------------------|-----------------------|
| `schema/pipeline_run.v1.2.json`        | `schema/pipeline_run.v1.2.json` | Pipeline event schema |
| `schema/dr_drill.event.v1.json`        | `schema/dr_drill.event.v1.json` | DR event schema       |
| `schema/registry.json`                 | `schema/registry.json`          | Tool registry schema  |
| `schema/cyclonedx-vex-1.5.schema.json` | `schema/cyclonedx-vex.json`     | VEX schema            |

**8. Configuration → hub-release/config/**

| Source                                | Target                             | Purpose          |
|---------------------------------------|------------------------------------|------------------|
| `config/repositories.yaml`            | `config/repositories.yaml`         | Managed repos    |
| `config/runner-isolation.yaml`        | `config/runner-isolation.yaml`     | Runner limits    |
| `config/mutation-observatory.ci.yaml` | `config/mutation-observatory.yaml` | Mutation config  |
| `config/projects.yaml`                | `config/projects.yaml`             | Project registry |

**9. Autopsy (Failure Analysis) → hub-release/cihub/autopsy/**

| Source                            | Target                            | Purpose                     |
|-----------------------------------|-----------------------------------|-----------------------------|
| `autopsy/analyzer.py`             | `cihub/autopsy/analyzer.py`       | Failure root cause analysis |
| `autopsy/rules/default_rules.yml` | `cihub/autopsy/rules/default.yml` | Analysis rules              |
| `autopsy/tests/`                  | `cihub/autopsy/tests/`            | Analyzer tests              |

**10. Dashboards → hub-release/dashboards/**

| Source                                   | Target                       | Purpose          |
|------------------------------------------|------------------------------|------------------|
| `dashboards/run_health.json`             | `dashboards/run_health.json` | Pipeline health  |
| `dashboards/mutation_effectiveness.json` | `dashboards/mutation.json`   | Mutation metrics |

**11. Fixtures → hub-release/tests/fixtures/**

| Source                   | Target                         | Purpose                |
|--------------------------|--------------------------------|------------------------|
| `fixtures/mutation/`     | `tests/fixtures/mutation/`     | Mutation test data     |
| `fixtures/supply_chain/` | `tests/fixtures/supply_chain/` | Supply chain test data |
| `fixtures/kyverno/`      | `tests/fixtures/kyverno/`      | Kyverno test manifests |
| `fixtures/ephemeral/`    | `tests/fixtures/ephemeral/`    | Ephemeral lab configs  |
| `tools/tests/fixtures/`  | `tests/fixtures/tools/`        | Tool test fixtures     |

**12. DR Data → hub-release/data/dr/**

| Source                    | Target                    | Purpose         |
|---------------------------|---------------------------|-----------------|
| `data/dr/manifest.json`   | `data/dr/manifest.json`   | DR baseline     |
| `data/dr/backup.json`     | `data/dr/backup.json`     | Backup snapshot |
| `data/dr/provenance.json` | `data/dr/provenance.json` | Provenance data |
| `data/dr/sbom.json`       | `data/dr/sbom.json`       | SBOM data       |

**13. Tests → hub-release/tests/**

| Source                    | Target                    | Purpose         |
|---------------------------|---------------------------|-----------------|
| `tools/tests/test_*.py`   | `tests/tools/test_*.py`   | Tool unit tests |
| `autopsy/tests/test_*.py` | `tests/autopsy/test_*.py` | Autopsy tests   |
| `scripts/test_*.py`       | `tests/scripts/test_*.py` | Script tests    |

**14. Workflows → hub-release/.github/workflows/**

| Source                       | Target                                 | Purpose           |
|------------------------------|----------------------------------------|-------------------|
| `chaos.yml`                  | `workflows/chaos.yml`                  | Chaos testing     |
| `dr-drill.yml`               | `workflows/dr-drill.yml`               | DR drills         |
| `cross-time-determinism.yml` | `workflows/cross-time-determinism.yml` | SLSA L4           |
| `kyverno-e2e.yml`            | `workflows/kyverno-e2e.yml`            | Policy E2E        |
| `hub-pipeline.yml`           | `workflows/hub-pipeline.yml`           | Fleet CI          |
| `update-action-pins.yml`     | `workflows/update-action-pins.yml`     | Pin automation    |
| `tools-ci.yml`               | `workflows/tools-ci.yml`               | Self-test         |
| `sign-digest.yml`            | `workflows/sign-digest.yml`            | Signing           |
| `mutation.yml`               | `workflows/mutation.yml`               | Mutation testing  |
| `unit.yml`                   | `workflows/unit.yml`                   | Unit tests        |
| `schema-ci.yml`              | `workflows/schema-ci.yml`              | Schema validation |
| `security-lint.yml`          | `workflows/security-lint.yml`          | Security linting  |
| `rekor-monitor.yml`          | `workflows/rekor-monitor.yml`          | Rekor monitoring  |
| `codeql.yml`                 | `workflows/codeql.yml`                 | CodeQL analysis   |

#### Consolidated Directory Structure

After integration, `hub-release/` becomes:  
(This needs to be updated to reflect current repo state)

```
hub-release/
├── cihub/                           # CLI + Core Tools
│   ├── __main__.py
│   ├── cli.py
│   ├── commands/                    # CLI commands (new, init, add, validate, etc.)
│   ├── generators/                  # Template rendering
│   ├── validators/                  # Validation logic
│   │   ├── workflow_integrity.py    # ← from scripts/
│   │   ├── runner_isolation.py      # ← from scripts/
│   │   ├── concurrency.py           # ← from scripts/
│   │   ├── schema.py                # ← from scripts/
│   │   └── schema_registry.py       # ← from scripts/
│   ├── runners/                     # Pipeline execution
│   │   ├── matrix_loader.py         # ← from scripts/
│   │   ├── pipeline_emit.py         # ← from scripts/
│   │   ├── summary_builder.py       # ← from scripts/
│   │   ├── telemetry.py             # ← from scripts/
│   │   └── canary.py                # ← from scripts/
│   ├── tools/                       # Core tools
│   │   ├── provenance_io.py         # ← from tools/
│   │   ├── verify_provenance.py     # ← from tools/
│   │   ├── generate_vex.py          # ← from tools/
│   │   ├── safe_subprocess.py       # ← from tools/
│   │   ├── chaos/                   # Chaos testing
│   │   │   └── runner.py            # ← from tools/run_chaos.py
│   │   ├── dr/                      # DR drills
│   │   │   ├── runner.py            # ← from tools/run_dr_drill.py
│   │   │   ├── config.py            # ← from tools/dr_drill/
│   │   │   └── operations.py        # ← from tools/dr_drill/
│   │   ├── mutation/                # Mutation testing
│   │   │   ├── observatory.py       # ← from tools/mutation_observatory.py
│   │   │   ├── pitest.py            # ← from tools/scripts/
│   │   │   └── reports.py           # ← from tools/scripts/
│   │   ├── policy/                  # Policy validation
│   │   │   ├── kyverno.py           # ← from tools/kyverno_policy_checker.py
│   │   │   ├── vuln_input.py        # ← from tools/build_vuln_input.py
│   │   │   └── issuer_subject.py    # ← from tools/build_issuer_subject_input.py
│   │   ├── supply_chain/            # Supply chain security
│   │   │   ├── action_pins.py       # ← from tools/update_action_pins.py
│   │   │   └── rekor.py             # ← from tools/verify_rekor_proof.py
│   │   ├── scheduler/               # CI optimization
│   │   │   └── predictor.py         # ← from tools/predictive_scheduler.py
│   │   ├── cache/                   # Cache management
│   │   │   └── sentinel.py          # ← from tools/cache_sentinel.py
│   │   ├── testing/                 # Test infrastructure
│   │   │   └── ephemeral_lab.py     # ← from tools/ephemeral_data_lab.py
│   │   └── scripts/                 # Shell scripts
│   │       ├── rekor_monitor.sh     # ← from tools/
│   │       ├── publish_referrers.sh # ← from tools/
│   │       ├── determinism_check.sh # ← from tools/
│   │       ├── install_tools.sh     # ← from scripts/
│   │       ├── deploy_kyverno.sh    # ← from scripts/
│   │       └── sign_bundle.sh       # ← from scripts/
│   ├── ingestion/                   # Event ingestion
│   │   ├── bigquery.py              # ← from ingest/chaos_dr_ingest.py
│   │   ├── warehouse.py             # ← from ingest/event_loader.py
│   │   └── schemas/
│   │       ├── event.v1.json
│   │       ├── chaos.v1.json
│   │       └── dr.v1.json
│   ├── autopsy/                     # Failure analysis
│   │   ├── analyzer.py              # ← from autopsy/
│   │   ├── rules/
│   │   │   └── default.yml          # ← from autopsy/rules/
│   │   └── tests/
│   ├── diagnostics/                 # Error reporting
│   ├── fixers/                      # Auto-fix logic
│   └── editors/                     # Editor integration
│
├── templates/                       # Jinja2 templates (existing)
├── profiles/                        # Profile definitions (existing)
│
├── policies/                        # Policy definitions
│   ├── rego/                        # ← from policies/*.rego
│   │   ├── issuer_subject.rego
│   │   ├── oci_referrers.rego
│   │   ├── sbom_vex.rego
│   │   └── tests/
│   └── kyverno/                     # ← from policies/kyverno/
│       ├── verify-images.yaml
│       ├── require-referrers.yaml
│       ├── secretless.yaml
│       └── block-pull-request-target.yaml
│
├── schema/                          # JSON schemas
│   ├── ci-hub-config.schema.json    # (existing)
│   ├── ci-report.v2.json            # (existing)
│   ├── pipeline_run.v1.2.json       # ← from schema/
│   ├── dr_drill.event.v1.json       # ← from schema/
│   ├── registry.json                # ← from schema/
│   └── cyclonedx-vex.json           # ← from schema/
│
├── config/                          # Configuration
│   ├── defaults.yaml                # (existing)
│   ├── repos/                       # (existing)
│   ├── repositories.yaml            # ← from config/
│   ├── runner-isolation.yaml        # ← from config/
│   ├── mutation-observatory.yaml    # ← from config/
│   └── projects.yaml                # ← from config/
│
├── dashboards/                      # Dashboard configs
│   ├── run_health.json              # ← from dashboards/
│   └── mutation.json                # ← from dashboards/
│
├── data/                            # Runtime data
│   └── dr/                          # ← from data/dr/
│       ├── manifest.json
│       ├── backup.json
│       ├── provenance.json
│       └── sbom.json
│
├── .github/
│   ├── actions/                     # Composite actions (existing)
│   └── workflows/                   # All workflows consolidated
│       ├── java-ci.yml              # (existing reusable)
│       ├── python-ci.yml            # (existing reusable)
│       ├── sync-templates.yml       # (existing)
│       ├── chaos.yml                # ← from .github/workflows/
│       ├── dr-drill.yml             # ← from .github/workflows/
│       ├── cross-time-determinism.yml
│       ├── hub-pipeline.yml
│       ├── kyverno-e2e.yml
│       ├── update-action-pins.yml
│       ├── sign-digest.yml
│       ├── tools-ci.yml
│       ├── mutation.yml
│       ├── unit.yml
│       ├── schema-ci.yml
│       ├── security-lint.yml
│       ├── rekor-monitor.yml
│       └── codeql.yml
│
├── tests/                           # All tests consolidated
│   ├── fixtures/                    # ← from fixtures/ + tools/tests/fixtures/
│   │   ├── mutation/
│   │   ├── supply_chain/
│   │   ├── kyverno/
│   │   ├── ephemeral/
│   │   └── tools/
│   ├── tools/                       # ← from tools/tests/
│   │   ├── test_provenance_io.py
│   │   ├── test_generate_vex.py
│   │   ├── test_mutation_observatory.py
│   │   ├── test_kyverno_policy_checker.py
│   │   ├── test_dr_drill.py
│   │   ├── test_cache_sentinel.py
│   │   ├── test_predictive_scheduler.py
│   │   └── ...
│   ├── autopsy/                     # ← from autopsy/tests/
│   ├── validators/
│   ├── generators/
│   └── integration/
│
├── scripts/                         # Legacy scripts (existing)
└── docs/                            # Documentation (existing)
```

#### Integration Phases

| Phase    | Files                                      | Effort | Priority |
|----------|--------------------------------------------|--------|----------|
| **I-1**  | `tools/*.py` → `cihub/tools/`              | Medium | High     |
| **I-2**  | `scripts/check_*.py` → `cihub/validators/` | Low    | High     |
| **I-3**  | `ingest/*.py` → `cihub/ingestion/`         | Low    | High     |
| **I-4**  | `policies/` → `policies/`                  | Low    | Medium   |
| **I-5**  | `schema/*.json` → `schema/`                | Low    | Medium   |
| **I-6**  | `autopsy/` → `cihub/autopsy/`              | Medium | Medium   |
| **I-7**  | `.github/workflows/*.yml` → consolidated   | Medium | High     |
| **I-8**  | `tests/` consolidation                     | Medium | Medium   |
| **I-9**  | `config/`, `dashboards/`, `data/`          | Low    | Low      |
| **I-10** | Update all imports, fix paths              | High   | Critical |

#### Files to DELETE After Integration

These become redundant after consolidation:

```
# Root repo files that move to hub-release:
# Some of these are in _quarantine currently
# We are currently in new hub-release repo
# We will have to copy these from quarntee or other CI-CD-HUB repo

ci-cd-hub/tools/                    # → hub-release/cihub/tools/
ci-cd-hub/scripts/                  # → hub-release/cihub/ (various)
ci-cd-hub/ingest/                   # → hub-release/cihub/ingestion/
ci-cd-hub/policies/                 # → hub-release/policies/
ci-cd-hub/schema/                   # → hub-release/schema/
ci-cd-hub/autopsy/                  # → hub-release/cihub/autopsy/
ci-cd-hub/dashboards/               # → hub-release/dashboards/
ci-cd-hub/fixtures/                 # → hub-release/tests/fixtures/
ci-cd-hub/config/                   # → hub-release/config/
ci-cd-hub/data/                     # → hub-release/data/
ci-cd-hub/.github/workflows/        # → hub-release/.github/workflows/

# Redundant workflow:
ci-cd-hub/.github/workflows/project-ci.yml  # Duplicates hub-pipeline.yml
```
#### Additional Files NOT in Original List (MISSED)

**15. Chaos Configuration → hub-release/config/chaos/**

| Source                     | Target                      | Purpose              |
|----------------------------|-----------------------------|----------------------|
| `chaos/chaos-fixture.json` | `config/chaos/fixture.json` | Chaos test scenarios |

**16. dbt Models → hub-release/models/**

| Source                          | Target                          | Purpose            |
|---------------------------------|---------------------------------|--------------------|
| `models/dbt_project.yml`        | `models/dbt_project.yml`        | dbt project config |
| `models/profiles.yml`           | `models/profiles.yml`           | dbt profiles       |
| `models/packages.yml`           | `models/packages.yml`           | dbt packages       |
| `models/tests/data_quality.yml` | `models/tests/data_quality.yml` | Data quality tests |

**17. Kyverno Deployment → hub-release/deploy/kyverno/**

| Source                              | Target                              | Purpose              |
|-------------------------------------|-------------------------------------|----------------------|
| `deploy/kyverno/install.yaml`       | `deploy/kyverno/install.yaml`       | Kyverno installation |
| `deploy/kyverno/kustomization.yaml` | `deploy/kyverno/kustomization.yaml` | Kustomize config     |
| `supply-chain-enforce/kyverno/`     | `deploy/kyverno/`                   | Merge duplicate      |

**18. Additional Scripts → hub-release/cihub/**

| Source                                     | Target                                    | Purpose              |
|--------------------------------------------|-------------------------------------------|----------------------|
| `scripts/run_dbt.py`                       | `cihub/runners/dbt.py`                    | dbt execution        |
| `scripts/load_projects.py`                 | `cihub/runners/projects.py`               | Project loading      |
| `scripts/summarize_codeql.py`              | `cihub/runners/codeql.py`                 | CodeQL summarization |
| `scripts/summarize_junit.py`               | `cihub/runners/junit.py`                  | JUnit summarization  |
| `scripts/scan_runtime_secrets.sh`          | `cihub/tools/scripts/scan_secrets.sh`     | Secret scanning      |
| `scripts/cache_provenance.sh`              | `cihub/tools/scripts/cache_provenance.sh` | Provenance caching   |
| `scripts/emit_cache_quarantine_event.py`   | `cihub/runners/cache_quarantine.py`       | Cache quarantine     |
| `scripts/prepare_policy_inputs.py`         | `cihub/tools/policy/prepare_inputs.py`    | Policy input prep    |
| `scripts/github_actions_egress_wrapper.sh` | `cihub/tools/scripts/egress_wrapper.sh`   | Egress control       |
| `scripts/enforce_egress_control.sh`        | `cihub/tools/scripts/egress_enforce.sh`   | Egress enforcement   |
| `scripts/test_egress_allowlist.sh`         | `cihub/tools/scripts/egress_test.sh`      | Egress testing       |
| `data-quality-and-dr/dr_recall.sh`         | `cihub/tools/scripts/dr_recall.sh`        | DR recall            |

**19. Documentation Scripts → hub-release/scripts/docs/**

| Source                                 | Target                                 | Purpose                |
|----------------------------------------|----------------------------------------|------------------------|
| `scripts/docs/check_orphan_docs.py`    | `scripts/docs/check_orphan.py`         | Orphan doc detection   |
| `scripts/docs/validate_frontmatter.py` | `scripts/docs/validate_frontmatter.py` | Frontmatter validation |
| `scripts/docs/generate_index.sh`       | `scripts/docs/generate_index.sh`       | Index generation       |
| `scripts/docs/generate_structure.sh`   | `scripts/docs/generate_structure.sh`   | Structure generation   |
| `scripts/docs/update_doc_links.sh`     | `scripts/docs/update_links.sh`         | Link updates           |

**20. Linting Configuration → hub-release/**

| Source                    | Target                    | Purpose            |
|---------------------------|---------------------------|--------------------|
| `.bandit.yaml`            | `.bandit.yaml`            | Bandit config      |
| `.bandit.full.yaml`       | `.bandit.full.yaml`       | Full bandit config |
| `.markdownlint-cli2.yaml` | `.markdownlint-cli2.yaml` | Markdown linting   |
| `.markdownlint.json`      | `.markdownlint.json`      | Markdown rules     |

**21. Documentation → hub-release/docs/**

| Source                     | Target                            | Purpose                |
|----------------------------|-----------------------------------|------------------------|
| `docs/SUPPLY_CHAIN.md`     | `docs/guides/supply-chain.md`     | Supply chain guide     |
| `docs/DR_RUNBOOK.md`       | `docs/guides/dr-runbook.md`       | DR runbook             |
| `docs/RUNNER_ISOLATION.md` | `docs/guides/runner-isolation.md` | Runner isolation       |
| `.github/SECURITY.md`      | `docs/guides/security.md`         | Security guide         |
| `docs/CANARY_SETUP.md`     | `docs/guides/canary.md`           | Canary setup           |
| `docs/TESTING.md`          | `docs/guides/testing.md`          | Testing guide          |
| `.github/CONTRIBUTING.md`  | `.github/CONTRIBUTING.md`         | Contribution guide     |
| `docs/adr/*.md`            | `docs/adr/`                       | Architecture decisions |
| `docs/modules/*.md`        | `docs/modules/`                   | Module documentation   |
| `docs/ops/*.md`            | `docs/ops/`                       | Operations docs        |
| `docs/analysis/*.md`       | `docs/analysis/`                  | Analysis docs          |

**22. Additional Workflows**

| Source | Target | Purpose |
|--------|--------|---------|
| `hub-production-ci.yml` | `workflows/hub-production-ci.yml` | Hub production CI (lint, test, security) |
| `release.yml` | `workflows/release.yml` | Release automation |

---

### 11.9 Boolean Config Integration Strategy

All integrated tools become simple boolean/config options in `.ci-hub.yml`, following the existing architecture pattern.

#### The Pattern

Every tool follows this structure:

```yaml
# .ci-hub.yml
tools:
  <tool_name>:
    enabled: true/false          # Simple boolean
    # Optional overrides below
```

The CLI:
1. Reads `enabled: true/false`
2. Generates appropriate workflow steps
3. Includes/excludes tool from execution

#### Tool → Boolean Config Mapping

**Existing Tools (Already Boolean)**

| Tool | Config Key | Default |
|------|------------|---------|
| checkstyle | `tools.checkstyle.enabled` | true (Java) |
| spotbugs | `tools.spotbugs.enabled` | true (Java) |
| jacoco | `tools.jacoco.enabled` | true (Java) |
| dependency-check | `tools.dependency_check.enabled` | true |
| ruff | `tools.ruff.enabled` | true (Python) |
| bandit | `tools.bandit.enabled` | true (Python) |
| pytest | `tools.pytest.enabled` | true (Python) |
| trivy | `tools.trivy.enabled` | true |
| semgrep | `tools.semgrep.enabled` | true |

**New Tools to Add (From Root Repo)**

| Tool | Config Key | Default | Source File |
|------|------------|---------|-------------|
| **Mutation Testing** | `tools.mutation.enabled` | false | `mutation_observatory.py` |
| **Chaos Testing** | `resilience.chaos.enabled` | false | `run_chaos.py` |
| **DR Drills** | `resilience.dr.enabled` | false | `run_dr_drill.py` |
| **VEX Generation** | `supply_chain.vex.enabled` | false | `generate_vex.py` |
| **SBOM Generation** | `supply_chain.sbom.enabled` | true | syft integration |
| **Cosign Signing** | `supply_chain.signing.enabled` | false | sign-digest.yml |
| **Rekor Monitoring** | `supply_chain.rekor.enabled` | false | `rekor_monitor.sh` |
| **Provenance** | `supply_chain.provenance.enabled` | true | `verify_provenance.py` |
| **Action Pinning** | `supply_chain.action_pins.enabled` | true | `update_action_pins.py` |
| **Cache Sentinel** | `performance.cache_sentinel.enabled` | false | `cache_sentinel.py` |
| **Predictive Scheduler** | `performance.scheduler.enabled` | false | `predictive_scheduler.py` |
| **Kyverno Policies** | `policies.kyverno.enabled` | false | `kyverno_policy_checker.py` |
| **OPA/Rego Policies** | `policies.opa.enabled` | false | `*.rego` files |
| **Autopsy** | `analysis.autopsy.enabled` | false | `autopsy/analyzer.py` |
| **Telemetry Ingest** | `telemetry.enabled` | false | `chaos_dr_ingest.py` |
| **Determinism Check** | `build.determinism.enabled` | false | `determinism_check.sh` |
| **Egress Control** | `security.egress.enabled` | false | `enforce_egress_control.sh` |
| **Runner Isolation** | `security.runner_isolation.enabled` | true | `check_runner_isolation.py` |
| **Secret Scanning** | `security.secret_scan.enabled` | true | `scan_runtime_secrets.sh` |
| **Ephemeral Labs** | `testing.ephemeral_labs.enabled` | false | `ephemeral_data_lab.py` |
| **dbt Models** | `data.dbt.enabled` | false | `run_dbt.py` |

#### Full `.ci-hub.yml` Schema (After Integration)

```yaml
# .ci-hub.yml - Complete schema with all integrated tools
schema_version: "2.0"

# Core settings
profile: standard  # security | standard | fast
language: java     # java | python | auto

# Standard tools (existing)
tools:
  # Java
  checkstyle:
    enabled: true
    config_file: checkstyle.xml
  spotbugs:
    enabled: true
    effort: max
  jacoco:
    enabled: true
    coverage_min: 70
  dependency_check:
    enabled: true
    fail_on_cvss: 7

  # Python
  ruff:
    enabled: true
  bandit:
    enabled: true
  pytest:
    enabled: true
    coverage_min: 70
  pip_audit:
    enabled: true

  # Universal
  trivy:
    enabled: true
    severity: HIGH,CRITICAL
  semgrep:
    enabled: true

  # Mutation testing (NEW)
  mutation:
    enabled: false            # Off by default (expensive)
    tool: pitest              # pitest | mutmut
    threshold: 70
    target_classes: []        # Empty = all

# Supply chain security (NEW)
supply_chain:
  sbom:
    enabled: true
    format: spdx-json         # spdx-json | cyclonedx
  vex:
    enabled: false
    exemptions_file: .cihub/vex-exemptions.json
  signing:
    enabled: false
    method: cosign-keyless    # cosign-keyless | gpg
  provenance:
    enabled: true
    slsa_level: 3             # 1 | 2 | 3
  rekor:
    enabled: false
  action_pins:
    enabled: true
    auto_update: true

# Resilience testing (NEW)
resilience:
  chaos:
    enabled: false
    config: .cihub/chaos.json
    kill_switch: true
  dr:
    enabled: false
    schedule: weekly          # weekly | monthly | on-demand
    manifest: .cihub/dr-manifest.json

# Performance optimization (NEW)
performance:
  cache_sentinel:
    enabled: false
    quarantine_threshold: 3
  scheduler:
    enabled: false
    optimize_for: time        # time | cost | reliability

# Policy enforcement (NEW)
policies:
  kyverno:
    enabled: false
    policy_dir: .cihub/kyverno/
  opa:
    enabled: false
    policy_dir: .cihub/rego/
  exceptions:
    enabled: false
    max_days: 30

# Security hardening (NEW)
security:
  egress:
    enabled: false
    mode: audit               # audit | warn | enforce
    allowlist: .cihub/egress-allowlist.yaml
  runner_isolation:
    enabled: true
    budget_file: .cihub/runner-budget.yaml
  secret_scan:
    enabled: true
    block_on_find: true

# Build verification (NEW)
build:
  determinism:
    enabled: false
    delay_hours: 24

# Analysis (NEW)
analysis:
  autopsy:
    enabled: false
    rules: default            # default | custom
    rules_file: .cihub/autopsy-rules.yml

# Telemetry & observability (NEW)
telemetry:
  enabled: false
  backend: local              # local | bigquery
  bigquery:
    project: ""
    dataset: ""

# Data quality (NEW)
data:
  dbt:
    enabled: false
    project_dir: models/

# Testing infrastructure (NEW)
testing:
  ephemeral_labs:
    enabled: false
    config: .cihub/ephemeral.yaml
```

#### How Boolean Configs Work in Workflows

The CLI generates workflow steps conditionally:

```yaml
# Generated workflow (simplified)
jobs:
  ci:
    steps:
      # Always runs
      - name: Checkout
        uses: actions/checkout@v4

      # Conditional based on tools.checkstyle.enabled
      {% if config.tools.checkstyle.enabled %}
      - name: Run Checkstyle
        run: mvn checkstyle:check
      {% endif %}

      # Conditional based on supply_chain.signing.enabled
      {% if config.supply_chain.signing.enabled %}
      - name: Sign artifacts
        run: cosign sign --yes ${{ env.IMAGE }}
      {% endif %}

      # Conditional based on resilience.chaos.enabled
      {% if config.resilience.chaos.enabled %}
      - name: Run chaos tests
        run: python -m cihub.tools.chaos.runner --config .cihub/chaos.json
      {% endif %}
```

#### Profiles Pre-Configure Booleans

```yaml
# profiles/security.yaml
tools:
  checkstyle: { enabled: true }
  spotbugs: { enabled: true }
  dependency_check: { enabled: true }
  trivy: { enabled: true }
  semgrep: { enabled: true }
  mutation: { enabled: true }  # Security profile includes mutation

supply_chain:
  sbom: { enabled: true }
  vex: { enabled: true }
  signing: { enabled: true }
  provenance: { enabled: true, slsa_level: 3 }
  rekor: { enabled: true }
  action_pins: { enabled: true }

security:
  egress: { enabled: true, mode: enforce }
  runner_isolation: { enabled: true }
  secret_scan: { enabled: true }

build:
  determinism: { enabled: true }
```

```yaml
# profiles/fast.yaml
tools:
  checkstyle: { enabled: true }
  spotbugs: { enabled: false }  # Skip for speed
  dependency_check: { enabled: false }
  trivy: { enabled: false }
  mutation: { enabled: false }

supply_chain:
  sbom: { enabled: false }
  signing: { enabled: false }
  provenance: { enabled: false }

resilience:
  chaos: { enabled: false }
  dr: { enabled: false }
```

#### CLI Commands

```bash
# Enable a tool
cihub config set tools.mutation.enabled true

# Disable a tool
cihub config set supply_chain.signing.enabled false

# Use a profile (sets many booleans at once)
cihub config set profile security

# Show effective config (with all booleans resolved)
cihub config show --effective

# Validate config
cihub validate
```

#### Schema Validation

Add to `schema/ci-hub-config.schema.json`:

```json
{
  "properties": {
    "supply_chain": {
      "type": "object",
      "properties": {
        "sbom": {
          "type": "object",
          "properties": {
            "enabled": { "type": "boolean", "default": true },
            "format": { "enum": ["spdx-json", "cyclonedx"], "default": "spdx-json" }
          }
        },
        "signing": {
          "type": "object",
          "properties": {
            "enabled": { "type": "boolean", "default": false },
            "method": { "enum": ["cosign-keyless", "gpg"], "default": "cosign-keyless" }
          }
        }
        // ... etc
      }
    },
    "resilience": {
      "type": "object",
      "properties": {
        "chaos": {
          "type": "object",
          "properties": {
            "enabled": { "type": "boolean", "default": false },
            "config": { "type": "string" },
            "kill_switch": { "type": "boolean", "default": true }
          }
        }
        // ... etc
      }
    }
  }
}
```

#### Integration Work Required

| Task | Effort | Priority |
|------|--------|----------|
| Update `ci-hub-config.schema.json` with new sections | Medium | High |
| Add new boolean fields to profile YAML files | Low | High |
| Update template rendering to check new booleans | Medium | High |
| Add `cihub config set` command for easy toggling | Low | Medium |
| Update CLI help/docs with new options | Low | Medium |
| Add validation for dependent options (e.g., rekor requires signing) | Medium | Medium |

---

## Phase 12: Event Ingestion Layer (Control Plane)

### What This Represents

This is not "random Python scripts." This is the **beginning of a control-plane ingestion layer**.

The difference between:
- "We ran a chaos test"
- "We can prove what happened, when, why, and what failed"

**Companies pay for the second one.**

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EVENT INGESTION ARCHITECTURE                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Raw Events                    Ingestion Layer              Storage         │
│  ──────────                    ───────────────              ───────         │
│                                                                             │
│  chaos.yml ──────┐                                                          │
│    events.ndjson │                                                          │
│                  ├───► chaos_dr_ingest.py ───┬───► BigQuery (cloud)         │
│  dr-drill.yml ───┤     - Schema validation   │                              │
│    events.ndjson │     - Run ID tagging      │                              │
│                  │     - Load ID tracking    │                              │
│  pipeline runs ──┤     - Dry-run mode        ├───► Local warehouse          │
│    report.json   │                           │     (artifacts/)             │
│                  │                           │                              │
│  autopsy ────────┤    event_loader.py ───────┤                              │
│    findings.json │     - NDJSON aggregation  │                              │
│                  │     - Summary generation  ├───► Evidence bundle          │
│  telemetry ──────┘     - Warehouse layout    │     (attestation.json)       │
│                                              │                              │
│                                              └───► Dashboards / BI          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `ingest/chaos_dr_ingest.py` | BigQuery loader with schema validation | 267 |
| `ingest/event_loader.py` | Local warehouse aggregator | 112 |

### What Makes This Senior-Level

1. **Structured event model** - Not raw logs, normalized events
2. **Schema validation** - JSON Schema against `dr_drill.event.v1.json`, `pipeline_run.v1.2.json`
3. **Run/Load ID correlation** - Every event traceable to source run
4. **Dry-run mode** - Validate without side effects
5. **Dual output** - Cloud (BigQuery) + local (warehouse)

### Canonical Event Schema

All chaos/DR/security tools should emit events conforming to:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_type", "timestamp", "source"],
  "properties": {
    "event_type": {
      "type": "string",
      "enum": ["chaos_fault", "dr_step", "policy_violation", "security_scan", "build_metric"]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "source": {
      "type": "object",
      "required": ["workflow", "run_id"],
      "properties": {
        "workflow": {"type": "string"},
        "run_id": {"type": "string"},
        "repo": {"type": "string"},
        "commit_sha": {"type": "string"}
      }
    },
    "payload": {
      "type": "object",
      "description": "Event-type-specific data"
    },
    "outcome": {
      "type": "string",
      "enum": ["success", "failure", "skipped", "recovered"]
    },
    "duration_ms": {
      "type": "integer"
    }
  }
}
```

### Integration with Evidence Bundle

The ingestion layer feeds directly into the Phase 10 attestation bundle:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INGESTION → EVIDENCE BUNDLE FLOW                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CI run completes                                                        │
│     └── Generates events.ndjson, report.json                                │
│                                                                             │
│  2. Ingestion layer processes                                               │
│     ├── Validates against schema                                            │
│     ├── Tags with run_id, load_id                                           │
│     └── Writes to warehouse                                                 │
│                                                                             │
│  3. Evidence bundle generator                                               │
│     ├── Reads warehouse/pipeline_runs.ndjson                                │
│     ├── Reads warehouse/chaos_events.ndjson (if present)                    │
│     ├── Reads warehouse/dr_drills.ndjson (if present)                       │
│     └── Packages into attestation-bundle.json                               │
│                                                                             │
│  4. Bundle includes                                                         │
│     ├── results (coverage, mutation, CVEs)                                  │
│     ├── attestations (provenance, SBOM, signature)                          │
│     ├── resilience_evidence (chaos outcomes)        ← NEW                   │
│     └── dr_evidence (recovery metrics)              ← NEW                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### CLI Integration

```yaml
# .ci-hub.yml
resilience:
  enabled: true
  ingest_events: true
  chaos:
    enabled: true
    fault_types: [network, resource, timing]
  dr:
    enabled: true
    schedule: weekly
```

```bash
# CLI commands
cihub ingest --chaos-ndjson artifacts/chaos/events.ndjson
cihub ingest --dr-ndjson artifacts/dr/events.ndjson
cihub ingest --pipeline-run artifacts/report.json
cihub ingest --warehouse ./warehouse --all

# Dry run (validate only)
cihub ingest --dry-run --chaos-ndjson artifacts/chaos/events.ndjson
```

### What This Unlocks

Once events are ingested and normalized:

| Capability | Query |
|------------|-------|
| Correlate chaos → test failures | `WHERE chaos.target = 'maven-central' AND test.outcome = 'failure'` |
| Compute MTTR | `AVG(recovered_at - started_at) WHERE outcome = 'recovered'` |
| Detect flaky chaos | `GROUP BY fault HAVING failure_rate > 0.2 AND success_rate > 0.2` |
| Prove DR drills restored | `WHERE step = 'restore' AND status = 'success'` |
| Track policy violations over time | `GROUP BY policy, week ORDER BY violation_count DESC` |

### Directory Structure

```
cihub/
├── ingestion/
│   ├── __init__.py
│   ├── events.py           # Canonical Event dataclasses
│   ├── schemas/
│   │   ├── event.v1.json   # Base event schema
│   │   ├── chaos.v1.json   # Chaos-specific fields
│   │   ├── dr.v1.json      # DR-specific fields
│   │   └── pipeline.v1.json
│   ├── loaders/
│   │   ├── chaos.py        # chaos_dr_ingest logic
│   │   ├── dr.py
│   │   ├── pipeline.py
│   │   └── base.py         # Common loader interface
│   ├── outputs/
│   │   ├── bigquery.py     # BigQuery writer
│   │   ├── warehouse.py    # Local NDJSON warehouse
│   │   └── bundle.py       # Evidence bundle integration
│   └── cli.py              # cihub ingest command
```

### Phase 12 Decision Points

**Q1: Canonical Event Schema**

| Option | Pros | Cons |
|--------|------|------|
| Define strict schema (Recommended) | Consistent queries, validation | All tools must conform |
| Loose schema + required fields | Flexible, easy adoption | Harder to query |

**Q2: Evidence Bundle Integration**

| Option | Pros | Cons |
|--------|------|------|
| Auto-include in bundle (Recommended) | Complete evidence | Larger bundles |
| Opt-in per event type | Smaller bundles | May miss evidence |

**Q3: Storage Backend**

| Option | Use Case |
|--------|----------|
| BigQuery (cloud) | Production, historical analysis, dashboards |
| Local warehouse (file) | CI artifacts, offline, self-hosted |
| Both (Recommended) | Full coverage |

### What NOT to Add Yet

| Feature | Reason |
|---------|--------|
| Databases (Postgres, etc.) | Keep file-based, deterministic |
| Message queues (Kafka, etc.) | Complexity without need |
| Streaming (real-time) | Batch is sufficient for now |
| External BI integrations | Use BigQuery/warehouse first |

---

## Phase 13: Future Integrations (Deferred)

These are explicitly deferred to maintain focus:

| Feature | Defer Until | Prerequisite |
|---------|-------------|--------------|
| Jira integration | After 10 paying customers | Fleet dashboard working |
| Slack integration | After 10 paying customers | Event ingestion working |
| SSO/RBAC | Enterprise tier | GitHub teams sufficient initially |
| CI time optimizer | After 6 months of telemetry | Need historical data |
| GitLab support | After 10 GitHub customers | Abstract workflow backend |
| Azure DevOps | After GitLab | Same abstraction |
| SaaS hosting | Enterprise demand | Self-hosted proven first |

---

## Resume Positioning

### How to Frame This Project

**For Platform Engineering roles:**

> "Designed and implemented a self-validating CI/CD platform with deterministic drift detection, enabling fleet-wide governance across 50+ repositories. Built event ingestion layer for chaos/DR telemetry with BigQuery integration."

**For Reliability Engineering (SRE) roles:**

> "Built cross-time determinism validation for SLSA Level 4 compliance, automated weekly DR drills with RTO/RPO metrics, and chaos testing infrastructure with MTTR correlation."

**For Security/Compliance roles:**

> "Implemented policy-as-code enforcement with Kyverno, cosign keyless signing with Rekor transparency logs, and audit-ready attestation bundles for SOC2/FedRAMP evidence."

**For DevOps/Developer Productivity roles:**

> "Created CLI tool that reduces CI setup from days to minutes, with auto-generated workflows, schema validation, and one-click fleet updates across repositories."

### Keywords That Matter

| Domain | Keywords |
|--------|----------|
| Platform | Fleet management, drift detection, template rendering, multi-repo orchestration |
| Reliability | Chaos testing, DR drills, MTTR, determinism, reproducible builds |
| Security | SLSA, attestation, provenance, cosign, Sigstore, supply chain, policy-as-code |
| Compliance | Audit trail, evidence bundle, SOC2, FedRAMP, policy exceptions |

---

## Target Repo Types Supported

| Repo Type | Detection | Template | Workflow |
|-----------|-----------|----------|----------|
| Java (Maven) | pom.xml | java-caller.yml.j2 | calls java-ci.yml |
| Java (Gradle) | build.gradle | java-caller.yml.j2 | calls java-ci.yml |
| Python | requirements.txt/pyproject.toml | python-caller.yml.j2 | calls python-ci.yml |
| Monorepo | .ci-hub.yml with subdirs | monorepo-caller.yml.j2 | matrix over subdirs |
| Custom | .ci-hub.yml with custom config | custom template | flexible |

---

## Multi-Language Expansion Strategy

> **Future scope** — Add after current blockers (hub-orchestrator, hub-security) are resolved.

Production-grade approach to add more languages without exceeding the GitHub Actions 25-input dispatch limit (see ADR-0024):

### Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| Per-language workflows | Each language gets its own reusable workflow + caller template |
| Lean caller inputs | Keep to ~20 inputs max: version, workdir, correlation_id, tool booleans |
| Config-first thresholds | Thresholds stay in `config/.ci-hub.yml`; single `threshold_overrides_yaml` input |
| No mega-dispatch | Route via orchestrator to per-language callers, not a single shared caller |
| Hardcode defaults | If a tool is always on, hardcode it in the workflow instead of adding an input |

### Adding a New Language Checklist

1. **Schema/Config**
   - Add language fields under `language.tools.*` in schema
   - Set defaults in `config/defaults.yaml`

2. **Workflows**
   - Create `.github/workflows/<lang>-ci.yml` (reusable workflow)
   - Create `templates/repo/hub-<lang>-ci.yml` (caller template)
   - Keep caller inputs lean (essential booleans + workdir + version)

3. **Orchestrator**
   - Update orchestrator to route to new language workflow
   - Pass only booleans and essentials (no thresholds)

4. **Gating/Reports**
   - Reuse existing enforcement/summary/report patterns
   - Share `scripts/` helpers to avoid divergence

5. **Docs/Tests**
   - Update CONFIG_REFERENCE, TOOLS documentation
   - Add template tests to `tests/test_templates.py`
   - Update ONBOARDING guide

### Input Budget Per Caller

| Category | Max Inputs | Examples |
|----------|------------|----------|
| Core | 3 | version, workdir, correlation_id |
| Tool booleans | ~15 | run_tests, run_lint, run_security, etc. |
| Override | 1 | threshold_overrides_yaml |
| Reserved | ~1 | Future expansion |
| **Total** | **~20** | Stay under 25 limit |

### What NOT to Do

- ❌ Create a single mega-dispatch with all languages
- ❌ Add per-language threshold inputs to dispatch
- ❌ Add tool toggles that are always on (hardcode instead)
- ❌ Skip schema/config/docs updates when adding a language

---

## Drift Prevention

| Check | Script/Tool | Catches |
|-------|-------------|---------|
| Config vs Ran | validate_summary.py | Tool was configured but didn't run |
| Summary vs Report | validate_summary.py | Summary claims don't match report.json |
| Artifacts vs Ran | validate_summary.py | Says tool ran but no artifact |
| Schema vs Inputs | test_contract_consistency.py | Workflow inputs drift from schema |
| POM vs Config | cihub validate | POM plugins don't match .ci-hub.yml |
| Workflow vs Config | cihub validate | Workflow inputs don't match .ci-hub.yml |

---

## Key Design Principles

1. **CLI is the single entry point** - All human operations go through `cihub`
2. **Templates are rendered** - Not static files, generated from Jinja2
3. **Reusable workflows for execution** - Actual CI logic lives in hub
4. **Composite actions for shared logic** - Report generation, validation
5. **Scripts are testable** - All logic in Python, unit tested
6. **Schema is source of truth** - Validates config, reports, everything
7. **Self-validating** - CLI validates everything it generates
8. **Profiles for quick setup** - Security, standard, fast presets
9. **Update capability** - Like Copier, can update existing projects

---

## References

- [Cookiecutter vs Yeoman](https://www.cookiecutter.io/article-post/compare-cookiecutter-to-yeoman)
- [Copier - Update existing projects](https://www.cookiecutter.io/article-post/cookiecutter-alternatives)
- [12 Scaffolding Tools](https://www.resourcely.io/post/12-scaffolding-tools)
- [YAML Linting Best Practices](https://www.mavjs.org/post/yaml-linting-schema-validation/)
- [Maven 4 CI-Friendly Variables](https://maven.apache.org/whatsnewinmaven4.html)
- [Yeoman Generator Testing](https://yeoman.io/)

---

## Related ADRs

- ADR-0002: Config Precedence
- ADR-0003: Dispatch and Orchestration
- ADR-0004: Aggregation and Reporting
- ADR-0023: Deterministic Correlation
- ADR-0024: Workflow Dispatch Input Limit
