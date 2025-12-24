# Best Practices Research Log

**Date:** 2025-12-14
**Purpose:** Research best practices for docs templates, CI/CD, ADR with boolean toggles

---

## 1. ADR (Architecture Decision Records) Best Practices

### Sources:
- [ADR Templates - adr.github.io](https://adr.github.io/adr-templates/)
- [MADR - Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [GitHub - joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)
- [AWS ADR Process Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)

### Key Findings:

**MADR (Markdown Architectural Decision Records)** is the most popular template format. Version 4.0.0 released 2024-09-17.

**MADR Template Structure:**
```markdown
# ADR-NNNN: Title

## Status
proposed | rejected | accepted | deprecated | superseded by ADR-XXXX

## Deciders
List everyone involved in the decision

## Date
YYYY-MM-DD (when last updated)

## Context and Problem Statement
Describe the context and problem

## Decision Drivers
- Driver 1
- Driver 2

## Considered Options
1. Option A
2. Option B
3. Option C

## Decision Outcome
Chosen option: "Option X" because...

### Positive Consequences
- Good thing 1
- Good thing 2

### Negative Consequences
- Bad thing 1

## Pros and Cons of the Options

### Option A
- Good: ...
- Bad: ...

### Option B
- Good: ...
- Bad: ...
```

**Template Variants Available:**
- `adr-template.md` - Full template with explanations
- `adr-template-minimal.md` - Mandatory sections only with explanations
- `adr-template-bare.md` - All sections, no explanations
- `adr-template-bare-minimal.md` - Mandatory sections, no explanations

**AWS Minimum ADR Requirements:**
1. Context of the decision
2. The decision itself
3. Consequences of the decision

---

## 2. GitHub Actions Reusable Workflows Best Practices

### Sources:
- [GitHub Docs - Reuse Workflows](https://docs.github.com/en/actions/how-tos/sharing-automations/reusing-workflows)
- [Earthly Blog - Best Practices for Reusable Workflows](https://earthly.dev/blog/github-actions-reusable-workflows/)
- [GitHub Blog - Using Reusable Workflows](https://github.blog/developer-skills/github/using-reusable-workflows-github-actions/)
- [BretFisher/github-actions-templates](https://github.com/BretFisher/github-actions-templates)
- [Incredibuild - Best Practices](https://www.incredibuild.com/blog/best-practices-to-create-reusable-workflows-on-github-actions)

### Key Best Practices:

**1. Versioning & Security:**
- Use commit SHAs for maximum reproducibility
- Use release tags for readability (e.g., `@v1.0.0`)
- Create releases for each stable version
- Semantic versioning recommended (1.x.x scheme)
- Avoid breaking changes

**2. Repository Structure:**
```
.github/workflows/
├── reusable-build.yml      # workflow_call event
├── reusable-test.yml       # workflow_call event
├── reusable-deploy.yml     # workflow_call event
```
- Subdirectories NOT supported
- Central repo must be public OR internal with sharing enabled

**3. Documentation:**
- Clear documentation and changelogs are ESSENTIAL
- Document inputs/outputs required
- Explain how workflows work
- Keep change logs updated

**4. Testing:**
- Create test workflows that pass inputs and verify outputs
- Test like unit tests (input → expected output)
- Create dedicated test repository
- Test on main branch AND test repos

**5. Design Principles:**
- Be generic enough for reuse across projects
- Provide as many steps out-of-the-box as possible
- Modular design
- Parameterization with sensible defaults

**6. Workflow Templates vs Reusable Workflows:**
- Workflow templates: Starting point users customize
- Reusable workflows: Called by other workflows, centrally managed

**7. Permissions:**
- Configure access policies for cross-repo usage
- Private/internal repos need explicit sharing enabled

---

## 3. Diátaxis Documentation Framework

(Search failed - using known knowledge)

### The Four Documentation Types:

1. **Tutorials** - Learning-oriented
   - Take users through a series of steps
   - Focus on learning, not accomplishing a task
   - Example: "Getting Started with CI/CD Hub"

2. **How-To Guides** - Task-oriented
   - Take users through steps to solve a problem
   - Focus on accomplishing a specific task
   - Example: "How to add a new repository"

3. **Technical Reference** - Information-oriented
   - Describe the machinery and how to operate it
   - Accurate, complete information
   - Example: "Workflow Inputs Reference"

4. **Explanation** - Understanding-oriented
   - Clarify and discuss a topic
   - Provide context and background
   - Example: "Why Central Execution is Default"

### Applied to CI/CD Hub:

| Type | Hub Document |
|------|-------------|
| Tutorial | ONBOARDING.md, QUICKSTART.md |
| How-To | How to add repo, How to toggle tools, How to customize thresholds |
| Reference | CONFIG_REFERENCE.md, WORKFLOWS.md, TOOLS.md |
| Explanation | MODES.md (central vs distributed), ARCHITECTURE.md |

---

## 4. Self-Documenting YAML Best Practices

### Sources:
- [MoldStud - Best Practices for Documenting YAML](https://moldstud.com/articles/p-best-practices-for-documenting-yaml-configurations)
- [Home Assistant - YAML Style Guide](https://developers.home-assistant.io/docs/documenting/yaml-style-guide/)
- [Spacelift - YAML Comments](https://spacelift.io/blog/yaml-comments)
- [Testkube - YAML Commenting Best Practices](https://testkube.io/blog/yaml-commenting-best-practices-kubernetes-testing)

### Key Best Practices:

**1. Comment Syntax:**
- Use `#` for comments (no block comments in YAML)
- Place comments on their own line ABOVE the key (preferred over inline)

**2. Explain Purpose and Rationale:**
```yaml
# Why we use temurin: Oracle licensing issues, temurin is free
# and maintained by Eclipse Adoptium
java:
  distribution: "temurin"
```

**3. Use Descriptive Key Names:**
```yaml
# BAD
mc: 70

# GOOD
min_coverage: 70  # Minimum code coverage percentage required
```

**4. Add Section Headers:**
```yaml
# ==============================================================================
# JAVA DEFAULTS
# ==============================================================================
# These settings control Java build and test behavior.
# Override per-repo in config/repos/<repo>.yaml
# ==============================================================================
```

**5. Document Available Options:**
```yaml
build_tool: "maven"  # Options: maven | gradle
threshold: "medium"  # Options: low | medium | high
```

**6. Use TODO/TEMP Tags:**
```yaml
# TODO: Add support for Kotlin projects
# TEMP: Disabled until bug #123 is fixed
```

**7. Avoid Over-commenting:**
- Don't comment obvious things
- Focus on WHY, not WHAT

**8. Keep Secrets Out of Comments:**
- Never put tokens, passwords, internal URLs in comments

---

## 5. Feature Toggles / Boolean Flags Patterns

### Sources:
- [Martin Fowler - Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
- [Open Practice Library - Feature Toggles](https://openpracticelibrary.com/practice/feature-toggles/)
- [CMU - Feature Flags vs Configuration](https://www.cs.cmu.edu/~ckaestne/featureflags/)

### Key Patterns:

**1. Simple Boolean Toggle:**
```yaml
tools:
  jacoco:
    enabled: true   # Set to false to disable coverage
  pitest:
    enabled: false  # Mutation testing (slow, enable per-repo)
```

**2. Toggle with Threshold:**
```yaml
jacoco:
  enabled: true
  min_coverage: 70  # Only applies when enabled: true
```

**3. Toggle Categories (from Martin Fowler):**

| Category | Purpose | Lifespan |
|----------|---------|----------|
| Release Toggles | Hide incomplete features | Short |
| Ops Toggles | Control operational behavior | Short-Medium |
| Experiment Toggles | A/B testing | Short |
| Permission Toggles | Premium features | Long |

**4. Fail Fast on Missing Toggle:**
```yaml
# If toggle value missing, throw error - don't assume true/false
# This prevents unknown state
```

**5. Configuration Hierarchy (already in our defaults.yaml):**
```
1. Repo's .ci-hub.yml (highest priority)
2. Hub's config/repos/<repo>.yaml
3. Hub's config/defaults.yaml (lowest priority)
```

---

## 6. CI/CD Template Repository Examples

### Sources:
- [GitHub Blog - Build CI/CD Pipeline](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)
- [cutenode/github-actions-ci-templates](https://github.com/cutenode/github-actions-ci-templates)
- [Azure/actions-workflow-samples](https://github.com/Azure/actions-workflow-samples)
- [actions/starter-workflows](https://github.com/actions/starter-workflows)

### Repository Structure Patterns:

**Pattern 1: By Language (Azure style):**
```
.github/workflows/
├── dotnet/
├── nodejs/
├── java/
├── python/
└── ruby/
```

**Pattern 2: By Function:**
```
.github/workflows/
├── ci.yml
├── cd.yml
├── security.yml
└── release.yml
```

**Pattern 3: Reusable + Caller (our current approach):**
```
.github/workflows/
├── hub-run-all.yml      # Orchestrator
├── java-ci.yml          # Reusable (workflow_call)
├── python-ci.yml        # Reusable (workflow_call)
└── hub-security.yml     # Security scans
```

### Naming Convention:
- `language-platform-ci.yml` (e.g., `nodejs-cross-platform-ci.yml`)
- Reusable workflows: `reusable-*.yml`

---

## 7. FROM PLAN.MD - Specific Items to Document

### Production Gaps Identified:
1. **Inputs not passed to dispatch** - hub-orchestrator.yml computes per-repo toggles but only sends `triggered_by_hub`
2. **Branch hardcoded** - Uses `ref: 'main'` instead of per-repo `default_branch`
3. **Fire-and-forget dispatch** - No run IDs captured, no polling, failures swallowed
4. **Aggregation is stub** - Writes static summary, doesn't pull downstream artifacts
5. **force_all_tools** - Now config-driven (`repo.force_all_tools`) and applied per-repo by orchestrator
6. **Missing permissions block** - Needs `actions:write`, `contents:read`

### Two Operating Modes (from plan.md):

| Mode | Description | Default? |
|------|-------------|----------|
| Central Execution | Hub clones repos, runs tests directly | YES (default) |
| Distributed Execution | Hub dispatches to repo workflows | NO (optional, guarded) |

### Docs to Create (from plan.md):

| Doc | Purpose | Diátaxis Type |
|-----|---------|---------------|
| WORKFLOWS.md | Each workflow, inputs, outputs, artifacts | Reference |
| CONFIG_REFERENCE.md | Field-by-field config mapping | Reference |
| TOOLS.md | What each tool does, toggles, thresholds | Reference |
| MODES.md | Central vs Distributed explanation | Explanation |
| TROUBLESHOOTING.md | Common failures, fixes | How-To |
| TEMPLATES.md | List templates, when to use | How-To |

### Templates to Create (from plan.md):

| Template | Path | Purpose |
|----------|------|---------|
| Master repo config | `templates/repo/.ci-hub.yml` | All toggles, heavily commented |
| Hub-side config | `templates/hub/config/repos/<repo>.yaml` | For orgs that don't touch repos |
| Agent workflow | `templates/repo-agent/.github/workflows/hub-agent.yml` | Distributed mode only |
| Python Security | `templates/profiles/python-security.yml` | Bandit, pip-audit, CodeQL |
| Python Quality | `templates/profiles/python-quality.yml` | pytest, Ruff, Black, mypy |
| Java Security | `templates/profiles/java-security.yml` | OWASP, CodeQL, Semgrep |
| Java Quality | `templates/profiles/java-quality.yml` | JaCoCo, Checkstyle, SpotBugs, PITest |

### ADR Decisions Needed:

| ADR | Decision Topic |
|-----|----------------|
| ADR-0001 | Central vs Distributed as default mode |
| ADR-0002 | Config precedence hierarchy |
| ADR-0003 | Reusable workflows vs workflow_dispatch |
| ADR-0004 | Aggregation strategy (same-run vs polling) |
| ADR-0005 | Dashboard approach (GitHub Pages vs Grafana) |

---

## 8. Action Items / Next Steps

### Phase 1: Documentation Structure
- [ ] Create `docs/WORKFLOWS.md`
- [ ] Create `docs/CONFIG_REFERENCE.md`
- [ ] Create `docs/TOOLS.md`
- [ ] Create `docs/MODES.md`
- [ ] Create `docs/TROUBLESHOOTING.md`
- [ ] Create `docs/TEMPLATES.md`

### Phase 2: Templates
- [ ] Create `templates/repo/.ci-hub.yml` (master template)
- [ ] Create `templates/hub/config/repos/repo-template.yaml`
- [ ] Create `templates/profiles/` directory with profiles
- [ ] Create `templates/repo-agent/` for distributed mode

### Phase 3: ADRs
- [ ] Create `docs/adr/` directory
- [ ] Create ADR-0001 through ADR-0005

### Phase 4: Fix Production Gaps
- [ ] Pass computed inputs to dispatch
- [ ] Honor default_branch per repo
- [ ] Add permissions block
- [x] Implement force_all_tools via config (repo.force_all_tools)

---

## 9. Complete Tool Catalog (from plan.md)

### Fast Feedback Tools (Run on Every PR)

| Category | Tool | Language | What It Does | Config Key |
|----------|------|----------|--------------|------------|
| Unit Tests | **JUnit** | Java | Runs unit tests, validates functions/classes | Built into Maven/Gradle |
| Unit Tests | **pytest** | Python | Test runner with fixtures, parametrization, plugins | `python.tools.pytest.enabled` |
| Coverage | **JaCoCo** | Java | Measures code coverage via bytecode instrumentation | `java.tools.jacoco.enabled` |
| Coverage | **pytest-cov** | Python | Coverage measurement, produces coverage.xml | `python.tools.pytest.enabled` |
| Coverage | **coverage.py** | Python | Underlying coverage engine for pytest-cov | Same as pytest-cov |
| Linting | **Checkstyle** | Java | Code style rules enforcement | `java.tools.checkstyle.enabled` |
| Linting | **SpotBugs** | Java | Finds bug patterns in bytecode | `java.tools.spotbugs.enabled` |
| Linting | **PMD** | Java | Static analysis, code smell detection | `java.tools.pmd.enabled` |
| Linting | **Ruff** | Python | Fast linter (replaces flake8, isort, many plugins) | `python.tools.ruff.enabled` |
| Formatting | **Black** | Python | Opinionated code formatter | `python.tools.black.enabled` |
| Formatting | **isort** | Python | Import ordering formatter/checker | `python.tools.isort.enabled` |
| Static Security | **CodeQL** | Java/Python | GitHub's SAST, finds security vulnerabilities | `*.tools.codeql.enabled` |
| Static Security | **Semgrep** | Java/Python | SAST with language-aware rules | Run in hub-run-all |
| Static Security | **Bandit** | Python | Security linter for Python source | `python.tools.bandit.enabled` |
| Dependency Scan | **OWASP Dependency-Check** | Java | Scans deps for known CVEs | `java.tools.owasp.enabled` |
| Dependency Scan | **pip-audit** | Python | Dependency vulnerability scanning | `python.tools.pip_audit.enabled` |
| Dependency Scan | **Trivy** | All | Container and filesystem vulnerability scan | Run when Dockerfile exists |
| Type Checking | **mypy** | Python | Static type checker (requires type hints) | `python.tools.mypy.enabled` |

### Deeper Confidence Tools (Often Nightly)

| Category | Tool | Language | What It Does | Config Key |
|----------|------|----------|--------------|------------|
| Mutation Testing | **PITest** | Java | Injects code mutations, measures test strength | `java.tools.pitest.enabled` |
| Mutation Testing | **mutmut** | Python | Mutation testing for Python | Run in hub-run-all |
| Mutation Testing | **cosmic-ray** | Python | Alternative Python mutation tester | Not implemented |
| Property Testing | **Hypothesis** | Python | Generates randomized test cases from properties | Run in hub-run-all |
| Property Testing | **jqwik** | Java | Property-based testing for JVM | ✅ Implemented (run_jqwik input) |
| Integration Tests | **Testcontainers** | Java/Python | Tests with real containers (DB, Redis, etc.) | Requires Docker |
| Contract Tests | **Pact** | Java | Consumer-driven contract testing | Not implemented |
| Contract Tests | **pact-python** | Python | Consumer-driven contract testing | Not implemented |
| DAST | **OWASP ZAP** | All | Attacks running service to find vulns | `run_zap` in hub-security |
| Load Testing | **k6** | All | Modern load testing tool | Not implemented |
| Load Testing | **Gatling** | Java | Scala-based load testing | Not implemented |
| Load Testing | **JMeter** | Java | Apache load testing tool | Not implemented |
| Load Testing | **Locust** | Python | Python load testing framework | Not implemented |

---

## 10. Tool Details - Java

### JaCoCo (Java Code Coverage)
- **What:** Coverage reporting for JVM bytecode
- **Prerequisites:** Maven/Gradle plugin configured in repo
- **Toggle:** `java.tools.jacoco.enabled: true`
- **Threshold:** `java.tools.jacoco.min_coverage: 70`
- **Output:** `target/site/jacoco/jacoco.xml`, HTML report
- **Gate:** Fails if coverage < min_coverage

### Checkstyle
- **What:** Enforces Java coding style rules
- **Prerequisites:** Plugin + config file (checkstyle.xml)
- **Toggle:** `java.tools.checkstyle.enabled: true`
- **Output:** `target/checkstyle-result.xml`
- **Gate:** Fails on violations if `fail_on_violation: true`

### SpotBugs
- **What:** Finds bug patterns in Java bytecode
- **Prerequisites:** Maven/Gradle plugin
- **Toggle:** `java.tools.spotbugs.enabled: true`
- **Options:** `effort: max`, `threshold: medium`
- **Output:** `target/spotbugsXml.xml`
- **Gate:** Fails on errors if `fail_on_error: true`

### PMD
- **What:** Static analysis, finds code smells
- **Prerequisites:** Maven/Gradle plugin + ruleset
- **Toggle:** `java.tools.pmd.enabled: true`
- **Output:** `target/pmd.xml`
- **Gate:** Configurable violation threshold

### OWASP Dependency-Check
- **What:** Scans dependencies for known CVEs
- **Prerequisites:** NVD API key recommended for speed
- **Toggle:** `java.tools.owasp.enabled: true`
- **Threshold:** `java.tools.owasp.fail_on_cvss: 7`
- **Output:** `dependency-check-report.json`, HTML
- **Gate:** Fails if any vuln >= CVSS threshold

### PITest (Mutation Testing)
- **What:** Mutates code to test strength of tests
- **Prerequisites:** PITest Maven plugin configured
- **Toggle:** `java.tools.pitest.enabled: true`
- **Threshold:** `java.tools.pitest.min_mutation_score: 70`
- **Options:** `threads: 4`, `timeout_multiplier: 2`
- **Output:** `target/pit-reports/mutations.xml`
- **Gate:** Fails if mutation score < threshold
- **Note:** SLOW - consider disabling for PRs

### CodeQL (Java)
- **What:** GitHub's semantic code analysis
- **Prerequisites:** None (runs in Actions)
- **Toggle:** `java.tools.codeql.enabled: true`
- **Output:** SARIF uploaded to Security tab
- **Gate:** Creates security alerts

### Docker Build & Health Check
- **What:** Builds container, verifies health endpoint
- **Prerequisites:** Dockerfile or docker-compose.yml
- **Toggle:** `java.tools.docker.enabled: false` (opt-in)
- **Options:** `compose_file`, `health_endpoint`, `health_timeout`
- **Gate:** Fails if health check fails

---

## 11. Tool Details - Python

### pytest
- **What:** Test runner with rich plugin ecosystem
- **Prerequisites:** pytest installed, tests in test_*.py
- **Toggle:** `python.tools.pytest.enabled: true`
- **Options:** `fail_fast: false`
- **Output:** Test results, coverage.xml if pytest-cov used
- **Gate:** Fails if tests fail

### pytest-cov / coverage.py
- **What:** Coverage measurement and reporting
- **Prerequisites:** pytest-cov installed
- **Toggle:** Same as pytest
- **Threshold:** `python.tools.pytest.min_coverage: 70`
- **Output:** `coverage.xml`, `htmlcov/`
- **Gate:** Fails if coverage < threshold

### Ruff
- **What:** Extremely fast Python linter (Rust-based)
- **What it replaces:** flake8, isort, pyupgrade, many more
- **Toggle:** `python.tools.ruff.enabled: true`
- **Output:** `ruff-report.json`
- **Gate:** Fails on errors if `fail_on_error: true`
- **Note:** Can also do formatting (ruff format)

### Black
- **What:** Opinionated code formatter ("uncompromising")
- **Toggle:** `python.tools.black.enabled: true`
- **Output:** List of files that would be reformatted
- **Gate:** Fails if files need reformatting (--check mode)

### isort
- **What:** Sorts and organizes Python imports
- **Toggle:** `python.tools.isort.enabled: true`
- **Output:** List of files with import issues
- **Gate:** Fails if imports need reordering
- **Note:** Ruff can also do this

### Bandit
- **What:** Security linter for Python code
- **Toggle:** `python.tools.bandit.enabled: true`
- **Output:** `bandit-report.json`
- **Gate:** Fails on high severity if `fail_on_high: true`
- **Severities:** HIGH, MEDIUM, LOW

### pip-audit
- **What:** Scans Python dependencies for vulnerabilities
- **Toggle:** `python.tools.pip_audit.enabled: true`
- **Output:** `pip-audit-report.json`
- **Gate:** Fails on any vulnerability if `fail_on_vuln: true`

### mypy
- **What:** Static type checker for Python
- **Prerequisites:** Type hints in code
- **Toggle:** `python.tools.mypy.enabled: false` (opt-in)
- **Output:** List of type errors
- **Gate:** Fails if type errors found
- **Note:** Requires gradual adoption

### Hypothesis
- **What:** Property-based testing framework
- **What it does:** Generates random inputs based on properties
- **Toggle:** Runs automatically if hypothesis tests exist
- **Output:** Number of examples generated/passed
- **Gate:** Fails if any property falsified

### mutmut
- **What:** Mutation testing for Python
- **What it does:** Changes code, checks if tests catch it
- **Toggle:** `skip_mutation` input to disable
- **Output:** Killed/survived mutation counts
- **Gate:** Advisory (mutation score)
- **Note:** SLOW - 10+ minute timeout

---

## 12. Tool Details - Universal (All Languages)

### CodeQL
- **What:** GitHub's semantic code analysis engine
- **Languages:** Java, Python, JavaScript, Go, C++, C#, Ruby
- **Toggle:** `*.tools.codeql.enabled: true`
- **Output:** SARIF → GitHub Security tab
- **Gate:** Creates security alerts, can block PRs

### Semgrep
- **What:** Fast, lightweight SAST with custom rules
- **Languages:** 30+ including Java, Python, JS, Go
- **Toggle:** Runs in hub-run-all automatically
- **Output:** `semgrep-report.json`
- **Gate:** Advisory (findings count)
- **Note:** `--config=auto` uses community rules

### Trivy
- **What:** Comprehensive vulnerability scanner
- **Scans:** Containers, filesystems, git repos, K8s
- **Toggle:** Runs when Dockerfile exists
- **Output:** `trivy-report.json`
- **Severities:** CRITICAL, HIGH, MEDIUM, LOW
- **Gate:** Advisory (vuln counts)

### OWASP ZAP (DAST)
- **What:** Dynamic Application Security Testing
- **What it does:** Attacks running app to find vulns
- **Toggle:** `run_zap` input in hub-security.yml
- **Prerequisites:** App must be running and accessible
- **Output:** ZAP report
- **Note:** Requires environment setup

---

## 13. Optional Features (from defaults.yaml)

| Feature | Config Key | Default | Purpose |
|---------|-----------|---------|---------|
| Chaos Testing | `chaos.enabled` | false | Inject failures for resilience testing |
| DR Drills | `dr_drill.enabled` | false | Automated backup/restore testing |
| Cache Sentinel | `cache_sentinel.enabled` | false | Detect cache tampering |
| Runner Isolation | `runner_isolation.enabled` | false | Concurrency limits, resource controls |
| Supply Chain | `supply_chain.enabled` | false | SBOM, VEX, provenance, signing |
| Egress Control | `egress_control.enabled` | false | Network allowlists |
| Canary Deploy | `canary.enabled` | false | Gradual rollout with auto-rollback |
| Telemetry | `telemetry.enabled` | false | Pipeline run data collection |
| Kyverno | `kyverno.enabled` | false | K8s admission control policies |

---

## 14. Report/Notification Features

| Feature | Config Key | Purpose |
|---------|-----------|---------|
| Artifact Retention | `reports.retention_days: 30` | How long to keep artifacts |
| Badges | `reports.badges.enabled: true` | Generate coverage badges |
| Codecov | `reports.codecov.enabled: true` | Upload to Codecov service |
| GitHub Summary | `reports.github_summary.enabled: true` | Rich step summary |
| Slack Notify | `notifications.slack.enabled: false` | Slack on failure/success |
| Email Notify | `notifications.email.enabled: false` | Email notifications |

---

## 15. Thresholds / Quality Gates

| Threshold | Config Key | Default | Meaning |
|-----------|-----------|---------|---------|
| Coverage Min | `thresholds.coverage_min` | 70 | Minimum code coverage % |
| Mutation Min | `thresholds.mutation_score_min` | 70 | Minimum mutation score % |
| Critical Vulns | `thresholds.max_critical_vulns` | 0 | Max critical vulns allowed |
| High Vulns | `thresholds.max_high_vulns` | 0 | Max high vulns allowed |
| OWASP CVSS | `java.tools.owasp.fail_on_cvss` | 7 | Fail if CVSS >= this |

---

## 16. MADR Template Details

### Sources:
- [GitHub - adr/madr](https://github.com/adr/madr)
- [MADR Template Explained](https://ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html)
- [MADR Examples](https://adr.github.io/madr/examples.html)

### MADR 4.0 Template (Released Sept 2024)

```markdown
---
status: {proposed | rejected | accepted | deprecated | superseded by ADR-XXXX}
date: {YYYY-MM-DD when last updated}
decision-makers: {list everyone involved}
consulted: {list everyone whose opinions are sought}
informed: {list everyone kept up-to-date}
---

# {short title, representative of solved problem and found solution}

## Context and Problem Statement

{Describe context and problem statement, e.g., in free form using 2-3 sentences
or in form of an illustrative story. May include issue links.}

## Decision Drivers

* {decision driver 1, e.g., a force, facing concern, …}
* {decision driver 2, e.g., a force, facing concern, …}
* … <!-- numbers of drivers can vary -->

## Considered Options

* {title of option 1}
* {title of option 2}
* {title of option 3}
* … <!-- numbers of options can vary -->

## Decision Outcome

Chosen option: "{title of option 1}", because {justification}.

### Consequences

* Good, because {positive consequence, e.g., improvement of one or more desired qualities, …}
* Bad, because {negative consequence, e.g., compromising one or more desired qualities, …}
* … <!-- numbers of consequences can vary -->

### Confirmation

{How will the implementation/compliance be confirmed? E.g., by a review or PoC.}

## Pros and Cons of the Options

### {title of option 1}

{example | description | pointer to more information | …}

* Good, because {argument a}
* Good, because {argument b}
* Neutral, because {argument c}
* Bad, because {argument d}
* … <!-- numbers of pros and cons can vary -->

### {title of option 2}

{example | description | pointer to more information | …}

* Good, because {argument a}
* Good, because {argument b}
* Neutral, because {argument c}
* Bad, because {argument d}
* …

## More Information

{Links to related decisions, resources, etc.}
```

### Usage:
1. Create `docs/adr/` directory
2. Copy template to `NNNN-title-with-dashes.md`
3. Number sequentially (0001, 0002, etc.)

---

## 17. GitHub Pages Dashboard Approaches

### Sources:
- [GitHub Blog - Open Source Metrics Dashboard](https://github.blog/open-source/maintainers/how-to-build-an-open-source-metrics-dashboard/)
- [lowlighter/metrics](https://github.com/lowlighter/metrics)
- [horosin/metrics-dashboard](https://github.com/horosin/metrics-dashboard)

### Approach 1: Static JSON + GitHub Pages (Recommended for Hub)
```
Hub Workflow → generates metrics.json → commits to gh-pages branch
                                      → builds static HTML
                                      → GitHub Pages serves it
```

**Pros:**
- No server needed
- Fast (data pre-loaded at build time)
- Free hosting

**Implementation:**
1. Hub run generates `hub-report.json` with all metrics
2. GitHub Action commits JSON to `gh-pages` branch
3. Simple HTML/JS reads JSON and renders charts (Chart.js, Plotly.js)
4. GitHub Pages serves the site

### Approach 2: lowlighter/metrics
- 30+ plugins, 300+ options
- Renders as SVG, Markdown, PDF, or JSON
- Embeddable in READMEs

### Approach 3: JSON + Google Sheets + Chart.js
- Store data in Google Sheet (public)
- Fetch and render with Chart.js
- Good for non-technical users

---

## 18. SLSA / Supply Chain Security

### Sources:
- [GitHub Supply Chain Security](https://github.com/security/advanced-security/software-supply-chain)
- [SLSA 3 Compliance with GitHub Actions](https://github.blog/security/supply-chain-security/slsa-3-compliance-with-github-actions/)
- [SLSA FAQ](https://slsa.dev/spec/v1.0/faq)

### SLSA Levels:
| Level | Requirements |
|-------|-------------|
| SLSA 1 | Provenance exists |
| SLSA 2 | Hosted build platform, signed provenance |
| SLSA 3 | Hardened builds, isolated, verified source |
| SLSA 4 | Two-person review, hermetic builds |

### Key Components:

**Provenance:** Metadata about where software came from
- Who built it
- Where it was built
- What codebase

**SBOM (Software Bill of Materials):**
- List of all components/dependencies
- Helps identify vulnerabilities
- GitHub can auto-generate from dependency graph

**Sigstore:** Free signing infrastructure
- cosign for container signing
- Fulcio for certificates
- Rekor for transparency log

### GitHub Actions Implementation:
```yaml
- uses: actions/attest-build-provenance@v1
  with:
    subject-path: 'dist/my-artifact'
```

### For Hub - Supply Chain Config:
```yaml
supply_chain:
  enabled: false  # opt-in
  sbom:
    enabled: true
    format: spdx  # or cyclonedx
  provenance:
    enabled: true
    slsa_level: 3
  signing:
    enabled: true
    method: sigstore
```

---

## 19. SDLC Phases & Best Practices

### Sources:
- [Atlassian - Complete Guide to SDLC](https://www.atlassian.com/agile/software-development/sdlc)
- [CircleCI - SDLC Phases and Best Practices](https://circleci.com/blog/sdlc-phases-and-best-practices/)
- [IBM - What is SDLC](https://www.ibm.com/think/topics/sdlc)
- [GitHub - What is SDLC](https://github.com/resources/articles/what-is-sdlc)
- [LinearB - SDLC Best Practices](https://linearb.io/blog/sdlc-best-practices)

### The 7 SDLC Phases:

| Phase | Purpose | Key Activities |
|-------|---------|----------------|
| 1. Planning | Foundation | Define goals, scope, timeline, resources |
| 2. Requirements | Analysis | Gather functional/non-functional requirements |
| 3. Design | Architecture | System design, data models, interfaces |
| 4. Development | Implementation | Write code, follow standards, version control |
| 5. Testing | Validation | Unit, integration, system, acceptance tests |
| 6. Deployment | Release | Staged rollout, canary, blue-green |
| 7. Maintenance | Operations | Bug fixes, updates, monitoring |

### Applying SDLC to Hub-Release:

| SDLC Phase | Hub Activity |
|------------|--------------|
| Planning | Define scope: what languages, tools, modes |
| Requirements | Document in RESEARCH.md, create ADRs |
| Design | Architecture decisions, config hierarchy |
| Development | Build workflows, scripts, templates |
| Testing | Test with fixture repos, validate configs |
| Deployment | Release versions, document changes |
| Maintenance | Fix bugs, add tools, update docs |

### 2024/2025 Best Practices:

**1. DevSecOps (Shift Left Security):**
- Security checks in Design and Development phases
- Automated SAST/DAST in CI/CD pipeline
- Don't wait until the end for security testing

**2. Data Hygiene & Metrics:**
- Track DORA metrics (deployment frequency, lead time, MTTR, change failure rate)
- Maintain clean data in Git, issue trackers
- Use metrics to improve

**3. Documentation:**
- Clear documentation at each phase
- Regular check-ins and communication
- Proactive problem-solving

**4. Code Quality:**
- Standardized code review process
- Manage technical debt
- Optimize developer workflow

---

## 20. Requirements Documentation (SRS) Best Practices

### Sources:
- [Perforce - How to Write SRS](https://www.perforce.com/blog/alm/how-write-software-requirements-specification-srs-document)
- [Asana - Software Requirement Document](https://asana.com/resources/software-requirement-document-template)
- [GeeksforGeeks - SRS Format](https://www.geeksforgeeks.org/software-engineering/software-requirement-specification-srs-format/)
- [GitHub - SRS-Template (IEEE 830)](https://github.com/jam01/SRS-Template)

### SRS Document Structure:

```markdown
# Software Requirements Specification

## 1. Introduction
### 1.1 Purpose
### 1.2 Scope
### 1.3 Definitions, Acronyms, Abbreviations
### 1.4 References
### 1.5 Overview

## 2. Overall Description
### 2.1 Product Perspective
### 2.2 Product Functions
### 2.3 User Characteristics
### 2.4 Constraints
### 2.5 Assumptions and Dependencies

## 3. Specific Requirements
### 3.1 Functional Requirements
### 3.2 Non-Functional Requirements
### 3.3 External Interface Requirements

## 4. Appendices
```

### Best Practices:

**1. Clear, Unambiguous Language:**
```
BAD:  "The system should be fast"
GOOD: "The system responds within 2 seconds for 95% of requests"
```

**2. Define Key Terms:**
- Create glossary
- Define acronyms
- Avoid jargon without explanation

**3. Make Requirements SMART:**
- **S**pecific - Clear and precise
- **M**easurable - Quantifiable criteria
- **A**chievable - Technically feasible
- **R**elevant - Aligned with goals
- **T**raceable - Linked to source

**4. Include Visual Aids:**
- Flowcharts
- ER diagrams
- UML diagrams
- Architecture visuals

**5. Version Control:**
- Track all changes
- Maintain history
- Clear revision log

**6. Standards:**
- IEEE 830
- ISO/IEC/IEEE 29148:2011
- Or company-specific template

---

## 21. Codebase Organization (Monorepo) Best Practices

### Sources:
- [Luca Pette - How to Structure a Monorepo](https://lucapette.me/writing/how-to-structure-a-monorepo/)
- [CircleCI - Monorepo Dev Practices](https://circleci.com/blog/monorepo-dev-practices/)
- [MindfulChase - Monorepo Best Practices](https://www.mindfulchase.com/deep-dives/monorepo-fundamentals-deep-dives-into-unified-codebases/structuring-your-monorepo-best-practices-for-directory-and-code-organization.html)

### Recommended Structure for Hub-Release:

```
hub-release/
├── .github/
│   └── workflows/           # GitHub Actions workflows
│       ├── hub-run-all.yml  # Central execution (default)
│       ├── hub-orchestrator.yml  # Distributed execution
│       ├── hub-security.yml
│       ├── java-ci.yml      # Reusable workflow
│       └── python-ci.yml    # Reusable workflow
│
├── config/
│   ├── defaults.yaml        # Global defaults
│   ├── repos/               # Per-repo overrides
│   │   └── <repo>.yaml
│   └── optional/            # Optional feature configs
│       ├── chaos.yaml
│       ├── dr-drill.yaml
│       └── supply-chain.yaml
│
├── docs/
│   ├── ONBOARDING.md        # Tutorial
│   ├── WORKFLOWS.md         # Reference
│   ├── CONFIG_REFERENCE.md  # Reference
│   ├── TOOLS.md             # Reference
│   ├── MODES.md             # Explanation
│   ├── TROUBLESHOOTING.md   # How-To
│   ├── RESEARCH.md          # Research log
│   └── adr/                 # Architecture Decision Records
│       ├── 0001-central-vs-distributed.md
│       ├── 0002-config-precedence.md
│       └── ...
│
├── templates/
│   ├── repo/                # For target repos
│   │   └── .ci-hub.yml      # Master template
│   ├── hub/                 # Hub-side templates
│   │   └── config/repos/repo-template.yaml
│   ├── profiles/            # Pre-configured profiles
│   │   ├── java-quality.yml
│   │   ├── java-security.yml
│   │   ├── python-quality.yml
│   │   └── python-security.yml
│   └── repo-agent/          # Distributed mode only
│       └── .github/workflows/hub-agent.yml
│
├── scripts/
│   ├── load_config.py       # Config merging
│   ├── aggregate_reports.py # Report aggregation
│   └── validate_config.py   # Schema validation
│
├── schema/
│   ├── ci-hub-config.schema.json
│   └── pipeline-run.v1.json
│
├── dashboards/
│   ├── overview.json
│   └── repo-detail.json
│
├── fixtures/                # Test repos for validation
│   ├── java-passing/
│   ├── java-failing/
│   ├── python-passing/
│   └── edge-cases/
│
├── policies/                # K8s/Kyverno policies
│   └── kyverno/
│
├── reports/                 # Generated (gitignored)
│
├── README.md
├── CHANGELOG.md
├── plan.md
└── pyproject.toml
```

### Key Principles:

**1. Separation of Concerns:**
- Workflows in `.github/workflows/`
- Config in `config/`
- Docs in `docs/`
- Templates in `templates/`

**2. Clear Ownership:**
- Each directory has clear purpose
- README in key directories

**3. Domain-Driven:**
- Organized by function, not file type
- Easy to navigate

**4. Unified Configuration:**
- Single source of truth for defaults
- Clear override hierarchy

---

## 22. CLI Tool Best Practices (Typer/Click)

### Sources:
- [CodeCut - Comparing Python CLI Tools](https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/)
- [Dev.to - 7 Python CLI Libraries 2024](https://dev.to/aaravjoshi/7-python-cli-libraries-for-building-professional-command-line-tools-2024-guide-7ad)
- [Real Python - Click](https://realpython.com/python-click/)
- [Typer Documentation](https://typer.tiangolo.com/)

### CLI Library Comparison:

| Library | Pros | Cons | Best For |
|---------|------|------|----------|
| **argparse** | Built-in, no deps | Verbose, manual | Simple scripts |
| **Click** | Decorators, composable | More boilerplate | Complex CLIs |
| **Typer** | Type hints, minimal code | Built on Click | Modern CLIs |

### Recommended: Typer

**Why Typer:**
- Uses Python type hints (cleaner code)
- Automatic help generation
- Automatic validation
- Built on Click (battle-tested)
- Less boilerplate than Click

### CLI Design Best Practices:

**1. Clear Documentation:**
```python
@app.command()
def add_repo(
    name: str = typer.Argument(..., help="Repository name"),
    language: str = typer.Option("python", help="Language: java or python"),
    branch: str = typer.Option("main", help="Default branch"),
):
    """Add a new repository to the hub configuration."""
```

**2. Consistent Naming:**
- Use kebab-case for commands: `add-repo`, `list-repos`
- Use snake_case for Python functions
- Keep command names short but descriptive

**3. Error Handling:**
```python
if not config_path.exists():
    typer.echo(f"Error: Config not found at {config_path}", err=True)
    raise typer.Exit(code=1)
```

**4. Feedback:**
- Use colors (typer.style)
- Show progress for long operations
- Confirm destructive actions

**5. Subcommands:**
```
hub-cli
├── repo
│   ├── add
│   ├── list
│   ├── remove
│   └── validate
├── config
│   ├── show
│   ├── lint
│   └── generate
└── run
    ├── all
    └── single
```

---

## 23. Interactive CLI Prompts

### Sources:
- [Questionary PyPI](https://pypi.org/project/questionary/)
- [InquirerPy GitHub](https://github.com/kazhala/InquirerPy)
- [PyInquirer GitHub](https://github.com/CITGuru/PyInquirer)

### Library Comparison:

| Library | Status | Features | Platform |
|---------|--------|----------|----------|
| **questionary** | Active | Modern, stable, prompt_toolkit 3 | Cross-platform |
| **InquirerPy** | Active | Feature-rich, fuzzy, async | Cross-platform |
| **PyInquirer** | Unmaintained | Original port | Cross-platform |
| **inquirer** | Active | Simple, stable | Unix mainly |

### Recommended: questionary or InquirerPy

### Prompt Types Available:

| Type | Use Case |
|------|----------|
| `text` | Free text input |
| `password` | Hidden input |
| `confirm` | Yes/No |
| `select` | Single choice from list |
| `checkbox` | Multiple choices |
| `path` | File/directory path |
| `autocomplete` | Searchable list |

### Example for Hub CLI:

```python
import questionary

def interactive_add_repo():
    answers = questionary.form(
        name = questionary.text("Repository name:"),
        language = questionary.select(
            "Language:",
            choices=["python", "java"]
        ),
        branch = questionary.text("Default branch:", default="main"),
        profile = questionary.select(
            "Apply profile:",
            choices=["none", "quality", "security", "strict"]
        ),
        tools = questionary.checkbox(
            "Enable tools:",
            choices=[
                "pytest", "ruff", "bandit", "mypy",
                "pip-audit", "black", "isort"
            ]
        ),
    ).ask()

    return answers
```

---

## 24. Config Validation (Pydantic + JSON Schema)

### Sources:
- [Pydantic JSON Schema Docs](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Couchbase - Pydantic Tutorial](https://www.couchbase.com/blog/validate-json-documents-in-python-using-pydantic/)

### Approach: Pydantic for Validation

**Why Pydantic:**
- 5-50x faster than alternatives
- Used by FastAPI, LangChain, OpenAI
- Type hints = self-documenting
- Auto-generates JSON Schema

**Key Insight:** Pydantic generates schemas but doesn't validate against external schemas. Use `jsonschema` library if you need to validate against existing JSON Schema files.

### Example for Hub Config:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ToolConfig(BaseModel):
    enabled: bool = True

class JaCoCoConfig(ToolConfig):
    min_coverage: int = Field(default=70, ge=0, le=100)

class PytestConfig(ToolConfig):
    min_coverage: int = Field(default=70, ge=0, le=100)
    fail_fast: bool = False

class JavaConfig(BaseModel):
    version: str = "21"
    distribution: str = "temurin"
    build_tool: str = Field(default="maven", pattern="^(maven|gradle)$")
    tools: dict[str, ToolConfig] = {}

class RepoConfig(BaseModel):
    owner: str
    name: str
    language: str = Field(pattern="^(java|python)$")
    default_branch: str = "main"

class HubConfig(BaseModel):
    repo: RepoConfig
    java: Optional[JavaConfig] = None
    python: Optional[PythonConfig] = None
```

### Validation in CLI:

```python
from pydantic import ValidationError
import yaml

def validate_config(path: Path) -> bool:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        HubConfig(**data)
        return True
    except ValidationError as e:
        typer.echo(f"Validation error: {e}", err=True)
        return False
```

---

## 25. SDLC Phasing & Rollout Strategy

### Sources:
- [TeachingAgile - Phased Deployment](https://teachingagile.com/sdlc/articles/phased-deployment-sdlc)
- [CircleCI - SDLC Phases](https://circleci.com/blog/sdlc-phases-and-best-practices/)
- [ProdPad - Phased Rollout](https://www.prodpad.com/blog/phased-rollout-strategy/)
- [DealHub - Phased Implementation](https://dealhub.io/glossary/phased-implementation/)

### Benefits of Phased Rollout:

| Benefit | Description |
|---------|-------------|
| Risk Mitigation | Fix issues in smaller sets |
| User Adaptability | Users adapt gradually |
| Quality Assurance | Gather feedback each phase |
| Faster Feedback | Learn early, adjust often |

### Deployment Strategies:

| Strategy | Description | Risk Level |
|----------|-------------|------------|
| **Canary** | Small % first, then expand | Lowest |
| **Blue-Green** | Two environments, switch traffic | Low |
| **Pilot** | Test in one dept/branch first | Low |
| **Big Bang** | All at once | Highest |

### Phased Delivery Best Practices:

**1. Each Phase Must Stand Alone:**
- Phase 1 should work without Phase 2
- Users may never upgrade

**2. Define Essential Features:**
- What MUST be in each phase?
- What can wait?

**3. Stay Alert Between Phases:**
- Gather feedback
- Adjust plan as needed

**4. Avoid Scope Creep:**
- Return to core goal each phase
- "Does this solve the user problem?"

### Applied to Hub-Release:

| Phase | Deliverable | Stands Alone? |
|-------|-------------|---------------|
| 0 | Research + Roadmap | Yes (planning docs) |
| 1 | Documentation | Yes (users can read) |
| 2 | Templates | Yes (users can copy) |
| 3 | Production Fixes | Yes (improves existing) |
| 4 | Aggregation | Yes (better metrics) |
| 5 | Dashboard | Yes (visualization) |
| 6 | Fixtures | Yes (testing) |
| 7 | Release | Yes (formal release) |

---

## 26. MoSCoW Prioritization Method

### Sources:
- [Wikipedia - MoSCoW Method](https://en.wikipedia.org/wiki/MoSCoW_method)
- [NetSolutions - MVP Feature Prioritization](https://www.netsolutions.com/hub/minimum-viable-product/prioritize-features/)
- [Product School - MoSCoW](https://productschool.com/blog/product-strategy/moscow-prioritization)
- [TekXAI - MoSCoW for MVP](https://tekxai.com/moscow-method-for-mvp-features/)

### The Four Categories:

| Priority | Meaning | Description |
|----------|---------|-------------|
| **M**ust Have | Critical | Non-negotiable, product won't work without |
| **S**hould Have | Important | Adds significant value, not essential |
| **C**ould Have | Nice-to-have | Extra value, can add later |
| **W**on't Have | Not now | Defer to future iterations |

### Hub-Release MoSCoW:

**Must Have (MVP):**
- Central execution for Java/Python
- Boolean toggles (enabled: true/false)
- Config hierarchy (defaults → repo override)
- Step summary with metrics
- Basic documentation

**Should Have:**
- Comprehensive tool documentation
- Heavily commented templates
- ADRs for key decisions
- Production gap fixes
- Config validation

**Could Have:**
- GitHub Pages dashboard
- CLI tool for config management
- Fixture repos for testing
- Distributed mode improvements
- Historical trend data

**Won't Have (Yet):**
- PyQt6 GUI
- Support for languages beyond Java/Python
- Real-time dashboard
- Slack/email notifications (beyond stub)
- Load testing tools

---

## 27. Developer Experience (DX) Principles

### Sources:
- [CodiLime - What is DX](https://codilime.com/blog/developer-experience-what-is-dx-and-why-you-should-care/)
- [Argo Project - Building DX](https://blog.argoproj.io/building-the-developer-experience-dx-from-the-ground-up-8254d50457f5)
- [OpsLevel - UX Principles for DX](https://www.opslevel.com/resources/devex-series-part-2-how-tooling-affects-developer-experience-devex)
- [Addy Osmani - DX Book](https://addyosmani.com/dx/)

### DX Priority:
```
User Experience > Developer Experience > Ease of Implementation
```

### Key DX Traits:

| Trait | Description |
|-------|-------------|
| Usability | Easy to use, intuitive |
| Reliability | Works consistently |
| Findability | Easy to discover features |
| Usefulness | Solves real problems |
| Accessibility | Works for all skill levels |
| Documentation | Clear, comprehensive docs |

### DX Best Practices for CLI:

**1. Great Feedback:**
- Informative (explain what's happening)
- Specific (exact error, not generic)
- Contextual (relevant to action)
- Brief (not overwhelming)

**2. Reduce Cognitive Load:**
- Sensible defaults
- Clear help text
- Consistent patterns
- Progressive disclosure

**3. Fast Iteration:**
- Quick setup (clone → run in minutes)
- Fast tests
- Clear errors
- Good debugging support

### Applied to Hub CLI:

```bash
# Good DX examples:
$ hub-cli repo add my-repo --language python
✓ Created config/repos/my-repo.yaml
✓ Validated against schema
→ Next: Run 'hub-cli run single my-repo' to test

$ hub-cli config lint
✓ config/defaults.yaml: valid
✓ config/repos/repo-a.yaml: valid
✗ config/repos/repo-b.yaml: invalid
  └─ Line 12: 'langauge' is not a valid key (did you mean 'language'?)
```

---

## 28. Hub CLI Tool Specification

### Proposed CLI Structure:

```
hub-cli
├── repo
│   ├── add          # Interactive or flag-based repo addition
│   ├── list         # List all configured repos
│   ├── show <name>  # Show config for a repo
│   ├── remove       # Remove repo config
│   └── validate     # Validate a repo config
├── config
│   ├── lint         # Validate all configs against schema
│   ├── show         # Show merged config for a repo
│   ├── generate     # Generate config from template
│   └── diff         # Show diff between configs
├── profile
│   ├── list         # List available profiles
│   ├── show <name>  # Show profile contents
│   └── apply        # Apply profile to repo
├── run
│   ├── all          # Trigger hub-run-all workflow
│   └── single       # Test single repo locally
└── docs
    ├── render       # Generate docs from templates
    └── serve        # Serve docs locally
```

### Key Features:

| Feature | Description | Priority |
|---------|-------------|----------|
| `repo add` | Interactive prompts or flags | P0 |
| `repo add --dry-run` | Preview without writing | P0 |
| `config lint` | Validate all configs | P0 |
| `profile apply` | Apply quality/security preset | P1 |
| `config generate` | Generate from template | P1 |
| `run single` | Test locally before push | P2 |

### Tech Stack:

| Component | Library | Why |
|-----------|---------|-----|
| CLI Framework | Typer | Modern, type hints |
| Prompts | questionary | Cross-platform, modern |
| Validation | Pydantic | Fast, generates schema |
| YAML | ruamel.yaml | Preserves comments |
| Output | Rich | Pretty tables, colors |

### Example Usage:

```bash
# Interactive mode
$ hub-cli repo add
? Repository name: my-new-repo
? Language: python
? Default branch: main
? Apply profile: security
? Enable additional tools: [x] mypy, [x] hypothesis
✓ Created config/repos/my-new-repo.yaml

# Flag mode
$ hub-cli repo add my-repo --language java --profile quality --dry-run

# Validation
$ hub-cli config lint --fix  # Auto-fix simple issues
```

---

## 29. Additional Research Topics Identified

### Still Need to Research:
- [ ] ruamel.yaml for comment-preserving YAML writes
- [ ] Rich library for pretty CLI output
- [ ] GitHub CLI (gh) integration patterns
- [ ] Local workflow testing (act)
- [ ] Semantic versioning for hub releases

### Covered in This Research:
- [x] ADR / MADR templates
- [x] GitHub Actions reusable workflows
- [x] Diátaxis documentation framework
- [x] Self-documenting YAML
- [x] Feature toggles / boolean flags
- [x] CI/CD template repos
- [x] SDLC phases
- [x] SRS requirements docs
- [x] Monorepo organization
- [x] SLSA / supply chain
- [x] GitHub Pages dashboards
- [x] CLI tools (Typer/Click)
- [x] Interactive prompts (questionary)
- [x] Config validation (Pydantic)
- [x] Phased rollout strategy
- [x] MoSCoW prioritization
- [x] Developer Experience (DX)

---

## 30. AGENTS.md Best Practices

### Sources:
- [GitHub Blog - How to Write a Great AGENTS.md](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
- [AGENTS.md Official Site](https://agents.md/)
- [GitHub - agentsmd/agents.md](https://github.com/agentsmd/agents.md)
- [OpenAI Codex - AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md/)
- [Builder.io - Improve AI Output with AGENTS.md](https://www.builder.io/blog/agents-md)
- [Claude Blog - Using CLAUDE.md Files](https://claude.com/blog/using-claude-md-files)

### What is AGENTS.md?

A simple, open format for guiding AI coding agents. Think of it as a **README for AI agents**.

- 60,000+ open-source projects already use it
- Backed by Google, OpenAI, Cursor, Factory, Sourcegraph
- Stewarded by Agentic AI Foundation (Linux Foundation)
- No schema or special tooling required - just Markdown

### Why AGENTS.md?

| README.md | AGENTS.md |
|-----------|-----------|
| For humans | For AI agents |
| Quick starts, descriptions | Build commands, tests, conventions |
| High-level overview | Detailed context agents need |

### The 6 Core Areas to Cover:

1. **Commands** - Build, test, lint, format commands
2. **Testing** - How to run tests, frameworks used
3. **Project Structure** - Where code lives, key directories
4. **Code Style** - Formatting, patterns, conventions
5. **Git Workflow** - Branch naming, commit format, PR process
6. **Boundaries** - What agents should never do

### Three-Tier Boundaries:

| Tier | Meaning | Examples |
|------|---------|----------|
| **Always Do** | Safe, encouraged | Read files, lint, format |
| **Ask First** | Needs confirmation | Install packages, git push, delete files |
| **Never Do** | Forbidden | Commit secrets, modify production, force push |

### Best Practices:

**1. Keep it Concise:**
- Aim for ≤ 150 lines
- Long files slow agents and bury signal

**2. Be Specific:**
```
BAD:  "This is a React project"
GOOD: "React 18 with TypeScript 5.3, Vite 5, Tailwind CSS 3.4"
```

**3. Lead with Commands:**
```markdown
## Commands
- `pnpm install` - Install dependencies
- `pnpm test` - Run all tests
- `pnpm lint` - Lint code
- `pnpm build` - Build for production
```

**4. File-Scoped Commands:**
```markdown
## Per-File Commands
- Type-check: `pnpm tsc --noEmit <file>`
- Lint: `pnpm eslint <file>`
- Test: `pnpm test <file>.test.ts`
```

**5. Use Nested Files for Monorepos:**
- Place AGENTS.md in each subproject
- Nearest file takes precedence
- Each package gets tailored instructions

**6. Link to Existing Docs:**
- Don't duplicate README
- Point to detailed docs when needed

### Tool-Specific Files:

| Tool | File | Location |
|------|------|----------|
| Universal | `AGENTS.md` | Project root |
| Claude Code | `CLAUDE.md` | Project root |
| GitHub Copilot | `copilot-instructions.md` | `.github/` |
| VS Code | `*.instructions.md` | `.github/instructions/` |
| JetBrains | `*.md` | `.aiassistant/rules/` |
| Continue | `.continuerules` | Project root |

### Cross-Tool Compatibility:

```markdown
# CLAUDE.md
Strictly follow the rules in ./AGENTS.md
```

### Example Structure:

```markdown
# AGENTS.md

## Project Overview
Brief context about the repository.

## Commands
- `npm install` - Install deps
- `npm test` - Run tests
- `npm run build` - Build

## Project Structure
- `src/` - Source code
- `tests/` - Test files
- `docs/` - Documentation

## Code Style
- TypeScript strict mode
- Single quotes, no semicolons
- 2-space indent

## Testing
- Jest for unit tests
- Run `npm test -- --watch` for dev

## Git Workflow
- Branch: `feature/description`
- Commits: conventional commits
- PRs require review

## Boundaries

### Always OK
- Read any file
- Run lint/format/test
- Create new files in src/

### Ask First
- Install new packages
- Delete files
- Modify configs

### Never
- Commit secrets or .env
- Force push
- Modify CI workflows without review
```

---

## 31. Research Complete

All major research compiled. Ready to:
1. Create AGENTS.md for hub-release
2. Create ADR directory and first ADRs
3. Begin Phase 1 implementation

### Documents Created:
- `docs/RESEARCH.md` - This file (~1700 lines)
- `docs/ROADMAP.md` - Phased implementation plan

### Topics Covered (31 total):
- ADR/MADR, GitHub Actions, Diátaxis, YAML, Feature Toggles
- CI/CD Templates, SDLC, SRS, Monorepo, SLSA
- CLI (Typer), Prompts (questionary), Validation (Pydantic)
- Phased Rollout, MoSCoW, Developer Experience
- Hub CLI Specification, AGENTS.md Best Practices
