# Smoke Test Repository Requirements

This document describes the repositories used for smoke testing the CI/CD Hub.

---

## Current Smoke Test Repositories

### Java Repository

**Repository:** `jguida941/java-spring-tutorials`
- **URL:** https://github.com/jguida941/java-spring-tutorials
- **Branch:** `main`
- **Language:** Java
- **Build Tool:** Maven
- **Config:** `config/repos/smoke-test-java.yaml`

**Purpose:** Tests Java CI pipeline functionality including:
- Maven build and test execution
- JaCoCo code coverage generation
- Checkstyle code style checks
- SpotBugs static analysis

**Tools Enabled:**
- ✅ JaCoCo (min_coverage: 50%)
- ✅ Checkstyle (non-blocking)
- ✅ SpotBugs (non-blocking)

**Tools Disabled (for speed):**
- ❌ OWASP Dependency Check
- ❌ PITest (mutation testing)
- ❌ CodeQL
- ❌ Docker

**Thresholds:**
- Coverage minimum: 50% (relaxed from default 70%)
- Mutation score: 0% (disabled)
- Max critical vulnerabilities: 100 (relaxed)
- Max high vulnerabilities: 100 (relaxed)

---

### Python Repository

**Repository:** `jguida941/ci-cd-bst-demo-github-actions`
- **URL:** https://github.com/jguida941/ci-cd-bst-demo-github-actions
- **Branch:** `main`
- **Language:** Python
- **Test Framework:** pytest
- **Config:** `config/repos/smoke-test-python.yaml`

**Purpose:** Tests Python CI pipeline functionality including:
- pytest test execution with coverage
- Ruff linting and security checks
- Black code formatting validation

**Tools Enabled:**
- ✅ pytest (min_coverage: 50%)
- ✅ Ruff (non-blocking)
- ✅ Black

**Tools Disabled (for speed):**
- ❌ Bandit security scanner
- ❌ pip-audit dependency scanner
- ❌ mypy type checking
- ❌ CodeQL
- ❌ Docker

**Thresholds:**
- Coverage minimum: 50% (relaxed from default 70%)
- Mutation score: 0% (disabled)
- Max critical vulnerabilities: 100 (relaxed)
- Max high vulnerabilities: 100 (relaxed)

---

## Repository Accessibility

Both repositories are:
- ✅ **Public** - No authentication required
- ✅ **Actively maintained** - Part of jguida941's portfolio
- ✅ **Accessible** - Can be cloned by GitHub Actions without special permissions

---

## In-Repo Fixture Option (recommended for predictability)

The dedicated fixtures repository (`jguida941/ci-cd-hub-fixtures`) contains subdirs for each fixture scenario:

**Core fixtures:**
- `java-maven-pass` / `java-maven-fail` - Maven projects
- `python-pyproject-pass` / `python-pyproject-fail` - pyproject.toml projects

**Extended fixtures (see `docs/development/execution/SMOKE_TEST.md`):**
- `java-gradle-pass` / `java-gradle-fail` - Gradle projects
- `python-setup-pass` / `python-setup-fail` - setup.py projects
- `python-src-layout-pass` - src/ layout
- `java-multi-module-pass` - Multi-module Maven
- `monorepo-pass/java`, `monorepo-pass/python` - Mixed repo subdirs

Hub configs point to these subdirs via `repo.subdir`. Source repo: https://github.com/jguida941/ci-cd-hub-fixtures

---

## Requirements for Alternative Smoke Test Repos

If you want to use different repositories for smoke testing, they should meet these criteria:

### Java Repository Requirements

**Minimum:**
- Maven or Gradle based project
- Contains compilable Java code
- Has at least a few unit tests
- Tests can execute successfully (or predictably)
- JaCoCo plugin configured (or can use hub's default)

**Ideal:**
- 10+ unit tests
- 50%+ code coverage
- Clean Checkstyle results
- No critical SpotBugs issues
- Fast build time (< 5 minutes)

**Example Structure:**
```
my-java-repo/
├── pom.xml (or build.gradle)
├── src/
│   ├── main/java/
│   │   └── com/example/
│   │       └── MyClass.java
│   └── test/java/
│       └── com/example/
│           └── MyClassTest.java
└── README.md
```

### Python Repository Requirements

**Minimum:**
- Python 3.8+ compatible
- Has requirements.txt or pyproject.toml
- Contains Python source code
- Has pytest tests
- Tests can execute successfully

**Ideal:**
- 10+ pytest tests
- 50%+ code coverage
- Clean Ruff lint results
- Black formatted code
- Fast test execution (< 5 minutes)

**Example Structure:**
```
my-python-repo/
├── pyproject.toml (or setup.py + requirements.txt)
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── module.py
├── tests/
│   ├── __init__.py
│   └── test_module.py
└── README.md
```

---

## Creating Purpose-Built Smoke Test Repos

For the most reliable smoke tests, consider creating dedicated fixture repositories:

### Suggested: `ci-cd-hub-fixtures/java-smoke-test`

**Features:**
- Minimal Spring Boot application
- Exactly 10 unit tests (for predictable counts)
- Exactly 70% code coverage (meets threshold)
- Zero Checkstyle violations
- Zero SpotBugs issues
- No dependencies with vulnerabilities
- Fast build (under 2 minutes)

**Benefits:**
- Predictable results
- Known baseline metrics
- No external dependencies breaking tests
- Complete control over test scenarios

### Suggested: `ci-cd-hub-fixtures/python-smoke-test`

**Features:**
- Simple Python library or Flask app
- Exactly 10 pytest tests
- Exactly 70% code coverage
- Zero Ruff violations
- Fully Black formatted
- Type hints for mypy
- No vulnerable dependencies

**Benefits:**
- Predictable results
- Known baseline metrics
- Fast test execution
- Complete control

---

## Configuration Template

If creating new smoke test repos, use this config template:

### Java Config Template

```yaml
repo:
  owner: YOUR_ORG
  name: YOUR_REPO
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
      enabled: false  # Disabled for smoke test speed
    pitest:
      enabled: false  # Disabled for smoke test speed
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

### Python Config Template

```yaml
repo:
  owner: YOUR_ORG
  name: YOUR_REPO
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
    black:
      enabled: true
    bandit:
      enabled: false  # Disabled for smoke test speed
    pip_audit:
      enabled: false  # Disabled for smoke test speed
    mypy:
      enabled: false
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

## Verifying Repository Compatibility

Before using a repository for smoke tests, verify:

### 1. Repository Exists and is Accessible

```bash
gh repo view OWNER/REPO --json name,defaultBranchRef,isPrivate
```

Expected output:
- `name`: Repository name
- `defaultBranchRef.name`: Branch name (should match config)
- `isPrivate`: `false` (for public repos) or ensure hub has access

### 2. Java Repository Has Required Files

```bash
gh repo view OWNER/REPO --json files
```

Required:
- `pom.xml` (Maven) or `build.gradle` (Gradle)
- Source files in `src/main/java/`
- Test files in `src/test/java/`

### 3. Python Repository Has Required Files

```bash
gh repo view OWNER/REPO --json files
```

Required:
- `requirements.txt` or `pyproject.toml`
- Python source files (`.py`)
- Test files (`test_*.py` or `*_test.py`)

### 4. Tests Can Run

Clone the repository locally and verify:

**Java:**
```bash
git clone https://github.com/OWNER/REPO
cd REPO
./mvnw test  # or: mvn test
```

**Python:**
```bash
git clone https://github.com/OWNER/REPO
cd REPO
pip install -r requirements.txt
pytest
```

---

## Troubleshooting

### "Repository not found" error

**Cause:** Repository doesn't exist or hub lacks access

**Solution:**
1. Verify repository URL: `gh repo view OWNER/REPO`
2. Check repository visibility (public vs private)
3. If private, ensure GITHUB_TOKEN has access
4. Verify owner and name in config match exactly

### "No tests found" error

**Java:**
- Ensure tests are in `src/test/java/`
- Test classes should end with `Test.java` or `Tests.java`
- Tests should use JUnit annotations (`@Test`)

**Python:**
- Ensure test files start with `test_` or end with `_test.py`
- Test functions should start with `test_`
- Tests should be in a `tests/` directory or alongside source

### "Coverage not generated" error

**Java:**
- Ensure JaCoCo plugin is in `pom.xml`
- Or rely on hub's default configuration
- Check that tests actually execute

**Python:**
- Ensure pytest-cov is installed
- Verify coverage.xml is generated after pytest runs
- Check pytest is finding source files to measure

---

## Next Steps

1. ✅ Verify current smoke test repos are accessible
2. ✅ Run smoke test workflow: `gh workflow run smoke-test.yml`
3. ✅ Check smoke test results and artifacts
4. Consider creating purpose-built fixture repos for predictable results
5. Update smoke test configs as repos evolve

---

## References

- [Smoke Test Guide](SMOKE_TEST.md) - How to run smoke tests
- [Config Reference](../reference/CONFIG_REFERENCE.md) - Configuration options
- [Workflows Reference](../guides/WORKFLOWS.md) - Workflow documentation
