# Config Reference

Complete reference for CI/CD Hub configuration files.

---

## Quick Start

**Config is the single source of truth.** When using the hub orchestrator, all tool toggles come from config files—workflow inputs are only for direct callers who bypass the hub.

### 1. Copy a Template

```bash
# For hub-side config (recommended)
cp templates/hub/config/repos/repo-template.yaml config/repos/my-app.yaml

# Or for repo-local config
cp templates/repo/.ci-hub.yml path/to/my-repo/.ci-hub.yml
```

### 2. Pick a Profile

| Profile      | Description                                  | Best For            |
|--------------|----------------------------------------------|---------------------|
| **Fast**     | Core tools only (lint, test, coverage)       | PRs, quick feedback |
| **Quality**  | Adds mutation testing, type checking         | Pre-merge, release  |
| **Security** | All security scanners (SAST, SCA, container) | Security audits     |

See `templates/profiles/` for ready-to-use profile configs.

### 3. Run the Hub

```bash
# Trigger via GitHub Actions UI or API
# The hub reads your config and passes all toggles to workflows
```

### Key Points

- **Hub-driven runs:** Orchestrator reads config and passes values to reusable workflows
- **Direct workflow calls:** Use workflow inputs (for repos calling workflows directly without hub)
- **Defaults are authoritative:** tool enablement defaults live in `config/defaults.yaml`
- **Config always wins:** Even if workflow defaults differ, hub passes config values

---

## Config Hierarchy

Configuration is merged with the following precedence (highest wins):

```
1. Repo-local .ci-hub.yml       (in target repo root - optional, highest)
2. Hub config/repos/<repo>.yaml (hub-side per-repo override)
3. Hub config/defaults.yaml     (global defaults)

Profiles: templates/profiles/*.yaml are starting points; apply them into config/repos, then repo-local overrides win.

Both modes: repo-local `.ci-hub.yml` is merged over hub config when present (repo wins).
```

**Example:** If `defaults.yaml` sets `java.tools.jacoco.min_coverage: 70` but `config/repos/my-app.yaml` sets it to `80`, the merged value is `80`.

---

## Dispatch-Time Threshold Override (Escape Hatch)

For dispatch mode, there's an **escape hatch** that operates **outside the config hierarchy**:

```yaml
# Workflow dispatch input (NOT a .ci-hub.yml key)
threshold_overrides_yaml: |
  coverage_min: 70
  owasp_cvss_fail: 7
  max_critical_vulns: 0
```

**Purpose:** The orchestrator uses this to pass resolved thresholds to workflows at dispatch time. This is useful when:
- Orchestrator has already merged configs and wants to pass final values
- You need to temporarily override thresholds for a single run

**Not a config tier:** This input is parsed by the workflow at runtime but is NOT part of the three-tier config hierarchy. It's a dispatch mechanism, not a configuration source.

**Supported keys:**
- `coverage_min` - Minimum coverage percentage
- `mutation_score_min` - Minimum mutation score percentage
- `owasp_cvss_fail` - CVSS threshold for OWASP/Trivy (fail if >= this value)
- `max_critical_vulns` - Maximum allowed CRITICAL vulnerabilities
- `max_high_vulns` - Maximum allowed HIGH vulnerabilities

See [ADR-0024](../adr/0024-workflow-dispatch-input-limit.md) for the design rationale.

---

## Schema Validation

All configs are validated against `schema/ci-hub-config.schema.json`.

**Where validation runs:**
- `scripts/load_config.py` - validates merged config on load
- `hub-orchestrator.yml` load-config job - validates merged config before dispatch
- `config-validate.yml` workflow - runs on config/schema changes

**Validation errors look like:**
```
Config validation failed for config/repos/my-app.yaml:
  - java.tools.jacoco.min_coverage: 150 is greater than maximum 100
  - repo.language: 'ruby' is not one of ['java', 'python']
```

---

## Required Fields

### repo (Required)

| Field                      | Type    | Required | Default | Description                                                                                                                                                    |
|----------------------------|---------|----------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `repo.owner`               | string  | Yes      | —       | GitHub owner or organization                                                                                                                                   |
| `repo.name`                | string  | Yes      | —       | Repository name                                                                                                                                                |
| `repo.language`            | enum    | No       | `java`  | `java` or `python`                                                                                                                                             |
| `repo.default_branch`      | string  | No       | `main`  | Branch for CI runs                                                                                                                                             |
| `repo.run_group`           | enum    | No       | `full`  | Group tag to filter runs (e.g., `full`, `fixtures`, `smoke`)                                                                                                   |
| `repo.dispatch_enabled`    | boolean | No       | `true`  | If `false`, hub skips dispatch mode for this repo                                                                                                              |
| `repo.force_all_tools`     | boolean | No       | `false` | Force-enable all tools for this repo (overrides individual `tool.enabled` flags)                                                                               |
| `repo.use_central_runner`  | boolean | No       | `true`  | If `true`, hub clones repo and runs tools (central mode). If `false`, hub dispatches to target repo's workflow (distributed mode).                             |
| `repo.repo_side_execution` | boolean | No       | `false` | If `true`, enables `cihub init` to write workflows INTO target repos. Requires explicit `--apply` flag. Default `false` keeps target repos clean. |

**Example:**
```yaml
repo:
  owner: jguida941
  name: my-java-app
  language: java
  default_branch: main
```

---

## Java Configuration

### java (Top-level)

| Field               | Type   | Default   | Description                                |
|---------------------|--------|-----------|--------------------------------------------|
| `java.version`      | string | `"21"`    | JDK version (17, 21, etc.)                 |
| `java.distribution` | enum   | `temurin` | `temurin`, `corretto`, `zulu`, `microsoft` |
| `java.build_tool`   | enum   | `maven`   | `maven` or `gradle`                        |

### java.tools.jacoco

| Field          | Type    | Default | Description                |
|----------------|---------|---------|----------------------------|
| `enabled`      | boolean | `true`  | Run JaCoCo coverage        |
| `min_coverage` | integer | `70`    | Minimum coverage % (0-100) |

### java.tools.checkstyle

| Field               | Type    | Default | Description                             |
|---------------------|---------|---------|-----------------------------------------|
| `enabled`           | boolean | `true`  | Run Checkstyle                          |
| `fail_on_violation` | boolean | `true`  | Fail build on violations                |
| `max_errors`        | integer | `0`     | Max allowed errors (0 = fail on any)    |
| `config_file`       | string  | `null`  | Path to checkstyle.xml (null = default) |

### java.tools.spotbugs

| Field           | Type    | Default  | Description                        |
|-----------------|---------|----------|------------------------------------|
| `enabled`       | boolean | `true`   | Run SpotBugs                       |
| `fail_on_error` | boolean | `true`   | Fail build on bugs found           |
| `max_bugs`      | integer | `0`      | Max allowed bugs (0 = fail on any) |
| `effort`        | enum    | `max`    | `min`, `default`, `max`            |
| `threshold`     | enum    | `medium` | `low`, `medium`, `high`            |

### java.tools.owasp

| Field                  | Type    | Default | Description                              |
|------------------------|---------|---------|------------------------------------------|
| `enabled`              | boolean | `true`  | Run OWASP Dependency-Check               |
| `fail_on_cvss`         | integer | `7`     | Fail if any vuln has CVSS >= this (0-10) |
| `nvd_api_key_required` | boolean | `true`  | Require NVD_API_KEY secret               |

### java.tools.pitest

| Field                | Type    | Default | Description                                    |
|----------------------|---------|---------|------------------------------------------------|
| `enabled`            | boolean | `true`  | Run PITest mutation testing (can be expensive) |
| `min_mutation_score` | integer | `70`    | Minimum mutation score % (0-100)               |
| `threads`            | integer | `4`     | Parallel threads                               |
| `timeout_multiplier` | integer | `2`     | Timeout factor                                 |

### java.tools.jqwik

| Field     | Type    | Default | Description                      |
|-----------|---------|---------|----------------------------------|
| `enabled` | boolean | `false` | Run jqwik property-based testing |

### java.tools.pmd

| Field               | Type    | Default | Description                              |
|---------------------|---------|---------|------------------------------------------|
| `enabled`           | boolean | `true`  | Run PMD                                  |
| `fail_on_violation` | boolean | `false` | Fail build on violations                 |
| `max_violations`    | integer | `0`     | Max allowed violations (0 = fail on any) |

### java.tools.semgrep

| Field              | Type    | Default | Description                                       |
|--------------------|---------|---------|---------------------------------------------------|
| `enabled`          | boolean | `false` | Run Semgrep SAST (expensive - enable when needed) |
| `fail_on_findings` | boolean | `false` | Fail build on findings                            |
| `max_findings`     | integer | `0`     | Max allowed findings (0 = fail on any)            |

### java.tools.trivy

| Field              | Type    | Default | Description                                               |
|--------------------|---------|---------|-----------------------------------------------------------|
| `enabled`          | boolean | `false` | Run Trivy container scan (expensive - enable when needed) |
| `fail_on_critical` | boolean | `false` | Fail on CRITICAL vulns                                    |
| `fail_on_high`     | boolean | `false` | Fail on HIGH vulns                                        |

### java.tools.codeql

| Field       | Type    | Default    | Description                                      |
|-------------|---------|------------|--------------------------------------------------|
| `enabled`   | boolean | `false`    | Run CodeQL SAST (expensive - enable when needed) |
| `languages` | array   | `["java"]` | Languages to analyze                             |

### java.tools.docker

| Field             | Type    | Default              | Description                    |
|-------------------|---------|----------------------|--------------------------------|
| `enabled`         | boolean | `false`              | Build and test Docker          |
| `compose_file`    | string  | `docker-compose.yml` | Docker Compose file path       |
| `health_endpoint` | string  | `/actuator/health`   | Health check endpoint          |
| `health_timeout`  | integer | `300`                | Health check timeout (seconds) |

> **Dispatch vs Config:** `run_docker` (the tool toggle) is a dispatch input. `docker_compose_file` and `docker_health_endpoint` are config strings set in `.ci-hub.yml` or the caller template's `with:` block—they are NOT dispatch inputs.

---

## Python Configuration

### python (Top-level)

| Field            | Type   | Default  | Description    |
|------------------|--------|----------|----------------|
| `python.version` | string | `"3.12"` | Python version |

### python.tools.pytest

| Field          | Type    | Default | Description                |
|----------------|---------|---------|----------------------------|
| `enabled`      | boolean | `true`  | Run pytest with coverage   |
| `min_coverage` | integer | `70`    | Minimum coverage % (0-100) |
| `fail_fast`    | boolean | `false` | Stop on first failure      |

### python.tools.ruff

| Field           | Type    | Default | Description                          |
|-----------------|---------|---------|--------------------------------------|
| `enabled`       | boolean | `true`  | Run Ruff linter                      |
| `fail_on_error` | boolean | `true`  | Fail build on lint errors            |
| `max_errors`    | integer | `0`     | Max allowed errors (0 = fail on any) |

### python.tools.bandit

| Field          | Type    | Default | Description                  |
|----------------|---------|---------|------------------------------|
| `enabled`      | boolean | `true`  | Run Bandit security scanner  |
| `fail_on_high` | boolean | `true`  | Fail on HIGH severity issues |

### python.tools.pip_audit

| Field          | Type    | Default | Description             |
|----------------|---------|---------|-------------------------|
| `enabled`      | boolean | `true`  | Run pip-audit           |
| `fail_on_vuln` | boolean | `true`  | Fail on vulnerabilities |

### python.tools.mypy

| Field     | Type    | Default | Description                    |
|-----------|---------|---------|--------------------------------|
| `enabled` | boolean | `false` | Run mypy type checker (opt-in) |

### python.tools.mutmut

| Field                | Type    | Default | Description                                    |
|----------------------|---------|---------|------------------------------------------------|
| `enabled`            | boolean | `true`  | Run mutmut mutation testing (can be expensive) |
| `min_mutation_score` | integer | `70`    | Minimum mutation score % (0-100)               |
| `timeout_minutes`    | integer | `15`    | Maximum runtime                                |

### python.tools.hypothesis

| Field     | Type    | Default | Description                         |
|-----------|---------|---------|-------------------------------------|
| `enabled` | boolean | `true`  | Run hypothesis property-based tests |

### python.tools.semgrep

| Field              | Type    | Default | Description                                       |
|--------------------|---------|---------|---------------------------------------------------|
| `enabled`          | boolean | `false` | Run Semgrep SAST (expensive - enable when needed) |
| `fail_on_findings` | boolean | `false` | Fail build on findings                            |
| `max_findings`     | integer | `0`     | Max allowed findings (0 = fail on any)            |

### python.tools.trivy

| Field              | Type    | Default | Description                                               |
|--------------------|---------|---------|-----------------------------------------------------------|
| `enabled`          | boolean | `false` | Run Trivy container scan (expensive - enable when needed) |
| `fail_on_critical` | boolean | `false` | Fail on CRITICAL vulns                                    |
| `fail_on_high`     | boolean | `false` | Fail on HIGH vulns                                        |

### python.tools.codeql

| Field       | Type    | Default      | Description                                      |
|-------------|---------|--------------|--------------------------------------------------|
| `enabled`   | boolean | `false`      | Run CodeQL SAST (expensive - enable when needed) |
| `languages` | array   | `["python"]` | Languages to analyze                             |

### python.tools.docker

| Field     | Type    | Default  | Description           |
|-----------|---------|----------|-----------------------|
| `enabled` | boolean | `falese` | Build and test Docker |

> **Dispatch vs Config:** `run_docker` (the tool toggle) is a dispatch input. Docker-specific config like compose file paths remain in `.ci-hub.yml` or the caller template's `with:` block—they are NOT dispatch inputs.

### python.tools.black

| Field                   | Type    | Default | Description                          |
|-------------------------|---------|---------|--------------------------------------|
| `enabled`               | boolean | `true`  | Run Black format checker             |
| `fail_on_format_issues` | boolean | `false` | Fail build on format issues          |
| `max_issues`            | integer | `0`     | Max allowed issues (0 = fail on any) |

### python.tools.isort

| Field            | Type    | Default | Description                          |
|------------------|---------|---------|--------------------------------------|
| `enabled`        | boolean | `true`  | Run isort import checker             |
| `fail_on_issues` | boolean | `false` | Fail build on import issues          |
| `max_issues`     | integer | `0`     | Max allowed issues (0 = fail on any) |

---

## Reports Configuration

### reports

| Field                    | Type    | Default | Description               |
|--------------------------|---------|---------|---------------------------|
| `reports.retention_days` | integer | `30`    | Artifact retention (days) |

### reports.badges

| Field     | Type    | Default | Description            |
|-----------|---------|---------|------------------------|
| `enabled` | boolean | `true`  | Generate status badges |
| `branch`  | string  | `main`  | Branch for badge URLs  |

### reports.codecov

| Field              | Type    | Default | Description          |
|--------------------|---------|---------|----------------------|
| `enabled`          | boolean | `true`  | Upload to Codecov    |
| `fail_ci_on_error` | boolean | `false` | Fail if upload fails |

### reports.github_summary

| Field             | Type    | Default | Description           |
|-------------------|---------|---------|-----------------------|
| `enabled`         | boolean | `true`  | Generate step summary |
| `include_metrics` | boolean | `true`  | Include metrics table |

---

## Thresholds (Quality Gates)

### thresholds

| Field                | Type    | Default | Description                     |
|----------------------|---------|---------|---------------------------------|
| `coverage_min`       | integer | `70`    | Global minimum coverage %       |
| `mutation_score_min` | integer | `70`    | Global minimum mutation score % |
| `max_critical_vulns` | integer | `0`     | Max CRITICAL vulnerabilities    |
| `max_high_vulns`     | integer | `0`     | Max HIGH vulnerabilities        |

> **Note:** These thresholds are enforced where scanners emit severity counts (OWASP, Trivy, pip-audit, Bandit).

---

## Notifications (Optional)

### notifications.slack

| Field        | Type    | Default | Description                |
|--------------|---------|---------|----------------------------|
| `enabled`    | boolean | `false` | Enable Slack notifications |
| `on_failure` | boolean | `true`  | Notify on failure          |
| `on_success` | boolean | `false` | Notify on success          |

### notifications.email

| Field     | Type    | Default | Description                |
|-----------|---------|---------|----------------------------|
| `enabled` | boolean | `false` | Enable email notifications |

---

## Optional Features (All Default Off)

These features are placeholders for future implementation:

| Feature          | Config Key                 | Description                        |
|------------------|----------------------------|------------------------------------|
| Chaos Testing    | `chaos.enabled`            | Inject failures to test resilience |
| DR Drills        | `dr_drill.enabled`         | Automated backup/restore testing   |
| Cache Sentinel   | `cache_sentinel.enabled`   | Detect cache tampering             |
| Runner Isolation | `runner_isolation.enabled` | Concurrency limits                 |
| Supply Chain     | `supply_chain.enabled`     | SBOM, VEX, provenance              |
| Egress Control   | `egress_control.enabled`   | Network allowlists                 |
| Canary Deploy    | `canary.enabled`           | Gradual rollout                    |
| Telemetry        | `telemetry.enabled`        | Pipeline metrics collection        |
| Kyverno          | `kyverno.enabled`          | K8s admission policies             |

See `config/optional/*.yaml` for full configuration options when enabling.

---

## Hub CI Configuration

The `hub_ci` section controls the hub's own CI pipeline (`hub-production-ci.yml`). Unlike `java` and `python` sections which configure target repos, `hub_ci` governs hub infrastructure validation.

### hub_ci (Top-level)

| Field            | Type    | Default | Description            |
|------------------|---------|---------|------------------------|
| `hub_ci.enabled` | boolean | `true`  | Enable hub CI pipeline |

### hub_ci.tools

All tools default to `true` (enabled).

| Field                | Type    | Default | Description                   |
|----------------------|---------|---------|-------------------------------|
| `actionlint`         | boolean | `true`  | Workflow syntax validation    |
| `zizmor`             | boolean | `true`  | Workflow security scanning    |
| `ruff`               | boolean | `true`  | Python linting and formatting |
| `syntax`             | boolean | `true`  | Python syntax validation      |
| `mypy`               | boolean | `true`  | Static type checking          |
| `yamllint`           | boolean | `true`  | YAML syntax validation        |
| `pytest`             | boolean | `true`  | Unit tests with coverage      |
| `mutmut`             | boolean | `true`  | Mutation testing              |
| `bandit`             | boolean | `true`  | Python SAST                   |
| `pip_audit`          | boolean | `true`  | Dependency vulnerability scan |
| `gitleaks`           | boolean | `true`  | Secret detection              |
| `trivy`              | boolean | `true`  | Filesystem/config scanning    |
| `validate_templates` | boolean | `true`  | Template validation           |
| `validate_configs`   | boolean | `true`  | Config schema validation      |
| `verify_matrix_keys` | boolean | `true`  | Matrix key consistency        |
| `license_check`      | boolean | `true`  | License compliance            |
| `dependency_review`  | boolean | `true`  | PR dependency review          |
| `scorecard`          | boolean | `true`  | OpenSSF scorecard             |

### hub_ci.thresholds

| Field                | Type    | Default | Description                               |
|----------------------|---------|---------|-------------------------------------------|
| `coverage_min`       | integer | `70`    | Minimum coverage percentage (0-100)       |
| `mutation_score_min` | integer | `70`    | Minimum mutation score percentage (0-100) |

### Example

```yaml
hub_ci:
  enabled: true
  tools:
    actionlint: true
    zizmor: true
    # ... all tools enabled by default
  thresholds:
    coverage_min: 70
    mutation_score_min: 70
```

---

## Complete Examples

### Minimal Java Config

```yaml
repo:
  owner: jguida941
  name: my-java-app
  language: java
```

### Full Java Config with Overrides

```yaml
repo:
  owner: jguida941
  name: my-java-app
  language: java
  default_branch: develop

java:
  version: "17"
  build_tool: gradle
  tools:
    jacoco:
      enabled: true
      min_coverage: 80
    checkstyle:
      enabled: true
      fail_on_violation: true
    spotbugs:
      enabled: true
      effort: max
      threshold: low
    owasp:
      enabled: true
      fail_on_cvss: 5
    pitest:
      enabled: false  # Skip mutation testing
    codeql:
      enabled: true
    docker:
      enabled: true
      compose_file: docker-compose.test.yml
      health_endpoint: /health

reports:
  retention_days: 14
  codecov:
    enabled: true

thresholds:
  coverage_min: 70
  mutation_score_min: 75
```

### Minimal Python Config

```yaml
repo:
  owner: jguida941
  name: my-python-app
  language: python
```

### Full Python Config with Overrides

```yaml
repo:
  owner: jguida941
  name: my-python-app
  language: python
  default_branch: main

python:
  version: "3.11"
  tools:
    pytest:
      enabled: true
      min_coverage: 85
      fail_fast: true
    ruff:
      enabled: true
    bandit:
      enabled: true
      fail_on_high: true
    pip_audit:
      enabled: true
    mypy:
      enabled: true  # Enable type checking
    codeql:
      enabled: true

reports:
  retention_days: 7

thresholds:
  coverage_min: 85
```

### Security-Focused Config

```yaml
repo:
  owner: jguida941
  name: secure-service
  language: java

java:
  tools:
    jacoco:
      enabled: false  # Focus on security, not coverage
    checkstyle:
      enabled: false
    spotbugs:
      enabled: true
      threshold: low  # Catch all potential bugs
    owasp:
      enabled: true
      fail_on_cvss: 4  # Stricter threshold
    pitest:
      enabled: false
    codeql:
      enabled: true

thresholds:
  max_critical_vulns: 0
  max_high_vulns: 0
```

---

## Troubleshooting Config Issues

### Common Errors

| Error                                | Cause                | Fix                                  |
|--------------------------------------|----------------------|--------------------------------------|
| `repo.owner is required`             | Missing owner field  | Add `repo.owner: your-github-handle` |
| `repo.language: 'ruby' is not valid` | Unsupported language | Use `java` or `python`               |
| `min_coverage: 150 exceeds maximum`  | Value out of range   | Use 0-100                            |
| `tools.unknown_tool is not allowed`  | Typo in tool name    | Check spelling against this doc      |

### Debugging Config Loading

1. Check if your config is valid YAML:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/repos/my-repo.yaml'))"
   ```

2. Run the validation script:
   ```bash
   python scripts/load_config.py config/repos/my-repo.yaml
   ```

3. Check the `config-validate` workflow logs for validation errors.

### Config Not Taking Effect

1. **Check precedence** - repo-local `.ci-hub.yml` overrides hub configs
2. **Check file location** - must be `config/repos/<repo-name>.yaml`
3. **Check language** - Python tools don't apply to Java repos and vice versa
4. **Check workflow** - some tools only run in central mode (see [TOOLS.md](TOOLS.md) in this directory)

---

## See Also

- [TOOLS.md](TOOLS.md) - Tool details and availability
- [MODES.md](../guides/MODES.md) - Central vs Distributed execution
- [WORKFLOWS.md](../guides/WORKFLOWS.md) - Workflow documentation
- `templates/repo/.ci-hub.yml` - Repo-local template
- `templates/hub/config/repos/repo-template.yaml` - Hub-side template
- `schema/ci-hub-config.schema.json` - JSON Schema source
