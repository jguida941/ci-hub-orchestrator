> **⚠️ SUPERSEDED**: This document has been merged into [GETTING_STARTED.md](GETTING_STARTED.md).
> See the **Distributed Mode: Repo-Side Setup** and **Secrets Setup** sections there.
> This file is kept for historical reference only.

---

# Dispatch Setup (Reusable Workflows) (Archived)

Use this guide to enable cross-repo dispatch from the hub orchestrator.

## When to use dispatch
- You need the target repo's runners/secrets or prefer repo-owned CI.
- You want CI results to appear in the target repo's Actions tab.
- Target repos have custom build requirements beyond hub capabilities.
- If a repo is central-only (no workflows), set `repo.dispatch_enabled: false` in its hub config.

## Dispatch Workflow Callers (Recommended)

The hub now uses a thin caller workflow (`hub-ci.yml`) that invokes the reusable workflows. This prevents drift and keeps inputs consistent.

### Recommended: cihub CLI

1. **Generate caller + config in the target repo:**
   ```bash
   cd /path/to/your-repo
   python -m cihub init --repo . --apply
   ```
   This creates:
   - `.ci-hub.yml`
   - `.github/workflows/hub-ci.yml`

2. **Commit and push:**
   ```bash
   git add .ci-hub.yml .github/workflows/hub-ci.yml
   git commit -m "Add hub CI caller"
   git push
   ```

### Manual fallback (same result)

Copy the caller template and rename it to `hub-ci.yml`:
```bash
# Java
cp templates/repo/hub-java-ci.yml /path/to/your-repo/.github/workflows/hub-ci.yml

# Python
cp templates/repo/hub-python-ci.yml /path/to/your-repo/.github/workflows/hub-ci.yml
```

### Legacy dispatch templates (archived)

These are archived for historical reference and should not be used for new repos:
- `templates/legacy/java-ci-dispatch.yml`
- `templates/legacy/python-ci-dispatch.yml`

### What Tools Are Included

**Java template tools:**
- JaCoCo (coverage)
- Checkstyle (code style violations)
- SpotBugs (bug detection)
- PMD (static analysis)
- OWASP Dependency Check (vulnerability scanning)
- PITest (mutation testing)
- Semgrep (SAST)
- Trivy (container/filesystem scanning)

**Python template tools:**
- pytest + coverage (tests & coverage)
- Ruff (linting)
- Black (formatting check)
- isort (import sorting)
- mypy (type checking)
- Bandit (security scanning)
- pip-audit (dependency vulnerabilities)
- mutmut (mutation testing)
- Semgrep (SAST)
- Trivy (container/filesystem scanning)

All tools are toggle-controlled via config. See [TOOLS.md](../reference/TOOLS.md) for details.

### report.json Format

The caller workflow generates a `report.json` artifact that the hub aggregates:

```json
{
  "repo": "owner/repo",
  "language": "java|python",
  "results": {
    "coverage": 85,           // % or null if not run
    "mutation_score": 70,     // % or null if not run
    "checkstyle_violations": 5,
    "spotbugs_bugs": 0,
    // ... all tool metrics
  },
  "tools_ran": {
    "jacoco": true,
    "checkstyle": true,
    "spotbugs": false,        // Tool was disabled
    // ...
  }
}
```

- **`null`** = tool didn't run (shows `-` in summary)
- **`0`** = tool ran, found nothing (shows `0` in summary)

See [ADR-0013](../adr/0013-dispatch-workflow-templates.md#comprehensive-reporting-updated-2025-12-15) for complete schema

## Secrets Setup

The hub requires two secrets for full functionality:

| Secret | Required For | Scope |
|--------|--------------|-------|
| `HUB_DISPATCH_TOKEN` | Distributed mode (cross-repo dispatch + artifact download) | Hub repo |
| `NVD_API_KEY` | Fast OWASP Dependency Check scans (Java repos) | Java repos |

### Step 1: Create a GitHub PAT

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. **Classic PAT (recommended):** Generate new token (classic) → scopes: `repo` + `workflow`
3. **Fine-grained PAT (stricter):**
   - Resource owner: your account
   - Repository access: include hub + all target repos
   - Permissions: Actions Read/Write, Contents Read, Metadata Read
4. Generate and copy the token

### Step 2: Set HUB_DISPATCH_TOKEN

**Using cihub CLI (recommended):**
```bash
# Set on hub repo with verification (recommended)
cihub setup-secrets --hub-repo owner/hub-repo --verify

# Also set on all connected repos
cihub setup-secrets --hub-repo owner/hub-repo --all --verify
```

The CLI verifies:
1. Token authenticates successfully
2. Token has cross-repo access (can read artifacts from connected repos)

**Manual method:**
```bash
gh secret set HUB_DISPATCH_TOKEN -R owner/hub-repo
```

### Step 3: Set NVD_API_KEY (Java repos)

Without an NVD API key, OWASP Dependency Check downloads 300K+ vulnerability records without rate limiting, taking 30+ minutes. With a key, it takes ~2-3 minutes.

1. Get a free key at: https://nvd.nist.gov/developers/request-an-api-key
2. Set the secret on all Java repos:

```bash
# Using CLI (recommended) - automatically detects Java repos
cihub setup-nvd --verify

# Manual method
gh secret set NVD_API_KEY -R owner/java-repo
```

The CLI:
- Reads `config/repos/*.yaml` to find Java repos
- Verifies the NVD key works before storing
- Sets `NVD_API_KEY` on each Java repo

## Configure repos
- Hub config: set `repo.dispatch_enabled: false` for central-only repos (e.g., fixtures). Default is true.
- Set `repo.dispatch_workflow` to specify the workflow file to dispatch to (default when using CLI: `hub-ci.yml`).
- Dispatchable repos must have a workflow with `workflow_dispatch` that accepts the hub inputs (use the caller templates).
- Use `repo.run_group` (full/fixtures/smoke) and the `run_group` workflow input to limit which configs the hub runs.

## Artifact naming
- Orchestrator uploads artifacts with repo-specific names to avoid collisions; keep unique names if adding artifacts.

## Troubleshooting
- `Workflow does not have 'workflow_dispatch' trigger`: Target repo workflow missing `workflow_dispatch` trigger. Copy the caller template to the target repo.
- `Unexpected inputs provided`: Target workflow doesn't accept the inputs the hub sends. Use the caller templates which accept all hub inputs.
- `Resource not accessible by integration`: token lacks `actions:write`/`contents:read` on target repo.
- `404 workflow` / `Not Found`: target repo has no dispatchable workflow, or `dispatch_workflow` config points to wrong filename.
- Artifact `409 Conflict`: artifacts are now named with repo/run id; keep names unique if adding more.
- Multiple entries for same repo: hub-run-all and orchestrator include `config_basename` and `subdir` in job/artifact names to disambiguate when multiple configs point to the same repo.

## Related
- [ADR-0013: Dispatch Workflow Templates](../adr/0013-dispatch-workflow-templates.md)
- [ADR-0014: Reusable Workflow Migration](../adr/0014-reusable-workflow-migration.md)
- [TEMPLATES.md](TEMPLATES.md) - All available templates
