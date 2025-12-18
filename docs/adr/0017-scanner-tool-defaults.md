# ADR-0017: Scanner Tool Defaults

- Status: Accepted
- Date: 2025-12-18

## Context

The CI/CD Hub workflows include multiple security and quality scanners. Some are fast and cheap to run; others are expensive (time, compute, rate limits). We need a clear policy for which tools are enabled by default.

Questions to resolve:
1. Which scanners should be on by default?
2. How to categorize tools (cheap vs expensive)?
3. What thresholds should apply by default?

## Decision

### 1. Tool Categories

**Core Tools (default: enabled)**
These run on every build by default - they're fast and essential:

| Language | Tool | Purpose | Approx Time |
|----------|------|---------|-------------|
| Python | pytest | Tests | 1-5 min |
| Python | ruff | Linting | <30s |
| Python | black | Formatting | <30s |
| Python | isort | Import sorting | <30s |
| Python | bandit | Security (fast) | <1 min |
| Python | pip-audit | Dependency vulnerabilities | <1 min |
| Java | maven/gradle | Build + tests | 2-5 min |
| Java | JaCoCo | Coverage | Included |
| Java | Checkstyle | Style | <30s |
| Java | SpotBugs | Bugs | <1 min |
| Java | PMD | Code analysis | <1 min |
| Java | OWASP | Dependencies | 2-5 min |

**Expensive Tools (default: disabled)**
These require explicit opt-in due to cost/time:

| Tool | Why Expensive | Default |
|------|--------------|---------|
| Semgrep | 2-5 min, external service | `false` |
| Trivy | 2-5 min, requires Dockerfile | `false` |
| CodeQL | 5-15 min, GitHub compute | `false` |
| Docker Build | 2-10 min, requires Dockerfile | `false` |
| mutmut/PITest | 10-15 min | `true` (but non-blocking) |

### 2. Default Input Values

**Python CI:**
```yaml
run_pytest: true        # Core
run_ruff: true          # Core
run_black: true         # Core
run_isort: true         # Core
run_bandit: true        # Core
run_pip_audit: true     # Core
run_mypy: false         # Opt-in (strict typing)
run_mutmut: true        # Enabled but non-blocking
run_semgrep: false      # Expensive
run_trivy: false        # Expensive + needs Dockerfile
run_codeql: false       # Expensive
run_docker: false       # Expensive + needs Dockerfile
```

**Java CI:**
```yaml
run_jacoco: true        # Core
run_checkstyle: true    # Core
run_spotbugs: true      # Core
run_pmd: true           # Core
run_owasp: true         # Core (but slower)
run_pitest: true        # Enabled but non-blocking
run_semgrep: false      # Expensive
run_trivy: false        # Expensive + needs Dockerfile
run_codeql: false       # Expensive
run_docker: false       # Expensive + needs Dockerfile
```

### 3. Default Thresholds

| Threshold | Default | Rationale |
|-----------|---------|-----------|
| `coverage_min` | 70% | Industry standard |
| `mutation_score_min` | 70% | High but advisory |
| `max_critical_vulns` | 0 | Zero tolerance for critical |
| `max_high_vulns` | 0 | Zero tolerance for high |
| `max_semgrep_findings` | 0 | Fail on any finding (when enabled) |
| `owasp_cvss_fail` | 7.0 | High severity |

### 4. Enabling Expensive Tools

To enable expensive tools, callers explicitly set flags:

```yaml
jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      run_semgrep: true      # Opt-in
      run_trivy: true        # Opt-in (only if Dockerfile exists)
      run_codeql: true       # Opt-in
```

### 5. Tool Skip Behavior

Tools gracefully skip when preconditions aren't met:

| Tool | Skip Condition |
|------|----------------|
| Trivy | No Dockerfile present |
| Docker Build | No Dockerfile present |
| OWASP | No pom.xml/build.gradle |
| pip-audit | No requirements.txt/pyproject.toml |

### 6. Java Maven Plugin Execution

**Important**: Maven plugins like Checkstyle, SpotBugs, and OWASP must be explicitly invoked with goals, not just configured in pom.xml. The `-Dcheckstyle.skip=false` flag only works if the plugin is already bound to a build phase via `<executions>`.

**Workflow must call plugin goals explicitly:**

```yaml
# WRONG: Only skips if plugin is already bound to a phase
mvn verify -Dcheckstyle.skip=false -Dspotbugs.skip=false

# CORRECT: Explicitly invoke plugin goals
mvn verify checkstyle:checkstyle spotbugs:spotbugs dependency-check:check
```

**Goal mapping:**

| Tool | Maven Goal |
|------|------------|
| Checkstyle | `checkstyle:checkstyle` |
| SpotBugs | `spotbugs:spotbugs` |
| PMD | `pmd:pmd` |
| OWASP | `dependency-check:check` |
| PITest | `pitest:mutationCoverage` |

**Alternative**: Add `<executions>` to pom.xml to bind plugins to `verify` phase, but this requires changes to every project's pom.xml.

### 7. Continue-on-Error Strategy

**Problem**: When tests fail, Maven stops before running analysis plugins. This prevents report generation.

**Solution**: Use Maven's `-fn` (fail-never) flag:

```yaml
- name: Build and Test
  continue-on-error: true  # Let workflow continue
  run: |
    # -fn continues despite errors, allowing all reports to generate
    mvn -B -ntp -fn verify checkstyle:checkstyle spotbugs:spotbugs || true
```

**Python equivalent**: `pytest ... || true` already handles this.

**Rationale**: CI should capture all findings (test failures, static analysis issues, vulnerabilities) even when some checks fail. Threshold enforcement happens in later steps.

### 8. Dependent Job Execution with `if: always()`

**Problem**: When using `continue-on-error: true` on steps, the individual steps continue but the **job** is still marked as `failure` if any step fails. This causes dependent jobs (with `needs: build-test`) to be **skipped** by default.

**Solution**: Add `if: always() && inputs.run_<tool>` to dependent jobs:

```yaml
mutation-test:
  name: Mutation Testing
  runs-on: ubuntu-latest
  needs: build-test
  if: always() && inputs.run_pitest  # Runs even if build-test fails
```

**Jobs requiring `if: always()`**:
- `mutation-test` - PITest/mutmut runs after build, needs test classes
- `pmd` - PMD analysis runs after build
- `semgrep` - SAST scan runs after build
- `trivy` - Container scan runs after build
- `docker-build` - Docker build runs after build

**Why not use `if: always()` alone?**
- `if: always()` alone would run the job even when it's disabled via inputs
- `if: always() && inputs.run_<tool>` respects the user's tool toggle while still running when build fails

**Note**: The `report` job already uses `if: always()` to generate the final report regardless of upstream failures.

## Consequences

### Positive

- Fast default builds (core tools only)
- Expensive tools are opt-in (no surprise bills/timeouts)
- Graceful degradation when preconditions missing
- Clear documentation of what runs by default

### Negative

- Some security tools not on by default
- Teams must explicitly enable Semgrep/Trivy/CodeQL
- Different experiences between basic and full scans

## Guidance for Teams

### Recommended Configurations

**Minimum (default)**:
All core tools, fast builds, essential coverage.

**Security-Focused**:
```yaml
run_semgrep: true
run_trivy: true  # If Dockerfile exists
run_codeql: true
```

**Full Suite**:
```yaml
run_semgrep: true
run_trivy: true
run_codeql: true
run_docker: true
run_mypy: true  # Python
```

## Related ADRs

- ADR-0006: Quality Gates Thresholds
- ADR-0016: Mutation Testing Policy
