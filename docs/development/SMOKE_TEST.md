# Smoke Test Guide

This document describes how to run smoke tests for the CI/CD Hub to verify it's working correctly before release.

---

## Overview

The smoke test validates the hub's core functionality by running it against minimal test repositories (one Java, one Python). It verifies:

- Repository discovery and config loading
- Language detection
- Tool execution (core tools only, with heavy tools disabled for speed)
- Artifact generation
- Summary report generation
- Pass/fail detection

---

## Prerequisites

### 1. GitHub Secrets

The hub requires these secrets to be configured in the repository settings:

| Secret Name | Required For | Description |
|-------------|--------------|-------------|
| `GITHUB_TOKEN` | All runs | Automatically provided by GitHub Actions (no setup needed) |
| `NVD_API_KEY` | Java OWASP scans | Optional - NVD API key for dependency vulnerability scanning. Can skip if `owasp.enabled: false` |

### 2. Repository Permissions

Ensure the GitHub Actions token has these permissions:

- `actions: read` - To read workflow status
- `contents: read` - To clone repositories
- `security-events: write` - For security scanning results (if enabled)

### 3. Test Repositories

The smoke test uses these repositories (configured in `config/repos/`):

**Java:**
- Repository: `jguida941/java-spring-tutorials`
- Branch: `main`
- Config: `config/repos/smoke-test-java.yaml`
- Tools enabled: JaCoCo (coverage), Checkstyle, SpotBugs
- Tools disabled: OWASP, PITest (mutation), CodeQL, Docker

**Python:**
- Repository: `jguida941/ci-cd-bst-demo-github-actions`
- Branch: `main`
- Config: `config/repos/smoke-test-python.yaml`
- Tools enabled: pytest (with coverage), Ruff, Black
- Tools disabled: Bandit, pip-audit, mypy, CodeQL, Docker

Both test repos have relaxed thresholds:
- Coverage minimum: 50% (vs 70% default)
- Mutation score: 0% (disabled)
- Max vulnerabilities: 100 (relaxed)

**Fixtures option (recommended for predictability):**
If you push a dedicated fixtures repo (`jguida941/ci-cd-hub-fixtures`) containing `java-passing`, `java-failing`, `python-passing`, `python-failing`, point the hub configs to:
- `config/repos/fixtures-java-passing.yaml`
- `config/repos/fixtures-java-failing.yaml`
- `config/repos/fixtures-python-passing.yaml`
- `config/repos/fixtures-python-failing.yaml`

---

## Running the Smoke Test

### Method 1: Manual Workflow Dispatch (Recommended)

1. Navigate to the **Actions** tab in GitHub
2. Select the **"Smoke Test"** workflow
3. Click **"Run workflow"**
4. Choose options:
   - **Branch**: Select branch to test (usually `main` or `master`)
   - **Skip mutation testing**: Leave checked (default - faster)
5. Click **"Run workflow"** to start

The workflow will run for approximately 5-10 minutes.

### Method 2: Using GitHub CLI

```bash
# From the hub-release directory
gh workflow run smoke-test.yml

# Or with specific inputs
gh workflow run smoke-test.yml \
  --field skip_mutation=true
```

### Method 3: Trigger via Hub Run All Workflow

You can also use the main hub workflow with specific repos:

```bash
gh workflow run hub-run-all.yml \
  --field repos="smoke-test-java,smoke-test-python" \
  --field skip_mutation=true
```

---

## Expected Outcomes

### Success Criteria

A successful smoke test should produce:

#### 1. Workflow Completion
- Both test-repo jobs complete (may have warnings, should not fail entirely)
- Summary job completes successfully
- Overall workflow status: Success (green)

#### 2. Repository Discovery
- Discover job finds 2 repositories
- Matrix contains both smoke-test-java and smoke-test-python

#### 3. Java Repository Results
The smoke-test-java job should generate:
- Test execution metrics (total, passed, failed)
- JaCoCo coverage report (XML + HTML)
- Checkstyle results (may have violations - that's OK)
- SpotBugs results (may have bugs - that's OK)
- Step summary with metrics table

Expected artifacts:
- `reports-java-spring-tutorials/` containing:
  - `target/surefire-reports/` (test results)
  - `target/site/jacoco/` (coverage HTML)
  - `target/checkstyle-result.xml`
  - `target/spotbugsXml.xml`

#### 4. Python Repository Results
The smoke-test-python job should generate:
- pytest execution results
- Coverage report (coverage.xml)
- Ruff lint results (may have issues - that's OK)
- Black format check results
- Step summary with metrics table

Expected artifacts:
- `reports-ci-cd-bst-demo-github-actions/` containing:
  - `coverage.xml`
  - `htmlcov/` (coverage HTML)
  - `ruff-report.json`
  - Test output

#### 5. Hub Summary
The summary job should display:
- Total repositories: 2
- Run number and trigger info
- Links to individual job summaries

---

## Verifying Success

### Check 1: Workflow Status
```bash
# List recent workflow runs
gh run list --workflow=smoke-test.yml --limit=5

# View details of latest run
gh run view --log
```

Expected: Status = "completed", Conclusion = "success"

### Check 2: Step Summaries

1. Go to the Actions tab
2. Click on the latest smoke test run
3. Check each job's summary:
   - **test-java**: Should show QA Metrics table with coverage %, test counts, and quality gates
   - **test-python**: Should show QA Metrics table with pytest results, coverage %, and lint status
   - **summary**: Should show hub summary with repo count

### Check 3: Artifacts

1. In the workflow run page, scroll to the bottom
2. Verify artifacts are uploaded:
   - `reports-java-spring-tutorials` (should contain test/coverage/tool outputs)
   - `reports-ci-cd-bst-demo-github-actions` (should contain coverage and reports)

Download and inspect to ensure they contain actual data (not empty files).

### Check 4: Logs

Inspect logs for each job to verify:

**Java job:**
```
- Maven build completed
- Tests executed (may have failures - check they're detected)
- JaCoCo coverage calculated
- Checkstyle ran
- SpotBugs ran
- Metrics extracted and displayed
```

**Python job:**
```
- Dependencies installed
- pytest ran with coverage
- Coverage calculated
- Ruff linting completed
- Black format check completed
- Metrics extracted and displayed
```

---

## Troubleshooting

### Common Issues

#### Issue: "No repositories found"

**Symptom:** Discover job shows count=0

**Solution:**
1. Check that `config/repos/smoke-test-*.yaml` files exist
2. Verify YAML syntax is correct
3. Ensure `repo.name` and `repo.owner` fields are set

#### Issue: "Repository not found" or "Authentication failed"

**Symptom:** Checkout step fails with 404 or auth error

**Solution:**
1. Verify the test repositories exist and are accessible:
   - `https://github.com/jguida941/java-spring-tutorials`
   - `https://github.com/jguida941/ci-cd-bst-demo-github-actions`
2. Check repository visibility (public repos don't need auth)
3. If private, ensure GITHUB_TOKEN has access

#### Issue: Java build fails

**Symptom:** Maven verify step fails

**Solution:**
1. This may be expected if the repo has failing tests
2. Check if tests are genuinely broken or if it's a known issue
3. Smoke test uses `continue-on-error: true` so it should still produce reports
4. Verify JDK version matches repo requirements (currently set to JDK 21)

#### Issue: Python tests fail

**Symptom:** pytest step fails

**Solution:**
1. Check if repo has requirements.txt or pyproject.toml
2. Verify Python version compatibility (currently set to 3.12)
3. Check if dependencies installed correctly
4. Smoke test uses `continue-on-error: true` so it should still produce coverage

#### Issue: No artifacts uploaded

**Symptom:** No artifacts appear in workflow run

**Solution:**
1. Check if tools actually generated reports
2. Look for errors in tool execution steps
3. Verify artifact paths match actual output locations
4. Check `if-no-files-found: ignore` is set (so workflow doesn't fail)

#### Issue: OWASP or other tool still running despite being disabled

**Symptom:** Heavy tools run even though config says `enabled: false`

**Solution:**
1. Verify the smoke test configs have the tool disabled
2. Check if `hub-run-all.yml` respects the config toggles
3. Current implementation may run all tools - config toggle support is being added

---

## What to Test Manually

After the automated smoke test passes, manually verify:

### 1. Config Override Hierarchy

Test that config precedence works:
1. Modify `config/repos/smoke-test-java.yaml` to set `jacoco.min_coverage: 100`
2. Run smoke test
3. Verify build fails due to coverage threshold
4. Revert change

### 2. Tool Toggle Behavior

Test disabling/enabling tools:
1. Edit smoke test config to enable PITest (`pitest.enabled: true`)
2. Run smoke test without skip_mutation flag
3. Verify mutation testing runs and appears in summary
4. Revert change

### 3. Failure Detection

Test that hub detects failures:
1. Temporarily point smoke-test-java to a repo with failing tests
2. Run smoke test
3. Verify job completes but summary shows failures
4. Revert change

### 4. Artifact Retention

Verify artifacts are stored:
1. Run smoke test
2. Wait 24 hours
3. Check that artifacts are still available (retention is 30 days)

---

## Smoke Test Configuration Files

### Java: `config/repos/smoke-test-java.yaml`

```yaml
repo:
  owner: jguida941
  name: java-spring-tutorials
  language: java
  default_branch: main

java:
  version: "21"
  tools:
    jacoco:
      enabled: true
      min_coverage: 50
    checkstyle:
      enabled: true
      fail_on_violation: false
    spotbugs:
      enabled: true
      fail_on_error: false
    owasp:
      enabled: false  # Skip for speed
    pitest:
      enabled: false  # Skip for speed
    codeql:
      enabled: false
    docker:
      enabled: false

thresholds:
  coverage_min: 50
  mutation_score_min: 0
  max_critical_vulns: 100
  max_high_vulns: 100
```

### Python: `config/repos/smoke-test-python.yaml`

```yaml
repo:
  owner: jguida941
  name: ci-cd-bst-demo-github-actions
  language: python
  default_branch: main

python:
  version: "3.12"
  tools:
    pytest:
      enabled: true
      min_coverage: 50
      fail_fast: false
    ruff:
      enabled: true
      fail_on_error: false
    bandit:
      enabled: false
    pip_audit:
      enabled: false
    mypy:
      enabled: false
    black:
      enabled: true
    codeql:
      enabled: false
    docker:
      enabled: false

thresholds:
  coverage_min: 50
  mutation_score_min: 0
  max_critical_vulns: 100
  max_high_vulns: 100
```

---

## Success Metrics

### Minimum Acceptance Criteria

For a smoke test to pass, it MUST demonstrate:

1. ✅ **Discovery works**: 2 repositories discovered
2. ✅ **Java CI runs**: Tests execute, coverage generated, tools run
3. ✅ **Python CI runs**: pytest runs, coverage generated, linting works
4. ✅ **Artifacts uploaded**: Both repos produce artifacts
5. ✅ **Summaries generated**: Step summaries show metrics tables
6. ✅ **Hub summary works**: Final summary job completes

### Quality Expectations (Nice-to-Have)

These are desirable but not required for initial smoke test:

- Coverage above 50% for both repos
- Zero critical vulnerabilities (if OWASP/pip-audit enabled)
- Zero high-severity security issues
- Clean style checks (Checkstyle/Ruff passing)
- All tests passing (no failures)

---

## Real Smoke Test Requirements

For a production smoke test, you would need:

### Ideal Test Repositories

**Java Repository Requirements:**
- Small Spring Boot or plain Java project
- Has at least 10 unit tests
- Achieves 70%+ line coverage
- Has clean Checkstyle/SpotBugs results
- No known vulnerabilities
- Maven-based build
- Public or accessible to hub

**Python Repository Requirements:**
- Small Flask/FastAPI or library project
- Has pytest tests with markers
- Achieves 70%+ coverage
- Clean Ruff/Black formatting
- Has type hints for mypy
- No dependency vulnerabilities
- Public or accessible to hub

### Alternative: Create Fixture Repos

Consider creating dedicated fixture repositories:
- `ci-cd-hub-fixtures/java-smoke-test` - Minimal passing Java app
- `ci-cd-hub-fixtures/python-smoke-test` - Minimal passing Python app

These would be purpose-built for testing and could include:
- Known test counts
- Known coverage percentages
- Intentional style violations (to test detection)
- Intentional security issues (to test scanning)

---

## Next Steps

After smoke test passes:

1. ✅ Mark smoke test checkbox in `hub-release/requirements/P0.md`
2. Run smoke test on CI/CD (not just manually)
3. Add smoke test to pre-release checklist
4. Document smoke test in release notes
5. Consider adding smoke test to PR checks (on config changes)

---

## References

- [P0 Requirements](../../requirements/P0.md) - Smoke test acceptance criteria
- [Workflows Reference](../guides/WORKFLOWS.md) - Hub workflow documentation
- [Config Reference](../reference/CONFIG_REFERENCE.md) - Configuration options
- [Tools Reference](../reference/TOOLS.md) - Tool descriptions and outputs
