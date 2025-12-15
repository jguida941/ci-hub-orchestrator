# Tools Reference

Comprehensive documentation for all quality, security, and testing tools supported by the CI/CD Hub.

> **Important:** Tools have different availability depending on execution mode. See the status columns carefully.

---

## Tool Availability Matrix

### Legend
- **Wired + Toggle**: Tool runs, controlled by config toggle
- **Wired (Always)**: Tool runs in this mode, no toggle exists
- **Not Wired**: Tool not implemented in this mode

> **Verification:** Central mode tools are in `hub-run-all.yml`. Grep for tool names to verify.

### Java Tools

| Tool | Central Mode | Reusable Workflow | Config Toggle | Status |
|------|--------------|-------------------|---------------|--------|
| JaCoCo | Wired (Always) | Wired + Toggle | `java.tools.jacoco.enabled` | Production |
| Checkstyle | Wired (Always) | Wired + Toggle | `java.tools.checkstyle.enabled` | Production |
| SpotBugs | Wired (Always) | Wired + Toggle | `java.tools.spotbugs.enabled` | Production |
| PMD | Wired (Always) | Not Wired | None | Central-only |
| OWASP DC | Wired (Always) | Wired + Toggle | `java.tools.owasp.enabled` | Production |
| PITest | Wired (skip_mutation) | Wired + Toggle | `java.tools.pitest.enabled` | Production |
| CodeQL | Not Wired | Wired + Toggle | `java.tools.codeql.enabled` | Reusable-only |

### Python Tools

| Tool | Central Mode | Reusable Workflow | Config Toggle | Status |
|------|--------------|-------------------|---------------|--------|
| pytest + coverage | Wired (Always) | Wired + Toggle | `python.tools.pytest.enabled` | Production |
| Ruff | Wired (Always) | Wired + Toggle | `python.tools.ruff.enabled` | Production |
| Bandit | Wired (Always) | Wired + Toggle | `python.tools.bandit.enabled` | Production |
| pip-audit | Wired (Always) | Wired + Toggle | `python.tools.pip_audit.enabled` | Production |
| Black | Wired (Always) | Not Wired | None | Central-only |
| isort | Wired (Always) | Not Wired | None | Central-only |
| mypy | Wired (Always) | Wired + Toggle | `python.tools.mypy.enabled` | Production |
| mutmut | Wired (skip_mutation) | Not Wired | None | Central-only |
| Hypothesis | Wired (Always) | Not Wired | None | Central-only |
| CodeQL | Not Wired | Wired + Toggle | `python.tools.codeql.enabled` | Reusable-only |

### Universal Tools (Central Mode Only)

| Tool | Central Mode | Reusable Workflow | When Runs | Status |
|------|--------------|-------------------|-----------|--------|
| Semgrep | Wired (Always) | Not Wired | Always | Central-only |
| Trivy | Wired (Conditional) | Not Wired | If Dockerfile exists | Central-only |

---

## Execution Modes Explained

### Central Mode (`hub-run-all.yml`)
- Hub clones your repo and runs ALL tools directly
- Tools run unconditionally (no config toggle)
- More tools available (PMD, Black, isort, mutmut, Semgrep, Trivy)
- **Recommended for most users**

### Reusable Workflows (`java-ci.yml`, `python-ci.yml`)
- Called from your repo's workflow or via distributed dispatch
- Tools controlled by workflow inputs and config toggles
- Fewer tools, but configurable
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

**Availability:** Central (always, line 460-477) | Reusable (NOT WIRED)

> **Note:** PMD runs in central mode (`hub-run-all.yml:460-477`). No config toggle exists. To add PMD to reusable workflows, a future update is needed.

**What it does:** Finds common programming flaws: unused variables, empty catch blocks, unnecessary object creation, complexity issues.

**Prerequisites:**
- Maven: Add `maven-pmd-plugin`
- Gradle: Add `pmd` plugin

**Artifacts produced (central mode):**
- `target/pmd.xml`

**To add to reusable workflow (TODO):**
- Add `run_pmd` input to java-ci.yml
- Add `java.tools.pmd.enabled` to defaults.yaml

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

**Availability:** Central (NOT WIRED) | Reusable (toggle)

> **Note:** CodeQL only runs in reusable workflows, not central mode.

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
- `run_codeql`: boolean (default: true)

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

**Availability:** Central (always, line 385-393) | Reusable (NOT WIRED)

> **Note:** Black runs in central mode (`hub-run-all.yml:385-393`). No config toggle exists yet.

**What it does:** Opinionated code formatter. "Any color you like, as long as it's black."

**Artifacts produced (central mode):**
- Check output (files that would be reformatted)

**To add to reusable workflow (TODO):**
- Add `run_black` input to python-ci.yml
- Add `python.tools.black.enabled` to defaults.yaml

---

### isort (Import Sorting)

**Availability:** Central (always, line 447-455) | Reusable (NOT WIRED)

> **Note:** isort runs in central mode (`hub-run-all.yml:447-455`). No config toggle exists yet.

**What it does:** Sorts and organizes imports according to PEP 8 guidelines.

**Artifacts produced (central mode):**
- Check output (files with unsorted imports)

**To add to reusable workflow (TODO):**
- Add `run_isort` input to python-ci.yml
- Add `python.tools.isort.enabled` to defaults.yaml

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
- stdout errors

---

### mutmut (Mutation Testing)

**Availability:** Central (skip_mutation input, line 416-445) | Reusable (NOT WIRED)

> **Note:** mutmut runs in central mode (`hub-run-all.yml:416-445`) when `skip_mutation=false`. Not available in reusable python-ci.yml.

**What it does:** Python mutation testing. Modifies code and checks if tests fail.

**Control (central mode only):**
- `skip_mutation: true` input to skip mutation testing

**Artifacts produced (central mode):**
- mutmut results (killed/survived counts)

**To add to reusable workflow (TODO):**
- Add `run_mutmut` input to python-ci.yml
- Add mutation score output

---

### Hypothesis (Property-Based Testing)

**Availability:** Central (always, line 405-414) | Reusable (NOT WIRED)

> **Note:** Hypothesis runs in central mode (`hub-run-all.yml:405-414`). Not available in reusable python-ci.yml.

**What it does:** Property-based testing - generates test cases automatically.

**Artifacts produced (central mode):**
- Example counts in output

---

### CodeQL (Python SAST)

**Availability:** Central (NOT WIRED) | Reusable (toggle)

> **Note:** CodeQL only runs in reusable workflows, not central mode.

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
- `run_codeql`: boolean (default: true)

---

## Universal Tools (Central Mode Only)

### Semgrep (SAST)

**Availability:** Central (always, line 503-518) | Reusable (NOT WIRED)

> **Note:** Semgrep runs in central mode (`hub-run-all.yml:503-518`). Runs for all languages.

**What it does:** Fast, lightweight static analysis using pattern matching. Runs with auto-config for common vulnerability patterns.

**When it runs:** Always in central mode (both Java and Python repos)

**Artifacts produced:**
- `semgrep-report.json`

**No configuration needed** - uses `--config=auto` for sensible defaults.

**To add to reusable workflows (TODO):**
- Add Semgrep steps to java-ci.yml and python-ci.yml
- Add toggle inputs

---

### Trivy (Container/Filesystem Scan)

**Availability:** Central (if Dockerfile exists, line 482-501) | Reusable (NOT WIRED)

> **Note:** Trivy runs in central mode (`hub-run-all.yml:482-501`) only when `Dockerfile` exists in repo.

**What it does:** Scans filesystems and container images for vulnerabilities, misconfigurations, and secrets.

**When it runs:** Only if `Dockerfile` exists in repo (central mode)

**Artifacts produced:**
- `trivy-report.json`

**Severity levels:**
- CRITICAL: Immediate action
- HIGH: Fix soon
- MEDIUM/LOW: Track and plan

**To add to reusable workflows (TODO):**
- Add Trivy steps to java-ci.yml and python-ci.yml
- Add toggle inputs

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

> **Note:** Vulnerability rollup (aggregating vuln counts across repos) is not yet implemented in hub-report.json.

---

## Gaps and TODO

### Tools Not Yet Wired to Reusable Workflows
These tools run in central mode (`hub-run-all.yml`) but need to be added to reusable workflows:

> **Important:** The config keys listed below do NOT currently exist in `config/defaults.yaml`, and the workflow inputs do NOT exist in `java-ci.yml`/`python-ci.yml`. Users cannot toggle these tools in distributed/reusable mode until both the config keys AND workflow steps are added.

| Tool | Workflow | Config Key Needed | Workflow Input Needed |
|------|----------|-------------------|----------------------|
| PMD | java-ci.yml | `java.tools.pmd.enabled` | `run_pmd` |
| Black | python-ci.yml | `python.tools.black.enabled` | `run_black` |
| isort | python-ci.yml | `python.tools.isort.enabled` | `run_isort` |
| mutmut | python-ci.yml | `python.tools.mutmut.enabled` | `run_mutmut` |
| Hypothesis | python-ci.yml | `python.tools.hypothesis.enabled` | `run_hypothesis` |
| Semgrep | both | `*.tools.semgrep.enabled` | `run_semgrep` |
| Trivy | both | `*.tools.trivy.enabled` | `run_trivy` |

### Missing Aggregation
- Vulnerability counts not rolled up in hub-report.json
- Per-tool metrics not yet aggregated across repos

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
No configuration needed - all tools run automatically. Use `skip_mutation: true` for faster runs.

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
| Tool not running | Any | Check availability matrix - may be central-only |

---

## See Also

- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Full config schema
- [WORKFLOWS.md](../guides/WORKFLOWS.md) - Workflow details
- [MODES.md](../guides/MODES.md) - Central vs Distributed
- [TROUBLESHOOTING.md](../guides/TROUBLESHOOTING.md) - Common issues
- [RESEARCH.md](../development/RESEARCH.md) - Deep research on each tool
