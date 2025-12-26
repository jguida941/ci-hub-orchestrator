# Tools Reference

Comprehensive documentation for all quality, security, and testing tools supported by the CI/CD Hub.

> **Important:** Tools have different availability depending on execution mode. See the status columns carefully.

---

## Tool Availability Matrix

### Legend
- **Wired + Toggle**: Tool runs, controlled by config toggle
- **Not Wired**: Tool not implemented in this mode

> **Verification:** Central mode tools are in `hub-run-all.yml`. Grep for tool names to verify.
>
> **Note:** Central mode now reads config via `load_config.py` and gates ALL tools based on `enabled: true/false` settings.

### Java Tools

| Tool | Central Mode | Distributed Mode | Config Toggle | Status |
|------|--------------|-------------------|---------------|--------|
| JaCoCo | Wired + Toggle | Wired + Toggle | `java.tools.jacoco.enabled` | Production |
| Checkstyle | Wired + Toggle | Wired + Toggle | `java.tools.checkstyle.enabled` | Production |
| SpotBugs | Wired + Toggle | Wired + Toggle | `java.tools.spotbugs.enabled` | Production |
| PMD | Wired + Toggle | Wired + Toggle | `java.tools.pmd.enabled` | Production |
| OWASP DC | Wired + Toggle | Wired + Toggle | `java.tools.owasp.enabled` | Production |
| PITest | Wired + Toggle | Wired + Toggle | `java.tools.pitest.enabled` | Production |
| jqwik | Not Wired | Wired + Toggle | `java.tools.jqwik.enabled` | Dispatch-only |
| CodeQL | Wired + Toggle | Wired + Toggle | `java.tools.codeql.enabled` | Production |
| Semgrep | Wired + Toggle | Wired + Toggle | `java.tools.semgrep.enabled` | Production |
| Trivy | Wired + Toggle | Wired + Toggle | `java.tools.trivy.enabled` | Production |

### Python Tools

| Tool | Central Mode | Distributed Mode | Config Toggle | Status |
|------|--------------|-------------------|---------------|--------|
| pytest + coverage | Wired + Toggle | Wired + Toggle | `python.tools.pytest.enabled` | Production |
| Ruff | Wired + Toggle | Wired + Toggle | `python.tools.ruff.enabled` | Production |
| Bandit | Wired + Toggle | Wired + Toggle | `python.tools.bandit.enabled` | Production |
| pip-audit | Wired + Toggle | Wired + Toggle | `python.tools.pip_audit.enabled` | Production |
| Black | Wired + Toggle | Wired + Toggle | `python.tools.black.enabled` | Production |
| isort | Wired + Toggle | Wired + Toggle | `python.tools.isort.enabled` | Production |
| mypy | Wired + Toggle | Wired + Toggle | `python.tools.mypy.enabled` | Production |
| mutmut | Wired + Toggle | Wired + Toggle | `python.tools.mutmut.enabled` | Production |
| Hypothesis | Wired + Toggle | Wired + Toggle | `python.tools.hypothesis.enabled` | Production |
| Semgrep | Wired + Toggle | Wired + Toggle | `python.tools.semgrep.enabled` | Production |
| Trivy | Wired + Toggle | Wired + Toggle | `python.tools.trivy.enabled` | Production |
| CodeQL | Wired + Toggle | Wired + Toggle | `python.tools.codeql.enabled` | Production |

### Universal Tools

| Tool | Central Mode | Distributed Mode | When Runs | Status |
|------|--------------|-------------------|-----------|--------|
| Semgrep | Wired + Toggle | Wired + Toggle | If `*.tools.semgrep.enabled` | Production |
| Trivy | Wired + Toggle | Wired + Toggle | If `*.tools.trivy.enabled` | Production |

---

## Execution Modes Explained

### Central Mode (`hub-run-all.yml`)
- Hub clones your repo and runs tools directly
- Tools are controlled by config toggles (`enabled: true/false`)
- Config is loaded via `scripts/load_config.py` at runtime
- Hub controls aggregation, summaries, and artifact uploads
- **Recommended for most users**

### Reusable Workflows (`java-ci.yml`, `python-ci.yml`)
- Called from your repo's workflow or via distributed dispatch
- Tools controlled by workflow inputs and config toggles
- Tool coverage matches the reusable workflow inputs
- Used for distributed mode or repo-local CI

---

## Java Tools (Detailed)

### JaCoCo (Code Coverage)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Measures which lines of code are executed by tests. Reports line, branch, and instruction coverage.

**Prerequisites:**
- Maven: Add `jacoco-maven-plugin` to pom.xml
- Gradle: Add `jacoco` plugin to build.gradle

**Config (reusable workflow only):**
```yaml
java:
  tools:
    jacoco:
      enabled: true
      min_coverage: 70  # Warn/fail if below this %
```

**Workflow inputs (java-ci.yml):**
- `run_jacoco`: boolean (default: true)
- `coverage_min`: number (default: 70)

**Artifacts produced:**
- `target/site/jacoco/jacoco.xml` - XML report for CI parsing
- `target/site/jacoco/index.html` - Human-readable HTML report

**Example pom.xml plugin:**
```xml
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.11</version>
  <executions>
    <execution>
      <goals><goal>prepare-agent</goal></goals>
    </execution>
    <execution>
      <id>report</id>
      <phase>verify</phase>
      <goals><goal>report</goal></goals>
    </execution>
  </executions>
</plugin>
```

---

### Checkstyle (Code Style)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Enforces coding standards and style rules. Catches formatting issues, naming conventions, and some code smells.

**Prerequisites:**
- Maven: Add `maven-checkstyle-plugin`
- Gradle: Add `checkstyle` plugin

**Config (reusable workflow only):**
```yaml
java:
  tools:
    checkstyle:
      enabled: true
      fail_on_violation: true
```

**Workflow inputs (java-ci.yml):**
- `run_checkstyle`: boolean (default: true)

**Artifacts produced:**
- `target/checkstyle-result.xml`

---

### SpotBugs (Bug Detection)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Static analysis on bytecode to find potential bugs: null pointer dereferences, infinite loops, resource leaks, etc.

**Prerequisites:**
- Maven: Add `spotbugs-maven-plugin`
- Gradle: Add `spotbugs` plugin

**Config (reusable workflow only):**
```yaml
java:
  tools:
    spotbugs:
      enabled: true
      fail_on_error: true
      effort: "max"      # min | default | max
      threshold: "medium" # low | medium | high
```

**Workflow inputs (java-ci.yml):**
- `run_spotbugs`: boolean (default: true)

**Artifacts produced:**
- `target/spotbugsXml.xml`
- `target/spotbugs.html` (if configured)

---

### PMD (Static Analysis)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `java.tools.pmd.enabled` in both modes.

**What it does:** Finds common programming flaws: unused variables, empty catch blocks, unnecessary object creation, complexity issues.

**Prerequisites:**
- Maven: Add `maven-pmd-plugin`
- Gradle: Add `pmd` plugin

**Artifacts produced:**
- `target/pmd.xml`

---

### OWASP Dependency-Check (Vulnerability Scanning)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Scans dependencies against the National Vulnerability Database (NVD) for known CVEs.

**Prerequisites:**
- Maven: Add `dependency-check-maven`
- **NVD API key strongly recommended** for faster/reliable scans

**Config (reusable workflow only):**
```yaml
java:
  tools:
    owasp:
      enabled: true
      fail_on_cvss: 7  # Fail if any vuln has CVSS >= this
      nvd_api_key_required: true
```

**Workflow inputs (java-ci.yml):**
- `run_owasp`: boolean (default: true)
- `owasp_cvss_fail`: number (default: 7)

**Secrets:**
- `NVD_API_KEY`: Get from https://nvd.nist.gov/developers/request-an-api-key

**Artifacts produced:**
- `target/dependency-check-report.html`
- `target/dependency-check-report.json`

---

### PITest (Mutation Testing)

**Availability:** Central (skip_mutation input) | Reusable (toggle)

**What it does:** Introduces small code changes (mutations) and checks if tests catch them. Measures test quality, not just coverage.

**Prerequisites:**
- Maven: Add `pitest-maven` plugin
- Tests must be reliable (no flaky tests)

**Config (reusable workflow only):**
```yaml
java:
  tools:
    pitest:
      enabled: true
      min_mutation_score: 70
      threads: 4
      timeout_multiplier: 2
```

**Workflow inputs:**
- Central: `skip_mutation`: boolean (default: false) - set true to skip
- Reusable: `run_pitest`: boolean (default: true)
- Reusable: `mutation_score_min`: number (default: 70)

**Artifacts produced:**
- `target/pit-reports/mutations.xml`
- `target/pit-reports/index.html`

**Performance tip:** Use `skip_mutation: true` for PR checks, enable for nightly builds.

---

### CodeQL (SAST)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `java.tools.codeql.enabled` in both modes.

**What it does:** GitHub's semantic code analysis engine. Finds security vulnerabilities with low false positive rate.

**Prerequisites:**
- Repository must be on GitHub
- `security-events: write` permission required

**Config:**
```yaml
java:
  tools:
    codeql:
      enabled: true
      languages: ["java"]
```

**Workflow inputs (java-ci.yml):**
- `run_codeql`: boolean (default: false)

**Artifacts produced:**
- SARIF results uploaded to GitHub Security tab

---

## Python Tools (Detailed)

### pytest + coverage

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Runs tests and measures code coverage using pytest-cov.

**Prerequisites:**
- `pytest` and `pytest-cov` installed (hub installs automatically)
- Tests in standard locations (tests/, test_*.py)

**Config (reusable workflow only):**
```yaml
python:
  tools:
    pytest:
      enabled: true
      min_coverage: 70
      fail_fast: false
```

**Workflow inputs (python-ci.yml):**
- `run_pytest`: boolean (default: true)
- `coverage_min`: number (default: 70)

**Artifacts produced:**
- `coverage.xml` - Cobertura format
- `htmlcov/` - HTML report
- JUnit XML (`test-results.xml` in reusable workflows, `pytest-junit.xml` in central mode)

---

### Ruff (Linting)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Extremely fast Python linter. Replaces Flake8 and includes security rules.

**Config (reusable workflow only):**
```yaml
python:
  tools:
    ruff:
      enabled: true
      fail_on_error: true
```

**Workflow inputs (python-ci.yml):**
- `run_ruff`: boolean (default: true)

**Artifacts produced:**
- `ruff-report.json`

**Rules included:**
- E/W: pycodestyle errors/warnings
- F: pyflakes
- S: flake8-bandit (security)
- B: flake8-bugbear

---

### Bandit (Security Scanner)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Finds common security issues in Python code: hardcoded passwords, SQL injection, command injection, etc.

**Config (reusable workflow only):**
```yaml
python:
  tools:
    bandit:
      enabled: true
      fail_on_high: true
```

**Workflow inputs (python-ci.yml):**
- `run_bandit`: boolean (default: true)

**Artifacts produced:**
- `bandit-report.json`

**Severity levels:**
- HIGH: Immediate fix required
- MEDIUM: Should fix
- LOW: Consider fixing

---

### pip-audit (Dependency Vulnerabilities)

**Availability:** Central (always) | Reusable (toggle)

**What it does:** Checks installed packages against PyPI's vulnerability database.

**Config (reusable workflow only):**
```yaml
python:
  tools:
    pip_audit:
      enabled: true
      fail_on_vuln: true
```

**Workflow inputs (python-ci.yml):**
- `run_pip_audit`: boolean (default: true)

**Artifacts produced:**
- `pip-audit-report.json`

---

### Black (Code Formatting)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `python.tools.black.enabled` in both modes.

**What it does:** Opinionated code formatter. "Any color you like, as long as it's black."

**Workflow inputs (python-ci.yml):**
- `run_black`: boolean (default: true)
- `max_black_issues`: integer (default: 0)

**Artifacts produced:**
- `black-output.txt`

---

### isort (Import Sorting)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `python.tools.isort.enabled` in both modes.

**What it does:** Sorts and organizes imports according to PEP 8 guidelines.

**Workflow inputs (python-ci.yml):**
- `run_isort`: boolean (default: true)
- `max_isort_issues`: integer (default: 0)

**Artifacts produced:**
- `isort-output.txt`

---

### mypy (Type Checking)

**Availability:** Central (always) | Reusable (toggle, default OFF)

**What it does:** Static type checker for Python. Catches type errors before runtime.

**Config (reusable workflow only):**
```yaml
python:
  tools:
    mypy:
      enabled: false  # Opt-in
```

**Workflow inputs (python-ci.yml):**
- `run_mypy`: boolean (default: false)

**Artifacts produced:**
- `mypy-output.txt`

---

### mutmut (Mutation Testing)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `python.tools.mutmut.enabled`. Central mode can also skip via `skip_mutation`.

**What it does:** Python mutation testing. Modifies code and checks if tests fail.

**Workflow inputs (python-ci.yml):**
- `run_mutmut`: boolean (default: true)
- `mutation_score_min`: number (default: 70)

**Artifacts produced:**
- `mutmut-run.log`

---

### Hypothesis (Property-Based Testing)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `python.tools.hypothesis.enabled` in both modes.

**What it does:** Property-based testing - generates test cases automatically.

**Workflow inputs (python-ci.yml):**
- `run_hypothesis`: boolean (default: true)

**Artifacts produced:**
- `hypothesis-output.txt`

---

### CodeQL (Python SAST)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Controlled by `python.tools.codeql.enabled` in both modes.

**What it does:** GitHub's semantic code analysis for Python.

**Config:**
```yaml
python:
  tools:
    codeql:
      enabled: true
      languages: ["python"]
```

**Workflow inputs (python-ci.yml):**
- `run_codeql`: boolean (default: false)

---

## Universal Tools (All Modes)

### Semgrep (SAST)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Central mode uses `semgrep --config=auto` in `hub-run-all.yml`.

**What it does:** Fast, lightweight static analysis using pattern matching. Runs with auto-config for common vulnerability patterns.

**When it runs:** If `*.tools.semgrep.enabled` is true.

**Artifacts produced:**
- `semgrep-report.json`

---

### Trivy (Container/Filesystem Scan)

**Availability:** Central (toggle) | Reusable (toggle)

> **Note:** Central mode runs a filesystem scan via `trivy fs`.

**What it does:** Scans filesystems and container images for vulnerabilities, misconfigurations, and secrets.

**When it runs:** If `*.tools.trivy.enabled` is true.

**Artifacts produced:**
- `trivy-report.json`

**Severity levels:**
- CRITICAL: Immediate action
- HIGH: Fix soon
- MEDIUM/LOW: Track and plan

---

## Thresholds Reference

These thresholds are defined in `config/defaults.yaml` and apply to reusable workflows:

| Tool | Config Key | Default | Recommended |
|------|------------|---------|-------------|
| JaCoCo | `java.tools.jacoco.min_coverage` | 70 | 80 |
| PITest | `java.tools.pitest.min_mutation_score` | 70 | 70 |
| OWASP DC | `java.tools.owasp.fail_on_cvss` | 7 | 7 |
| pytest | `python.tools.pytest.min_coverage` | 70 | 80 |

**Global thresholds (in `thresholds` section):**
```yaml
thresholds:
  coverage_min: 70
  mutation_score_min: 70
  max_critical_vulns: 0
  max_high_vulns: 0
```

> **Note:** Vulnerability rollup is now implemented in hub-report.json (as of 2025-12-15). The orchestrator aggregates critical/high/medium vuln counts across all repos and tools.

---

## Gaps and TODO

### Dispatch Callers - Current (Updated 2025-12-22)

The standard caller workflow (`hub-ci.yml`) exposes all reusable workflow inputs except Docker-related inputs (GitHub's 25-input limit). Use central mode or a docker-specific caller when Docker is required.

### Aggregation - Complete (Updated 2025-12-15)

The orchestrator now aggregates ALL tool metrics:
- Vulnerability counts rolled up from OWASP, Bandit, pip-audit, Trivy, Semgrep
- Per-tool metrics (checkstyle, spotbugs, pmd, ruff, black, isort, mypy) tracked per repo
- Separate summary tables for Java and Python repos
- Total counts for security posture across all repos

### Remaining Gaps

| Gap | Status | Notes |
|-----|--------|-------|
| Docker inputs in standard callers | Limited | Not exposed due to the 25-input limit |
| jqwik in central mode | Partial | Runs with tests but no dedicated hub-run-all toggle/summary |

---

## Tool Interactions

### Overlap Between Tools

| Concern | Primary Tool | Also Covers |
|---------|--------------|-------------|
| Code coverage | JaCoCo / pytest-cov | - |
| Code style | Checkstyle / Ruff | - |
| Bug patterns | SpotBugs | PMD (partial) |
| Security (code) | Bandit, Ruff S-rules | Semgrep, CodeQL |
| Security (deps) | OWASP DC / pip-audit | Trivy |
| Test quality | PITest / mutmut | - |
| Formatting | Black | isort (imports) |

---

## Recommended Configurations

### For Central Mode Users
Most tools are enabled by default. Customize via `config/repos/<repo>.yaml`:
```yaml
python:
  tools:
    mutmut: { enabled: false }  # Skip mutation testing
    semgrep: { enabled: true }  # Enable SAST
```
Use `skip_mutation: true` workflow input for faster runs.

### For Reusable Workflow Users

**Minimal (fast CI):**
```yaml
java:
  tools:
    jacoco: { enabled: true }
    checkstyle: { enabled: true }
    spotbugs: { enabled: false }
    pitest: { enabled: false }
    owasp: { enabled: false }
```

**Quality-focused:**
```yaml
java:
  tools:
    jacoco: { enabled: true, min_coverage: 80 }
    checkstyle: { enabled: true }
    spotbugs: { enabled: true }
    pitest: { enabled: true, min_mutation_score: 70 }
    owasp: { enabled: false }  # Run separately
```

**Security-focused:**
```yaml
java:
  tools:
    jacoco: { enabled: false }
    checkstyle: { enabled: false }
    spotbugs: { enabled: true }
    owasp: { enabled: true, fail_on_cvss: 5 }
    codeql: { enabled: true }
```

---

## Troubleshooting

| Issue | Tool | Fix |
|-------|------|-----|
| Coverage shows 0% | JaCoCo/pytest | Check if plugin/package installed, reports generated |
| SpotBugs fails | SpotBugs | Ensure Maven/Gradle plugin configured |
| OWASP times out | OWASP DC | Add NVD_API_KEY secret |
| PITest too slow | PITest | Use `skip_mutation: true` or reduce scope |
| Ruff has many errors | Ruff | Add `ruff.toml` to configure rules |
| mypy fails | mypy | Start with `--ignore-missing-imports` |
| Tool not running | Any | Check availability matrix and caller inputs |

---

## See Also

- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Full config schema
- [WORKFLOWS.md](../guides/WORKFLOWS.md) - Workflow details
- [MODES.md](../guides/MODES.md) - Central vs Distributed
- [TROUBLESHOOTING.md](../guides/TROUBLESHOOTING.md) - Common issues
- [RESEARCH_LOG.md](../development/research/RESEARCH_LOG.md) - Deep research on each tool

## Tool gating
- Tools run based on config run_* flags from merged config.
- Defaults live in `config/defaults.yaml`; override per repo as needed.
- Thresholds: prefer thresholds.* as source of truth; tool-level min_* are defaults.
