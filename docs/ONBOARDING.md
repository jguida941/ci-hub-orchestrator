# Onboarding a New Repository

This guide shows how to connect your repository to the CI/CD Hub.

**Choose your mode:**
- **Central Mode (Recommended):** Hub clones and tests repos. Repos stay clean - no workflow files needed.
- **Distributed Mode:** Repos have their own workflow files that call hub's reusable workflows.

---

## Quick Start: Central Mode (5 minutes)

The hub clones your repo and runs all CI tools. You only add a config file to the hub.

### Step 1: Create Hub Config

```bash
# Copy a profile template
cp templates/profiles/java-fast.yaml config/repos/my-repo.yaml

# Or for Python
cp templates/profiles/python-fast.yaml config/repos/my-repo.yaml
```

### Step 2: Edit Repo Metadata

Edit `config/repos/my-repo.yaml` to add your repo details:

```yaml
repo:
  owner: your-github-handle
  name: your-repo-name
  language: java  # or python
  default_branch: main

# Profile settings are already included from the template
# Only change what you need to customize
```

### Step 3: Validate and Run

```bash
# Validate your config
python scripts/validate_config.py config/repos/my-repo.yaml

# Run the hub (via GitHub Actions UI or CLI)
gh workflow run hub-run-all.yml
```

**Done!** The hub will clone your repo and run all configured tools.

---

## Advanced: Distributed Mode (15 minutes)

Use this if your repo needs its own runners, secrets, or you prefer repo-controlled CI.

### Step 1: Add Hub Config (Optional)

Same as central mode - create `config/repos/my-repo.yaml` if you want the hub to track this repo.

### Step 2: Add Workflow to Your Repo

Create `.github/workflows/ci.yml` in your repository:

#### Java Projects

```yaml
name: CI

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@main
    with:
      java_version: '21'
      run_jacoco: true
      run_checkstyle: true
      run_spotbugs: true
      run_owasp: true
      run_pitest: false      # Expensive - enable when needed
      run_codeql: false      # Expensive - enable when needed
      coverage_min: 70
    secrets: inherit
```

#### Python Projects

```yaml
name: CI

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ci:
    uses: jguida941/ci-cd-hub/.github/workflows/python-ci.yml@main
    with:
      python_version: '3.12'
      run_pytest: true
      run_ruff: true
      run_bandit: true
      run_pip_audit: true
      run_mutmut: false      # Expensive - enable when needed
      run_codeql: false      # Expensive - enable when needed
      coverage_min: 70
    secrets: inherit
```

### Step 3: (Optional) Add Local Overrides

Add `.ci-hub.yml` to your repo root for repo-controlled settings:

```yaml
version: "1.0"
language: java

java:
  tools:
    pitest:
      enabled: false
    jacoco:
      min_coverage: 80
    docker:
      enabled: true
```

---

## Java: Required Maven Plugins

For Java projects, ensure your `pom.xml` has the necessary plugins:

```xml
<build>
  <plugins>
    <!-- JaCoCo for coverage -->
    <plugin>
      <groupId>org.jacoco</groupId>
      <artifactId>jacoco-maven-plugin</artifactId>
      <version>0.8.11</version>
    </plugin>

    <!-- Checkstyle -->
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-checkstyle-plugin</artifactId>
      <version>3.3.1</version>
    </plugin>

    <!-- SpotBugs -->
    <plugin>
      <groupId>com.github.spotbugs</groupId>
      <artifactId>spotbugs-maven-plugin</artifactId>
      <version>4.8.3.1</version>
    </plugin>

    <!-- OWASP Dependency Check (optional) -->
    <plugin>
      <groupId>org.owasp</groupId>
      <artifactId>dependency-check-maven</artifactId>
      <version>9.0.9</version>
    </plugin>

    <!-- PITest Mutation Testing (optional) -->
    <plugin>
      <groupId>org.pitest</groupId>
      <artifactId>pitest-maven</artifactId>
      <version>1.15.3</version>
    </plugin>
  </plugins>
</build>
```

---

## Verify Setup

1. Push changes (if distributed) or trigger hub workflow (if central)
2. Check the Actions tab for the workflow run
3. Verify artifacts are generated
4. Check the summary for metrics

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Workflow file not found" | Ensure hub repo is public or you have access |
| "PITest fails" | Ensure test classes exist; disable pitest first |
| "OWASP is slow" | Add `NVD_API_KEY` secret ([get free key](https://nvd.nist.gov/developers/request-an-api-key)) |
| "Docker build fails" | Ensure Dockerfile exists; set `run_docker: true` only if needed |
| "Coverage is 0%" | Check test files are running; verify pytest/JaCoCo setup |

For more issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## See Also

- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - All config options
- [TOOLS.md](TOOLS.md) - What tools are available
- [MODES.md](MODES.md) - Central vs Distributed explained
- [templates/profiles/](../templates/profiles/) - Pre-built profiles
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Fix common issues
