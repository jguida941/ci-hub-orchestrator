# Getting Started with CI/CD Hub

This guide walks you through setting up and using the CI/CD Hub CLI from scratch.
By the end, you'll have validated the CLI works end-to-end on your machine.

---

## Prerequisites

### 1. Clone the Repository

```bash
# Clone the hub
git clone https://github.com/jguida941/ci-cd-hub.git
cd ci-cd-hub

# Optional (maintainers only): clone fixtures for hub CI smoke tests
# git clone https://github.com/jguida941/ci-cd-hub-fixtures.git ../ci-cd-hub-fixtures
```

### 2. Set Up Python Environment

```bash
# Create virtual environment (Python 3.11+ required)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"      # Core + development
pip install -e ".[ci]"       # CI tool runners (pytest, ruff, etc.)
pip install -e ".[wizard]"   # Optional: interactive wizard
```

### 3. Verify Installation

```bash
# Check Python version (must be 3.11+)
python --version

# Check CLI is available
python -m cihub --version

# Check gh CLI (needed for GitHub operations)
gh --version
gh auth status
```

Expected output:
```
Python 3.11.x or higher
cihub 0.x.x
gh version 2.x.x
Logged in to github.com as <your-username>
```

If `gh auth status` fails, run:
```bash
gh auth login
```

---

## Quick Start (3 Commands)

Test the CLI on a scaffolded Python fixture in under 2 minutes:

```bash
# 0. Optional: preflight check
python -m cihub preflight

# 1. Scaffold a minimal repo
WORKDIR=$(mktemp -d)
python -m cihub scaffold python-pyproject "$WORKDIR/cihub-sample"

# 2. Run smoke test (detect → init → validate)
python -m cihub smoke "$WORKDIR/cihub-sample"

# 3. Optional: full run (runs cihub ci)
python -m cihub smoke --full "$WORKDIR/cihub-sample"
```

Expected:
- `detect`, `init`, and `validate` succeed
- With `--full`: `.cihub/report.json` and `.cihub/summary.md` created

---

## Choosing Your Execution Mode

The hub supports two execution modes. **Central mode is the default and recommended** for most users.

### Quick Comparison

| Aspect | Central Mode | Distributed Mode |
|--------|--------------|------------------|
| **Default** | Yes | No (opt-in) |
| **Where CI runs** | In the hub repo | In each target repo |
| **Repos need workflows** | No | Yes |
| **Permissions needed** | `contents:read` | `contents:read` + `actions:write` |
| **Setup complexity** | Low | High |

### Decision Flowchart

```
Start
  │
  ▼
Do target repos NEED to run CI in their own environment?
  │
  ├─ NO ──► Use CENTRAL MODE (recommended)
  │
  ▼ YES
  │
Do you have actions:write on target repos?
  │
  ├─ NO ──► Use CENTRAL MODE (can't dispatch)
  │
  ▼ YES
  │
Are target repos set up with workflow_dispatch workflows?
  │
  ├─ NO ──► Set them up, or use CENTRAL MODE
  │
  ▼ YES
  │
Use DISTRIBUTED MODE
```

Control via `repo.use_central_runner`:
- `true` (default) = Central mode
- `false` = Distributed mode

---

## Central Mode: Hub Config (5 minutes)

The hub clones your repo and runs all CI tools. You only add a config file to the hub.

### Step 1: Create Hub Config

```bash
# Copy a profile template
cp templates/profiles/java-fast.yaml config/repos/my-repo.yaml

# Or for Python
cp templates/profiles/python-fast.yaml config/repos/my-repo.yaml
```

### Step 2: Edit Repo Metadata

Edit `config/repos/my-repo.yaml`:

```yaml
repo:
  owner: your-github-handle
  name: your-repo-name
  language: java  # or python
  default_branch: main

# Profile settings are already included from the template
```

### Step 3: Validate and Run

```bash
# Validate your config
make validate-config REPO=my-repo

# Run the hub (via GitHub Actions UI or CLI)
gh workflow run hub-run-all.yml
```

**Done!** The hub will clone your repo and run all configured tools.

---

## Distributed Mode: Repo-Side Setup

Use this if your repo needs its own runners, secrets, or you prefer repo-controlled CI.

### Step 1: Generate Caller Workflow

```bash
cd /path/to/your-repo
python -m cihub init --repo . --apply
```

This creates:
- `.ci-hub.yml` - repo-local config
- `.github/workflows/hub-ci.yml` - caller workflow

### Step 2: Commit and Push

```bash
git add .ci-hub.yml .github/workflows/hub-ci.yml
git commit -m "Add hub CI caller"
git push
```

### Step 3: Configure Hub (Optional)

If you want the hub to track this repo:

```yaml
# config/repos/my-repo.yaml
repo:
  owner: your-github-handle
  name: your-repo-name
  language: java
  dispatch_enabled: true
  dispatch_workflow: hub-ci.yml
```

---


## Local Validation Checklist (Pre-Push)

Run this sequence before pushing workflow or CLI changes:

```bash
make preflight    # Environment checks
make lint         # Ruff lint
make typecheck    # mypy
make test         # pytest
make actionlint   # workflow syntax
make docs-check   # docs drift
make smoke        # full smoke test on scaffold
```

One-shot command:

```bash
make check
```

Or run the CLI wrapper directly:

```bash
python -m cihub check
```

Notes:
- `cihub validate --repo .` validates **repo-local** `.ci-hub.yml`.
- `make validate-config REPO=<name>` validates **hub configs** in `config/repos/`.

---

## How the CLI Works

### Config Precedence (highest wins)

```
repo .ci-hub.yml  →  hub config/repos/<repo>.yaml  →  hub config/defaults.yaml
```

### Key Commands

| Command | Purpose |
|---------|---------|
| `cihub preflight` | Check environment readiness |
| `cihub scaffold` | Generate a minimal test repo |
| `cihub smoke` | Run a local CLI smoke test |
| `cihub init` | Generate `.ci-hub.yml` + `hub-ci.yml` in a repo |
| `cihub validate` | Check config against schema |
| `cihub ci` | Run all enabled tools locally |
| `cihub run <tool>` | Run a single tool (Python only) |
| `cihub fix-pom` | Add missing Maven plugins (Java only) |
| `cihub config` | Manage hub-side repo configs |
| `cihub check` | Run the full local validation suite |
| `cihub docs generate` | Generate CLI and config reference docs |

Run `python -m cihub --help` for the full command list.

---

## Walkthrough: Python Repo

### Step 1: Prepare Workspace

```bash
WORKDIR=$(mktemp -d)
python -m cihub scaffold python-pyproject "$WORKDIR/python-pyproject"
cd "$WORKDIR/python-pyproject"
```

### Step 2: Detect Language

```bash
python -m cihub detect --repo .
```

Expected: `python`

### Step 3: Initialize

```bash
python -m cihub init \
  --repo . \
  --language python \
  --owner your-github-handle \
  --name your-repo-name \
  --branch main \
  --apply
```

Expected:
- `.ci-hub.yml` created with `language: python`
- `.github/workflows/hub-ci.yml` created

### Step 4: Validate

```bash
python -m cihub validate --repo .
```

Expected: `Config OK`

### Step 5: Run CI

```bash
python -m cihub ci --repo . --output-dir .cihub --install-deps
```

Expected:
- Tools run: pytest, ruff, black, isort, bandit, pip-audit (based on config)
- `.cihub/report.json` created
- `.cihub/summary.md` created

### Step 6: View Report

```bash
python -m cihub report summary --report .cihub/report.json
```

---

## Walkthrough: Java Maven Repo

### Step 1: Prepare Workspace

```bash
WORKDIR=$(mktemp -d)
python -m cihub scaffold java-maven "$WORKDIR/java-maven"
cd "$WORKDIR/java-maven"
```

### Step 2: Initialize

```bash
python -m cihub init \
  --repo . \
  --language java \
  --owner your-github-handle \
  --name your-repo-name \
  --branch main \
  --apply
```

### Step 3: Fix POM (Add Missing Plugins)

```bash
python -m cihub fix-pom --repo . --apply
```

Expected: Missing Maven plugins added to `pom.xml` (JaCoCo, Checkstyle, SpotBugs, etc.)

### Step 4: Validate and Run

```bash
python -m cihub validate --repo .
python -m cihub ci --repo . --output-dir .cihub
```

Note: Requires `mvn` or `./mvnw` in PATH.

---

## Walkthrough: Java Gradle Repo

Same as Maven, but:
- Skip `fix-pom` (Maven-only)
- Set `java.build_tool: gradle` in `.ci-hub.yml`
- Requires `gradle` or `./gradlew` in PATH

```bash
WORKDIR=$(mktemp -d)
python -m cihub scaffold java-gradle "$WORKDIR/java-gradle"
cd "$WORKDIR/java-gradle"

python -m cihub init --repo . --language java --owner test --name test --branch main --apply
python -m cihub validate --repo .
python -m cihub ci --repo . --output-dir .cihub
```

---

## Walkthrough: Monorepo (Subdir)

For repos with multiple projects in subdirectories:

```bash
WORKDIR=$(mktemp -d)
python -m cihub scaffold monorepo "$WORKDIR/monorepo"
cd "$WORKDIR/monorepo"

# Initialize with --subdir pointing to the project
python -m cihub init \
  --repo . \
  --language java \
  --owner test \
  --name test \
  --branch main \
  --subdir java \
  --apply

# Validate
python -m cihub validate --repo .

# Run CI (uses subdir from config)
python -m cihub ci --repo . --output-dir .cihub
```

The `.ci-hub.yml` will include `repo.subdir: java`.

---

## Secrets Setup (GitHub Actions)

For distributed mode and OWASP scans, configure these secrets:

### 1. Create a Personal Access Token (PAT)

1. Go to [GitHub Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Click **Generate new token**
3. Set:
   - **Token name:** `ci-cd-hub-dispatch`
   - **Expiration:** 90 days (or custom)
   - **Repository access:** Select repositories (hub + target repos)
   - **Permissions:**
     - **Actions:** Read and write
     - **Contents:** Read
     - **Metadata:** Read
4. Click **Generate token** and copy it

### 2. Set Hub Dispatch Secret

```bash
# Set on hub repo
gh secret set HUB_DISPATCH_TOKEN --repo your-org/ci-cd-hub

# Or use cihub CLI (recommended - also sets on connected repos)
python -m cihub setup-secrets --hub-repo your-org/ci-cd-hub --all --verify
```

### 3. Set Repo Variables (Target Repos)

In each target repo, set these variables:

```bash
gh variable set HUB_REPO --repo your-org/target-repo --body "your-org/ci-cd-hub"
gh variable set HUB_REF --repo your-org/target-repo --body "main"
```

### 4. Set NVD API Key (Java Repos Only)

For fast OWASP dependency scanning (2-3 min vs 30+ min):

1. Get a free API key at [NVD API Key Request](https://nvd.nist.gov/developers/request-an-api-key)
2. Set the secret:

```bash
gh secret set NVD_API_KEY --repo your-org/java-repo

# Or use cihub CLI
python -m cihub setup-nvd --verify
```

---

## Troubleshooting

### `python -m cihub: command not found`

**Fix:**
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### `Config validation failed`

**Fix:**
```bash
python -m cihub validate --repo . --json
```
Check `problems` array for specific errors.

### `gh: command not found`

**Fix:**
```bash
brew install gh  # macOS
# or: sudo apt install gh  # Ubuntu
gh auth login
```

### `Tool not found: mvn / gradle / pytest`

**Fix:** Install the tool:
```bash
brew install maven   # or gradle
pip install -e ".[ci]"  # Python tools
```

### `Permission denied` on GitHub Actions

**Fix:**
1. Verify PAT has `actions: write` permission
2. Re-run `python -m cihub setup-secrets --verify`
3. Check repo variables are set (HUB_REPO, HUB_REF)

### `OWASP scan fails with rate limit`

**Fix:**
```bash
python -m cihub setup-nvd --verify
```

For more issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Success Checklist

After completing this guide, verify:

- [ ] `python -m cihub --version` works
- [ ] `python -m cihub validate --repo <fixture>` returns `Config OK`
- [ ] `python -m cihub ci --repo <fixture>` produces `report.json`
- [ ] `.ci-hub.yml` and `.github/workflows/hub-ci.yml` generated correctly
- [ ] (Optional) GitHub Actions workflow runs successfully

---

## See Also

**Reference Docs:**
- [CLI Reference](../reference/CLI.md) - All CLI commands (generated)
- [Config Reference](../reference/CONFIG.md) - All config options (generated)
- [Tools Reference](../reference/TOOLS.md) - Tool availability and settings

**Advanced Guides:**
- [Monorepos](MONOREPOS.md) - Multi-project repo configuration
- [Templates](TEMPLATES.md) - Available config templates and profiles
- [Kyverno](KYVERNO.md) - Kubernetes admission control policies

**Maintainer Docs:**
- [Integration Smoke Test](INTEGRATION_SMOKE_TEST.md) - CLI validation guide
- [Workflows](WORKFLOWS.md) - Hub workflow details
