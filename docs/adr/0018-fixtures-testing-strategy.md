# ADR-0018: Fixtures & Testing Strategy

**Status**: Accepted  
**Date:** 2025-12-18  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-25  

## Context

The CI/CD Hub needs test fixtures to validate:
1. Reusable workflows produce correct reports
2. Tool integrations work across languages
3. Threshold enforcement behaves correctly
4. Docker/Trivy scanning works when Dockerfiles present

The fixtures live in a separate repository (`ci-cd-hub-fixtures`) and are tested via workflow dispatch.

## Decision

### 1. Fixture Repository Structure

```
ci-cd-hub-fixtures/
├── .github/workflows/
│   ├── hub-python-ci.yml    # Caller for Python fixtures
│   └── hub-java-ci.yml      # Caller for Java fixtures
├── python-passing/          # Clean Python code, all tests pass
├── python-failing/          # Python with intentional issues
├── python-with-docker/      # Python + Dockerfile for Trivy/Docker
├── java-passing/            # Clean Java code, all tests pass
├── java-failing/            # Java with intentional issues
└── java-with-docker/        # Java + Dockerfile for Trivy/Docker
```

### 2. Fixture Intent

| Fixture | Expected Result | Purpose |
|---------|-----------------|---------|
| `python-passing` | All checks pass | Validates happy path |
| `python-failing` | Has findings | Validates detection (relaxed thresholds) |
| `python-with-docker` | Docker/Trivy run | Validates container scanning |
| `java-passing` | All checks pass | Validates happy path |
| `java-failing` | Has findings | Validates detection (relaxed thresholds) |
| `java-with-docker` | Docker/Trivy run | Validates container scanning |

### 3. Branching Strategy

**Fixtures workflows stay on a test branch** (`test-phase1b-schema`), not default branch.

Rationale:
- `workflow_dispatch` from GitHub API requires workflow to exist on target branch
- Test branch allows iterating without affecting `main`
- Trigger via `--ref test-phase1b-schema`

```bash
# Trigger fixture run
gh workflow run hub-python-ci.yml \
  --repo jguida941/ci-cd-hub-fixtures \
  --ref test-phase1b-schema
```

### 4. Caller Configuration

Each caller workflow tests multiple fixtures with appropriate configurations:

```yaml
jobs:
  ci-passing:
    name: "Python Passing"
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@v1
    with:
      workdir: 'python-passing'
      artifact_prefix: 'python-passing-'
      # Default thresholds
    secrets: inherit

  ci-failing:
    name: "Python Failing"
    uses: ...
    with:
      workdir: 'python-failing'
      artifact_prefix: 'python-failing-'
      # Relaxed thresholds to allow findings
      coverage_min: 0
      mutation_score_min: 0
      max_high_vulns: 999
      max_semgrep_findings: 999

  ci-docker:
    name: "Python Docker"
    uses: ...
    with:
      workdir: 'python-with-docker'
      artifact_prefix: 'python-docker-'
      run_trivy: true
      run_docker: true
      # Relaxed code quality (focus is Docker/Trivy)
      max_high_vulns: 10
      max_semgrep_findings: 10
```

### 5. Docker Fixture Scope

**Decision**: Keep non-docker fixtures clean (no Dockerfiles).

| Fixture Type | Has Dockerfile | Purpose |
|--------------|----------------|---------|
| `*-passing` | No | Core code quality validation |
| `*-failing` | No | Core code quality validation |
| `*-with-docker` | Yes | Container scanning validation |

Rationale: Adding Dockerfiles everywhere would distort coverage for code quality cases. Container scanning is a separate concern tested by dedicated fixtures.

### 6. Validation Criteria

After each fixture run, validate:

| Check | Expected |
|-------|----------|
| `schema_version` | `"2.0"` |
| `tests_passed` | > 0 for passing fixtures |
| `tool_metrics` | Populated (not all null) |
| `tools_ran` | Matches input flags |
| Artifacts | Unique names with prefix |

```bash
# Download and validate
gh run download <run-id> -n python-passing-ci-report
jq '.schema_version, .results.tests_passed, .tool_metrics' report.json
```

### 7. Change Control

When to update fixtures:
- After workflow schema changes (new fields in report.json)
- After adding/removing tool inputs
- After threshold logic changes
- After fixing tool integration bugs

Process:
1. Make changes to hub workflows on feature branch
2. Update fixture callers to reference feature branch
3. Run fixtures, validate reports
4. Merge hub changes to main
5. Update fixture callers to reference `@v1` (or new tag)
6. Optionally merge fixtures to main (if test branch strategy changes)

## Consequences

### Positive

- Clear separation of fixture concerns (passing/failing/docker)
- Branch-based testing allows iteration without breaking main
- Artifact prefixes prevent collisions
- Each fixture has documented expected behavior

### Negative

- Fixtures on test branch require `--ref` to trigger
- Multiple jobs per workflow increases CI time
- Must remember to update fixture callers when tagging releases

## Relaxed Thresholds Documentation

### Python Fixtures

**python-passing:**
```yaml
mutation_score_min: 0  # mutmut config detection being fixed
# All other thresholds at default (coverage_min: 70, etc.)
```

**python-failing:**
```yaml
coverage_min: 0           # Intentional low coverage
mutation_score_min: 0     # Expected to have low score
max_critical_vulns: 999   # Allow findings to be captured
max_high_vulns: 999       # Allow findings to be captured
max_semgrep_findings: 999 # Semgrep finds issues - we want to see them, not fail
```

**python-with-docker:**
```yaml
max_high_vulns: 10        # Focus is Docker/Trivy, not code quality
max_semgrep_findings: 10  # Focus is Docker/Trivy, not code quality
# run_mutmut: false       # Skip mutation testing for speed
```

### Java Fixtures

**java-passing:**
```yaml
# Default thresholds (coverage_min: 70, etc.)
# mutation_score_min: 0 handled by workflow's non-blocking pitest
```

**java-failing:**
```yaml
coverage_min: 0           # Intentional low coverage
mutation_score_min: 0     # Expected to have low score
owasp_cvss_fail: 11       # 11 > max CVSS (10), so never fails - allows capturing
max_critical_vulns: 999   # Allow findings to be captured
max_high_vulns: 999       # Allow findings to be captured
max_semgrep_findings: 999 # Semgrep finds issues - we want to see them, not fail
max_pmd_violations: 999   # PMD finds violations - we want to see them, not fail
```

**java-with-docker:**
```yaml
max_high_vulns: 10        # Focus is Docker/Trivy, not code quality
max_semgrep_findings: 10  # Focus is Docker/Trivy, not code quality
# run_pitest: false       # Skip mutation testing for speed
```

### Summary Table

| Fixture | coverage | mutation | critical | high | semgrep | pmd | owasp |
|---------|----------|----------|----------|------|---------|-----|-------|
| python-passing | 70 | 0* | 0 | 0 | 0 | N/A | N/A |
| python-failing | 0 | 0 | 999 | 999 | 999 | N/A | N/A |
| python-docker | 70 | N/A | 0 | 10 | 10 | N/A | N/A |
| java-passing | 70 | 0* | 0 | 0 | 0 | 0 | 7 |
| java-failing | 0 | 0 | 999 | 999 | 999 | 999 | 11 |
| java-docker | 70 | N/A | 0 | 10 | 10 | 0 | 7 |

`*` = Relaxed due to tool configuration issues (TODO: restore to 70 when fixed)
`N/A` = Tool disabled for this fixture

### TODO: Restore When Fixed

1. **mutation_score_min** on passing fixtures: Set to 70 once mutmut/pitest configuration is working
2. **Investigate** why python-docker has bandit/semgrep findings (inherited from python-passing copy)
3. **Consider** whether docker fixtures should run all tools or just Docker/Trivy

## Related ADRs

- ADR-0008: Hub Fixtures Strategy
- ADR-0014: Reusable Workflow Migration
- ADR-0016: Mutation Testing Policy

---

## Addendum (2025-12-25): Expanded Fixture Matrix

The fixture naming scheme has been expanded to encode language, build system, layout, and outcome:

**New naming convention:**
- `java-maven-pass`, `java-maven-fail` - Maven projects
- `java-gradle-pass`, `java-gradle-fail` - Gradle projects
- `python-pyproject-pass`, `python-pyproject-fail` - pyproject.toml projects
- `python-setup-pass`, `python-setup-fail` - setup.py projects
- `python-src-layout-pass` - src/ layout
- `java-multi-module-pass` - Multi-module Maven
- `monorepo-pass/java`, `monorepo-fail/java` - Monorepo subdirs

**Heavy tool fixtures (optional):**
Heavy tools (Trivy, CodeQL) are off by default for speed. Optional `fixtures-*-heavy.yaml` configs enable them for nightly/release validation.

See `docs/development/execution/SMOKE_TEST.md` for the full matrix and naming convention.
