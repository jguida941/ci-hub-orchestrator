# ADR-0021: Java POM Compatibility and CLI Enforcement

**Status**: Accepted  
**Date:** 2025-12-24  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The CI/CD Hub relies on Java projects having properly configured `pom.xml` files with the correct Maven plugins (JaCoCo, Checkstyle, SpotBugs, PMD, etc.). When repos are missing these plugins or have them only in `<pluginManagement>` (which defines config but doesn't execute), the CI tools don't run correctly. Tool enablement is driven by `.ci-hub.yml` booleans, so required plugins must be derived from config, not hard-coded assumptions.

Problems encountered:
1. **Multi-module projects**: Plugins in `<pluginManagement>` don't execute - they must be in `<plugins>`
2. **Missing plugins**: Repos without JaCoCo get 0% coverage; repos without Checkstyle skip linting
3. **Version drift**: Different repos use different plugin versions causing inconsistent behavior
4. **Manual setup burden**: Users must manually configure pom.xml correctly

The CLI tool (`cihub`) already handles onboarding for `.ci-hub.yml` and caller workflows. Extending it to handle pom.xml setup provides a complete onboarding solution.

## Decision

### 1. Maven Only in v1.0

Focus on Maven projects first. Gradle support deferred to v1.1+.

### 2. Required Plugins (Config-Driven)

The following plugins are required when the corresponding tool is enabled in `.ci-hub.yml`:

| Plugin | Purpose | Enabled by Default |
|--------|---------|--------------------|
| `jacoco-maven-plugin` | Code coverage | Yes |
| `maven-checkstyle-plugin` | Code style | Yes |
| `spotbugs-maven-plugin` | Bug detection | Yes |
| `maven-pmd-plugin` | Static analysis | Yes |
| `dependency-check-maven` | OWASP vulnerability scan | Yes |
| `pitest-maven` | Mutation testing | Yes |

### 3. Multi-Module Rules

For multi-module Maven projects:
- Parent POM must have plugins in `<build><plugins>` section (not only `<pluginManagement>`)
- This ensures plugins execute on all modules
- Child modules inherit plugin execution from parent

### 4. CLI Commands

```bash
# Full onboarding - config + workflow, then optional pom.xml fix
cihub init --repo . --language java

# Validate config + pom.xml (warn by default)
cihub validate --repo .

# Fix pom.xml only (standalone)
cihub fix-pom --repo . [--dry-run]

# Fix dependencies only (standalone)
cihub fix-deps --repo . [--dry-run]
```

### 5. CLI Behavior

**`cihub validate`**:
- Read `.ci-hub.yml` booleans to determine which plugins are required
- Warn by default if plugins are missing or only in `<pluginManagement>`
- `--strict` flag to fail on missing plugins
- Check multi-module structure

**`cihub fix-pom`**:
- `--dry-run` shows what would change (default behavior without flag)
- `--apply` to actually modify pom.xml
- Never overwrites existing plugin config
- Only adds missing plugin stubs for enabled tools
- Handles multi-module: adds to parent pom's `<plugins>` section
- Does not manage repo-specific files (e.g., `checkstyle.xml`) or rule sets
- Also applies dependency fixes for enabled tools (see below)

**`cihub init`**:
- Includes pom.xml validation and optional fix
- Prompts user if pom.xml needs changes
- `--fix-pom` flag to auto-fix without prompting

### 6. Dependency Management (Config-Driven)

Some tools require dependencies rather than Maven plugins. The CLI handles these separately:

- `cihub fix-deps` adds missing dependencies for enabled tools (currently `jqwik`)
- `cihub fix-pom` runs both plugin and dependency fixes
- Dependencies are added to module `pom.xml` files for multi-module projects

### 7. Tools Without POM Changes

The following tools do not require pom.xml changes because they run in GitHub Actions:
- CodeQL
- Semgrep
- Trivy
- Docker

### 8. Plugin Versions

Lock to specific versions defined in hub's `templates/java/pom-plugins.xml`:
- JaCoCo: 0.8.11
- Checkstyle: 3.3.1
- SpotBugs: 4.8.3.1
- PMD: 3.23.0
- OWASP: 9.0.9
- PITest: 1.15.3

### 9. Dependency Versions

Lock to specific versions defined in hub's `templates/java/pom-dependencies.xml`:
- jqwik: 1.8.4

These align with versions in `docs/guides/GETTING_STARTED.md`.

## Consequences

### Positive
- Complete onboarding with single command
- Consistent plugin configuration across repos
- Early detection of pom.xml issues via `validate`
- Reduced manual setup burden

### Negative
- CLI complexity increases
- Must maintain plugin version list
- Maven-only initially (Gradle users must configure manually)

### Neutral
- Existing repos may need one-time `fix-pom` run
- Fixture repos serve as test cases for pom.xml handling

## Testing

Test against fixture repos:
- `ci-cd-hub-fixtures` - Contains Java passing/failing configs
- `java-spring-tutorials` - Multi-module Maven project

CLI integration tests:
- `tests/test_cli_integration.py` exercises `cihub init/update/fix-pom` against a local clone of `ci-cd-hub-fixtures`
- Tests copy a fixture subdir into a temp repo, then run CLI commands and assert plugin/dependency insertion
- Set `CIHUB_FIXTURES_PATH=/path/to/ci-cd-hub-fixtures` if the repo isn't located next to `hub-release`

Verification steps:
1. `cihub validate --repo .` detects missing plugins
2. `cihub fix-pom --repo . --dry-run` shows correct changes
3. `cihub fix-pom --repo . --apply` adds plugins without breaking build
4. CI run passes after fix

## Related

- ADR-0010: Dispatch Token and Skip
- ADR-0014: Reusable Workflow Migration
- `docs/guides/GETTING_STARTED.md` - User-facing plugin documentation
