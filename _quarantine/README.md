# _quarantine - Cold Storage for Unintegrated Files

> **THIS IS NOT EXECUTABLE CODE. DO NOT IMPORT FROM HERE.**

## Rules (Non-Negotiable)

1. **No imports** - CI fails if any file imports from `_quarantine`
2. **No CLI wiring** - Files here don't exist to the CLI
3. **No tests** - Tests cannot import from here
4. **Exit ticket required** - Every file has documented graduation criteria

## What This Is

Cold storage for files copied from the root repo that need integration into `cihub/`.

Files stay here until:
- Target location is decided
- Imports are fixed
- Unit tests pass
- No circular dependencies
- Ownership category is clear

## What This Is NOT

- A runtime namespace
- A temporary shortcut
- A place for "I'll fix it later"

## Graduation Process

1. Check `INTEGRATION_STATUS.md` for the file's exit ticket
2. Create target directory in `cihub/` if needed
3. Use `git mv` to move file to final location
4. Fix all imports (relative to new location)
5. Add/update tests
6. Update `INTEGRATION_STATUS.md` status
7. Commit with message: `feat(integration): graduate <filename> to cihub/<target>/`

## Categories

Files will graduate to one of:
- `cihub/tools/` - Standalone tools (mutation, chaos, dr, etc.)
- `cihub/validators/` - Validation scripts
- `cihub/runners/` - Execution wrappers
- `cihub/ingestion/` - Data ingestion
- `cihub/autopsy/` - Failure analysis
- `scripts/` - Standalone scripts (not part of cihub package)
- `policies/` - Rego/Kyverno policies
- `config/` - Configuration files
- `schema/` - JSON schemas

## Enforcement

```bash
# CI runs this - hard fail if ANY import from _quarantine
python scripts/check_quarantine_imports.py
```

## When Empty

When this directory contains only this README, integration is complete.
Delete the directory at that point.
