# ADR-0025: CLI Modular Restructure with Interactive Wizard

**Status**: Accepted  
**Date:** 2025-12-25  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The current `cihub/cli.py` is a 1,688-line monolithic file with 8 commands. As we add more features (wizard onboarding, config management, workflow generation), this structure becomes unmaintainable.

Additionally, onboarding new repos requires manual YAML editing. Users need an interactive wizard to configure repos without memorizing config schema.

**Core Principle:** "Target repos stay clean" - The hub manages config; target repos don't need hub-specific files unless explicitly opted in.

## Decision

**Restructure the CLI into modular components with an optional interactive wizard.**

### Module Structure

```
cihub/
├── cli.py                    # Entry point + argparse (reduced to routing)
├── config/                   # Config management
│   ├── io.py                 # YAML I/O
│   ├── merge.py              # Deep merge
│   ├── schema.py             # JSON schema validation
│   └── paths.py              # PathConfig (exists)
├── commands/                 # Command implementations
│   ├── new.py                # Create hub-side config for new repo
│   ├── config_cmd.py         # Config management (show/set/enable/disable)
│   └── ... (existing commands extracted)
└── wizard/                   # Interactive prompts (optional dependency)
    ├── core.py               # WizardRunner
    ├── styles.py             # Centralized questionary+Rich theme
    ├── validators.py         # Input validation
    ├── summary.py            # Rich config summary display
    └── questions/            # Per-category question modules
```

### Soft Dependencies

The wizard uses `questionary` (prompts) and `rich` (pretty output) as **optional dependencies**:

```toml
[project.optional-dependencies]
wizard = ["questionary>=2.0.0", "rich>=13.0.0"]
```

Install with: `pip install cihub[wizard]`

Without wizard deps, CLI works but `--interactive` flags show a helpful error.

### Two Essential Booleans

| Boolean | Purpose | Default |
|---------|---------|---------|
| `use_central_runner` | Central (hub clones) vs distributed (dispatch to repo) | `true` |
| `repo_side_execution` | Enable workflow generation into target repos | `false` |

Both are per-repo settings under `repo.*` in config. `repo_side_execution: false` ensures target repos stay clean by default.

### New Commands (MVP)

| Command | Purpose | Writes to |
|---------|---------|-----------|
| `cihub new <repo>` | Create hub-side config for a repo | `config/repos/<repo>.yaml` |
| `cihub config show` | Display merged config | (read-only) |
| `cihub config set <path> <value>` | Set config value | `config/repos/<repo>.yaml` |
| `cihub config enable <tool>` | Enable a tool | `config/repos/<repo>.yaml` |
| `cihub config disable <tool>` | Disable a tool | `config/repos/<repo>.yaml` |

All operations write to hub-side config only. No writes to target repos in MVP.

## Alternatives Considered

1. **Typer/Click instead of argparse:**
   Rejected: argparse works and is stdlib. No benefit to switching.

2. **Full scaffolding (create files in target repos):**
   Deferred: Conflicts with "repos stay clean" principle. See ADR-0026 for opt-in workflow generation.

3. **Single wizard library (only Rich or only questionary):**
   Rejected: questionary excels at prompts, Rich at output. Separation of concerns.

4. **Required wizard dependencies:**
   Rejected: Forces installation for users who only want non-interactive CLI.

## Consequences

**Positive:**
- Maintainable modular structure
- Optional wizard for interactive onboarding
- Consistent with existing hub-side config approach
- Testable command modules
- Graceful degradation without wizard deps

**Negative:**
- More files to navigate
- Optional deps add installation complexity
- Must keep wizard in sync with schema changes

## Implementation

### Phase 1: Foundation
- Add wizard optional deps to pyproject.toml
- Add `use_central_runner` and `repo_side_execution` to schema/defaults/docs

### Phase 2: Config Module
- Extract YAML I/O to `cihub/config/io.py`
- Move deep merge to `cihub/config/merge.py`
- Add schema validation in `cihub/config/schema.py`

### Phase 3: Wizard Module
- Create `wizard/` with styles, validators, core, summary
- Add question modules for language/tools/security/thresholds

### Phase 4: Commands Refactor
- Extract existing commands to `cihub/commands/`
- Add `--wizard` flag to `init` command

### Phase 5: New Commands
- Implement `cihub new` (hub-side only)
- Implement `cihub config` subcommands

## References

- ADR-0026: Repo-Side Execution Guardrails (placeholder for future opt-in)
- `docs/development/architecture/ARCHITECTURE_PLAN.md` - Full architecture plan
- [questionary PyPI](https://pypi.org/project/questionary/)
- [Rich library](https://rich.readthedocs.io/)
