# ADR-0016: Mutation Testing Policy

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

Mutation testing (mutmut for Python, PITest for Java) is valuable for measuring test quality but has challenges:

1. **Performance**: Can take 10-15 minutes per run
2. **Flakiness**: Some mutations cause infinite loops or timeouts
3. **Configuration complexity**: Requires correct source path detection
4. **Blocking vs warning**: Should failures block the build or just warn?

Current state (2025-12-18):
- `run_mutmut` and `run_pitest` default to `true`
- Both use `continue-on-error: true` (failures warn but don't block)
- Mutation score threshold defaults to 70%
- mutmut respects pyproject.toml `[tool.mutmut]` config when present

## Decision

### 1. Default State: Enabled but Non-Blocking

| Tool | Default Enabled | Default Blocking |
|------|-----------------|------------------|
| mutmut (Python) | `true` | `false` (warn only) |
| PITest (Java) | `true` | `false` (warn only) |

**Rationale**: Teams should see mutation scores in reports without immediately being blocked. This allows gradual adoption.

### 2. Enforcement Levels

Callers can choose enforcement level:

**Advisory (default)**: Run and report, never fail
```yaml
run_mutmut: true
mutation_score_min: 0  # Any score acceptable
```

**Warning**: Run and warn if below threshold (current behavior)
```yaml
run_mutmut: true
mutation_score_min: 70  # Warn if below 70%
# continue-on-error: true (in workflow)
```

**Strict**: Fail if below threshold (remove continue-on-error)
```yaml
run_mutmut: true
mutation_score_min: 70
# Requires workflow change to remove continue-on-error
```

### 3. Configuration Detection

The workflow should respect project configuration when present:

| File | Section | Behavior |
|------|---------|----------|
| `pyproject.toml` | `[tool.mutmut]` | Use project config, don't override paths |
| `pom.xml` | `<plugin>pitest-maven</plugin>` | Use project config |
| None | N/A | Use workflow defaults |

### 4. Timeout and Performance

| Setting | Value | Rationale |
|---------|-------|-----------|
| Timeout | 15 minutes | Prevents infinite loops from blocking CI |
| Runner | `pytest -x -q` (Python) | Fail fast on first test failure |
| Threads | Default (auto) | Let tools optimize |

### 5. Score Calculation

```
Mutation Score = (Killed Mutants / Total Mutants) × 100
```

| Score | Rating |
|-------|--------|
| 80-100% | Excellent |
| 60-79% | Good |
| 40-59% | Needs improvement |
| <40% | Poor |

## Consequences

### Positive

- Teams get visibility into test quality without being blocked
- Gradual adoption path (advisory → warning → strict)
- Respects existing project configuration
- Timeout prevents runaway builds

### Negative

- Non-blocking default means mutation failures can be ignored
- Score of 0% can indicate config issues, not actual test quality
- Performance impact on CI (10-15 min for mutation testing)

## Implementation

### Python (mutmut 3.x)

**Important:** mutmut 3.x removed CLI flags. All configuration must be in pyproject.toml.

**pyproject.toml configuration (required):**

```toml
[tool.mutmut]
paths_to_mutate = ["src/"]          # Array format required in 3.x
tests_dir = ["tests/"]              # Array format required in 3.x
also_copy = ["scripts/", "config/"] # Additional dirs needed by tests
```

**Workflow usage:**

```yaml
- name: Run mutmut
  run: mutmut run  # 3.x reads all config from pyproject.toml
  continue-on-error: true
  timeout-minutes: 15
```

**Version differences (2.x vs 3.x):**

| Feature | mutmut 2.x | mutmut 3.x |
|---------|------------|------------|
| CLI paths | `--paths-to-mutate src/` | N/A (use pyproject.toml) |
| CLI runner | `--runner "pytest -x"` | N/A (hardcoded pytest) |
| Config format | strings or arrays | arrays only |
| Import handling | N/A | `also_copy` for extra dirs |

**Common issue:** If tests import modules outside `paths_to_mutate` (e.g., `scripts/`),
add them to `also_copy` or tests will fail with `ModuleNotFoundError`.

**This project's configuration:**

```toml
[tool.mutmut]
paths_to_mutate = ["cihub/"]
tests_dir = ["tests/"]
also_copy = ["scripts/", "config/", "schema/", "templates/", ".github/"]
```

Directories required because tests:
- `scripts/`: Import aggregate_reports, load_config, validate_summary
- `config/`: Load defaults.yaml, repo configs
- `schema/`: Validate against JSON schemas
- `templates/`: Load template files (.ci-hub.yml, workflows)
- `.github/`: Validate workflow YAML files

### Java (PITest)

```yaml
- name: Run PITest
  run: mvn test-compile org.pitest:pitest-maven:mutationCoverage
  continue-on-error: true
  timeout-minutes: 15
```

## Migration Path

For teams wanting strict enforcement:

1. Start with `mutation_score_min: 0` (advisory)
2. Monitor scores in reports for baseline
3. Set realistic threshold (e.g., 50%)
4. Request workflow modification to remove `continue-on-error` if needed

## Related ADRs

- ADR-0006: Quality Gates Thresholds
- ADR-0014: Reusable Workflow Migration
