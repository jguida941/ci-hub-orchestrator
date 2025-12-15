# CI/CD Hub

A **centralized CI/CD orchestration hub** that tests ALL your repositories from one place.

**Key Principle:** The hub clones and tests your repos. **Repos don't need ANY workflow files.**

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        CI/CD HUB                            │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Run All     │  │ Security &  │  │ Hub         │         │
│  │ Repos       │  │ Supply Chain│  │ Orchestrator│         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              config/repos/*.yaml                     │   │
│  │  - contact-suite-spring-react.yaml                  │   │
│  │  - java-spring-tutorials.yaml                       │   │
│  │  - your-repo.yaml                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ Repo A   │    │ Repo B   │    │ Repo C   │
     │ (cloned) │    │ (cloned) │    │ (cloned) │
     └──────────┘    └──────────┘    └──────────┘

     NO WORKFLOW FILES NEEDED IN YOUR REPOS!
```

## Features

### Java Tools
| Tool | Purpose | Report |
|------|---------|--------|
| **JaCoCo** | Code coverage | % with progress bar |
| **Checkstyle** | Code style | Violation count |
| **SpotBugs** | Bug detection | Bug count |
| **OWASP** | Dependency vulnerabilities | Critical/High/Medium/Low |
| **PITest** | Mutation testing | Score with killed/survived |
| **CodeQL** | SAST security analysis | Alerts |

### Python Tools
| Tool | Purpose | Report |
|------|---------|--------|
| **pytest-cov** | Test coverage | % with progress bar |
| **Ruff** | Linting + security rules | Issue count |
| **Bandit** | Security scanner | High/Medium/Low |
| **pip-audit** | Dependency vulnerabilities | Vuln count |
| **Black** | Code formatting | Files to reformat |
| **mypy** | Type checking | Error count |
| **CodeQL** | SAST security analysis | Alerts |

### Supply Chain Security
| Tool | Purpose |
|------|---------|
| **SBOM** | Software Bill of Materials (Syft) |
| **CodeQL** | Static Application Security Testing |
| **ZAP** | Dynamic Application Security Testing |
| **Dependency Review** | PR dependency changes |

## Quick Start

### 1. Add Your Repository (ONE config file, that's it!)

Create `config/repos/your-repo.yaml`:

```yaml
repo:
  owner: your-github-username
  name: your-repo-name
  language: java  # or python
  default_branch: main
```

### 2. Run the Hub

From GitHub Actions:
```bash
# Run all repos
gh workflow run "Hub: Run All Repos"

# Run specific repos
gh workflow run "Hub: Run All Repos" -f repos="my-repo,other-repo"

# Run security scans
gh workflow run "Hub: Security & Supply Chain"
```

**That's it!** No files needed in your repos.

## Workflows

### `hub-run-all.yml` - Test All Repos
- Clones each configured repo
- Detects language (Java/Python)
- Runs ALL quality tools
- Generates beautiful QA metrics reports
- Uploads all artifacts centrally

### `hub-security.yml` - Security & Supply Chain
- CodeQL SAST analysis
- SBOM generation
- pip-audit / OWASP dependency check
- Bandit / Ruff security rules
- Optional ZAP DAST scanning

### `hub-orchestrator.yml` - Trigger External Workflows
- For repos that DO have their own workflows
- Triggers via repository_dispatch

## Reports Generated

The hub generates **beautiful GitHub Step Summaries** like this:

```
┌─────────────────────────────────────────────────────────────┐
│ QA Metrics (Java)                                           │
├────────────────────┬─────────────────┬─────────────────────┤
│ Metric             │ Result          │ Details             │
├────────────────────┼─────────────────┼─────────────────────┤
│ Tests              │ 1082 executed   │ Runtime: 37.1s      │
│ Line Coverage      │ 89% ████████░░  │ 2592/2912 lines     │
│ Mutation Score     │ 83% ████████░░  │ 1159 killed         │
│ Dependency-Check   │ scan complete   │ 0 vulnerabilities   │
│ SpotBugs           │ 0 bugs          │ Static analysis     │
│ Checkstyle         │ 0 violations    │ Code style          │
└────────────────────┴─────────────────┴─────────────────────┘

Quality Gates:
✅ Unit Tests    - Passed
✅ Checkstyle    - Passed
✅ SpotBugs      - Passed
✅ JaCoCo        - Generated
✅ OWASP Check   - Passed
```

## Directory Structure

```
hub-release/
├── .github/workflows/
│   ├── hub-run-all.yml          # 🎯 Main: Test all repos
│   ├── hub-security.yml         # 🔒 Security & SBOM
│   ├── hub-orchestrator.yml     # 📡 Trigger external workflows
│   ├── java-ci.yml              # (Reusable if needed)
│   └── python-ci.yml            # (Reusable if needed)
├── config/
│   ├── defaults.yaml            # Global settings
│   ├── repos/                   # ⭐ YOUR REPOS GO HERE
│   │   ├── contact-suite-spring-react.yaml
│   │   └── java-spring-tutorials.yaml
│   └── optional/                # Optional features
├── policies/kyverno/            # K8s admission policies
├── dashboards/                  # Visualization definitions
├── schema/                      # JSON schemas
├── scripts/                     # Helper scripts
└── docs/                        # Documentation
```

## Adding a New Repository

**Step 1:** Create config file

```bash
# In the hub repo
cat > config/repos/my-new-repo.yaml << 'EOF'
repo:
  owner: jguida941
  name: my-new-repo
  language: java
  default_branch: main
EOF
```

**Step 2:** Commit and push

```bash
git add config/repos/my-new-repo.yaml
git commit -m "Add my-new-repo to hub"
git push
```

**Step 3:** Run the hub - Done!

## Requirements

### For Java Repos
- Maven or Gradle build file (`pom.xml` or `build.gradle`)
- Standard project structure
- (Optional) JaCoCo, Checkstyle, SpotBugs, PITest plugins

### For Python Repos
- `requirements.txt` or `pyproject.toml`
- Tests in standard locations (`tests/`, `test_*.py`)

### Hub Requirements
- GitHub Actions enabled
- Permissions to read target repos (public or same org)

## Configuration Options

### Repo Config

```yaml
repo:
  owner: jguida941
  name: my-repo
  language: java          # java | python
  default_branch: main    # or master

# Optional overrides
java:
  version: "21"
  tools:
    pitest:
      enabled: false      # Disable mutation testing
    docker:
      enabled: true       # Enable Docker testing
```

### Skipping Tools

Set in repo config to disable specific tools:

```yaml
java:
  tools:
    pitest:
      enabled: false
    owasp:
      enabled: false
```

## Connected Repositories

| Repository | Language | Status |
|------------|----------|--------|
| contact-suite-spring-react | Java | Configured |
| java-spring-tutorials | Java | Configured |

---

**The hub is the central brain. Your repos stay clean. One place to rule them all.**
