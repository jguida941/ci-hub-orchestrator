# ADR-0017: Scanner Tool Defaults

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

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
| `max_black_issues` | 0 | Zero tolerance for formatting |
| `max_isort_issues` | 0 | Zero tolerance for import order |
| `max_ruff_errors` | 0 | Zero tolerance for lint errors |
| `owasp_cvss_fail` | 7.0 | High severity |

### 3a. Relaxed Thresholds for Test Fixtures

The `*-failing` fixtures use relaxed thresholds to verify tool detection works correctly:

```yaml
# Relaxed thresholds (accept failures for testing detection)
coverage_min: 0
mutation_score_min: 0
max_critical_vulns: 999
max_high_vulns: 999
max_semgrep_findings: 999
max_black_issues: 999
max_isort_issues: 999
max_ruff_errors: 999
```

**Purpose**: Failing fixtures intentionally contain issues (bad formatting, lint errors, security issues). Relaxed thresholds allow the CI to complete and generate full reports showing detected issues.

### 3b. Production Verification Strategy

**Problem**: How do users verify their CI pipeline is correctly detecting issues?

**Solution - Dual Fixture Approach**:

1. **Passing Fixture** (`*-passing`): Clean code that should pass all checks with strict thresholds
2. **Failing Fixture** (`*-failing`): Intentionally bad code with relaxed thresholds

**What users should check**:

| Fixture | Expected Behavior |
|---------|-------------------|
| `*-passing` | All jobs pass, no issues detected |
| `*-failing` | All jobs complete, issues detected in reports |

**Verification checklist for failing fixture**:
- [ ] Black reports formatting issues (`black_issues > 0`)
- [ ] Ruff reports lint errors (`ruff_errors > 0`)
- [ ] Bandit reports security issues (`bandit_high > 0` or `bandit_medium > 0`)
- [ ] Coverage shows low % (`coverage < 70`)
- [ ] Semgrep reports findings (when enabled)
- [ ] Report artifacts contain issue counts

**Template approach**: Users can use the fixture caller workflows as templates. The `ci-passing` job shows strict production settings; the `ci-failing` job shows relaxed testing settings.

### 3c. Automated Report Validation

To ensure CI pipelines are working correctly, fixture workflows include validation jobs that assert report.json contents. Validation FAILS (not warns) when expectations aren't met.

**Validation job structure**:

```yaml
validate-passing:
  name: "Validate Passing Report"
  runs-on: ubuntu-latest
  needs: ci-passing
  if: always()
  steps:
    - name: Download Report
      uses: actions/download-artifact@v4
      with:
        name: python-passing-ci-report
        path: ./report

    - name: Validate Report Structure
      run: |
        REPORT="./report/report.json"
        ERRORS=0
        # Assert schema_version == "2.0"
        # Assert tests_passed > 0, tests_failed == 0
        # Assert coverage >= 70%
        # Assert ALL tools_ran.* == true for enabled tools
        # Assert ALL tool_metrics.* are populated (not null)
        # Assert lint/security issues == 0
        if [ "$ERRORS" -gt 0 ]; then exit 1; fi
```

**Validation checks by fixture type**:

| Check | Passing Fixture | Failing Fixture |
|-------|-----------------|-----------------|
| `schema_version` | Must be "2.0" | Must be "2.0" |
| `tests_passed` | > 0 | > 0 |
| `tests_failed` | Must be 0 | Any (expected failures) |
| `coverage` | >= 70% | Any value |
| `tools_ran.*` | ALL enabled tools must be `true` | ALL enabled tools must be `true` |
| `tool_metrics.*` | ALL must be populated (not null) | ALL must be populated (not null) |
| `tool_metrics.black_issues` | Must be 0 | Must be > 0 (FAIL if no issues) |
| `tool_metrics.ruff_errors` | Must be 0 | > 0 (expected) |
| `tool_metrics.checkstyle_errors` | Must be 0 (Java) | > 0 (expected, Java) |

**Python tools validated**: pytest, ruff, bandit, pip_audit, mypy, black, isort, mutmut, semgrep, trivy, docker, codeql

**Java tools validated**: jacoco, checkstyle, spotbugs, owasp, pitest, pmd, semgrep, trivy, docker, codeql

**Key principles**:
1. Validation FAILS when expectations aren't met - no silent warnings
2. Failing fixtures MUST detect issues - if they don't, the fixture was cleaned unintentionally
3. Failing fixtures stay confined to the fixtures repo - never copy relaxed thresholds to production
4. Production callers use passing fixture as template with strict thresholds

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

**Problem**: When tests fail, Maven stops before running analysis plugins. Even with `-fn` (fail-never), explicit goals appended to the command line don't run after lifecycle failure.

**Solution**: Split the build into two phases:

```yaml
- name: Build and Test
  continue-on-error: true  # Let workflow continue
  run: |
    # Phase 1: Run build lifecycle (may fail on tests)
    mvn -B -ntp verify || echo "Build completed with errors"

    # Phase 2: Run analysis tools separately with -DskipTests
    # This ensures they run even if tests failed above
    mvn -B -ntp -DskipTests checkstyle:checkstyle spotbugs:spotbugs dependency-check:check
```

**Why two phases?**
- Maven's `-fn` flag doesn't prevent explicit goals from being skipped when lifecycle fails
- Running analysis goals separately with `-DskipTests` ensures they execute regardless of test results
- Each phase uses `|| echo "..."` or `|| true` to allow the workflow to continue

**Python equivalent**: `pytest ... || true` already handles this.

**Rationale**: CI should capture all findings (test failures, static analysis issues, vulnerabilities) even when some checks fail. Threshold enforcement happens in later steps.

### 7a. OWASP NVD API Rate Limiting

**Problem**: OWASP Dependency Check downloads vulnerability data from the NVD API. Without rate limiting, bulk downloads trigger 403 errors due to NVD rate limits (even without an API key).

**Solution**: Add delay and retry parameters to avoid rate limiting:

```yaml
mvn -B -ntp -DskipTests \
  -DnvdApiDelay=2500 \
  -DnvdMaxRetryCount=10 \
  -Ddependencycheck.failOnError=false \
  dependency-check:check
```

**Flag explanations**:
- `-DnvdApiDelay=2500`: 2.5 second delay between NVD API calls (avoids rate limiting)
- `-DnvdMaxRetryCount=10`: Retry failed API calls up to 10 times
- `-Ddependencycheck.failOnError=false`: Don't fail the build if vulnerabilities are found

**Notes**:
- This works without an NVD API key, just slower due to rate limiting
- With an NVD API key (set as `NVD_API_KEY` secret), downloads are faster
- See: https://nvd.nist.gov/developers/request-an-api-key
- Reference: https://github.com/dependency-check/DependencyCheck/issues/6330

### 7b. PITest and -DskipTests

**Problem**: PITest mutation testing was showing 0% because the command included `-DskipTests`:

```bash
# WRONG: PITest skips because tests are disabled
mvn test-compile org.pitest:pitest-maven:mutationCoverage -DskipTests
```

PITest needs to run tests to detect which mutations are killed.

**Solution**: Remove `-DskipTests` from PITest invocation:

```bash
# CORRECT: PITest runs tests internally to detect killed mutations
mvn test-compile org.pitest:pitest-maven:mutationCoverage
```

**Note**: `test-compile` ensures test classes exist before PITest runs.

### 7c. PITest Requires Passing Tests ("Green Suite")

**Important**: PITest requires all tests to pass before mutation testing can run. If any tests fail, PITest exits with error:

```
7 tests did not pass without mutation when calculating line coverage.
Mutation testing requires a green suite.
```

**Implications for fixtures**:
- `java-passing` / `python-passing`: PITest/mutmut runs and generates mutation scores
- `java-failing` / `python-failing`: PITest/mutmut cannot run (tests intentionally fail)
- This is expected behavior, not a bug

**Rationale**: Mutation testing detects "killed" mutations by checking if tests fail when code is mutated. If tests already fail, there's no baseline to compare against.

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

## TODO: User-Facing Documentation

Once workflows are stable, create user-facing documentation with:

### Tool Versions Reference

| Language | Tool | Plugin/Package | Version |
|----------|------|----------------|---------|
| Java | OWASP Dependency Check | dependency-check-maven | 12.1.9 |
| Java | SpotBugs | spotbugs-maven-plugin | 4.8.3.1 |
| Java | PITest | pitest-maven | 1.15.3 |
| Java | Checkstyle | maven-checkstyle-plugin | 3.3.1 |
| Java | PMD | maven-pmd-plugin | 3.21.2 |
| Java | JaCoCo | jacoco-maven-plugin | 0.8.11 |
| Python | pytest | pytest | latest |
| Python | Ruff | ruff | latest |
| Python | Bandit | bandit | latest |
| Python | pip-audit | pip-audit | latest |
| Python | mutmut | mutmut | latest |
| Universal | Semgrep | semgrep | latest |
| Universal | Trivy | aquasecurity/trivy-action | 0.28.0 |
| Universal | CodeQL | github/codeql-action | v3 |

### Documentation Deliverables

1. **Quick Start Guide**: Minimal caller workflow example
2. **Tool Reference**: All tools, versions, and what they check
3. **Threshold Reference**: Default values and how to customize
4. **Troubleshooting**: Common issues (PITest green suite, OWASP rate limiting, etc.)
5. **Upgrade Notes**: When tool versions change

### Version Pinning Strategy

- Java Maven plugins: Pinned in fixture pom.xml files (callers use their own versions)
- GitHub Actions: Pinned to major versions (@v3, @v4) for stability
- Python tools: Use latest via pip (caller's environment)

## Related ADRs

- ADR-0006: Quality Gates Thresholds
- ADR-0016: Mutation Testing Policy
