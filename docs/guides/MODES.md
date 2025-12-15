# Execution Modes

The CI/CD Hub supports two execution modes. **Central mode is the default and recommended** for most users.

---

## Quick Comparison

| Aspect | Central Mode | Distributed Mode |
|--------|--------------|------------------|
| **Default** | Yes | No (opt-in) |
| **Workflow** | `hub-run-all.yml` | `hub-orchestrator.yml` |
| **Where CI runs** | In the hub repo | In each target repo |
| **Repos need workflows** | No | Yes |
| **Permissions needed** | `contents:read` | `contents:read` + `actions:write` |
| **Tool availability** | ALL tools | Reusable workflow tools only |
| **Aggregation** | Immediate | Requires polling + artifact download |
| **Complexity** | Low | High |
| **Reliability** | High | Medium (more failure modes) |

---

## Central Mode (Default)

### What It Does

The hub clones each configured repository and runs the CI pipeline directly within the hub's GitHub Actions runner.

```
┌─────────────────┐
│   hub-release   │
│                 │
│  hub-run-all.yml│──┬── Clone repo-a ──► Run Java CI ──► Upload artifacts
│                 │  │
│                 │  ├── Clone repo-b ──► Run Python CI ──► Upload artifacts
│                 │  │
│                 │  └── Clone repo-c ──► Run Java CI ──► Upload artifacts
│                 │
│  Generate Summary ◄────────────────────────────────────┘
└─────────────────┘
```

### Prerequisites

1. **Hub Configuration:**
   - `config/repos/<repo>.yaml` for each target repo
   - Valid `repo.owner`, `repo.name`, `repo.language`

2. **Permissions:**
   - `contents: read` on target repos (to clone them)
   - If repos are private, the `GITHUB_TOKEN` or a PAT must have access

3. **Target Repos:**
   - No workflow files required in target repos
   - Must have standard build structure (pom.xml, build.gradle, requirements.txt, etc.)

### Tools Available

Central mode runs MORE tools than distributed mode:

**Java:** JaCoCo, Checkstyle, SpotBugs, PMD, OWASP DC, PITest, Semgrep, Trivy
**Python:** pytest, Ruff, Bandit, pip-audit, Black, isort, mypy, mutmut, Hypothesis, Semgrep, Trivy

> **Note:** All tools are controlled by config toggles (`enabled: true/false`). Most are enabled by default. Customize via `config/repos/<repo>.yaml`.

See [TOOLS.md](../reference/TOOLS.md) for the full availability matrix.

### When to Use

- **Always** (unless you have a specific reason to use distributed)
- When you want the simplest setup
- When you want all tools available
- When you want single-run aggregation
- When target repos shouldn't have CI workflow files

### Setup Instructions

1. Create a config file for each repo:
   ```yaml
   # config/repos/my-app.yaml
   repo:
     owner: jguida941
     name: my-app
     language: java
   ```

2. Run the workflow:
   - Manually: Actions → `Hub Run All` → Run workflow
   - On schedule: Runs nightly at 2 AM UTC
   - On config changes: Automatic

### Security Considerations

- **Token scope:** Only needs `contents:read`
- **Blast radius:** If hub is compromised, attacker can read (not write) target repos
- **Secrets:** Target repo secrets are NOT available (hub has its own secrets)
- **Network:** All tools run on hub's runner, not target repo's

---

## Distributed Mode (Optional)

### What It Does

The hub dispatches `workflow_dispatch` events to each target repo, triggering their CI workflows. The hub then polls for completion and downloads artifacts.

```
┌─────────────────┐     workflow_dispatch     ┌─────────────┐
│   hub-release   │ ────────────────────────► │   repo-a    │
│                 │                           │  java-ci.yml│
│  hub-orchestrator│                          └──────┬──────┘
│     .yml        │                                  │
│                 │ ◄────── poll status ─────────────┤
│                 │                                  │
│                 │ ◄────── download artifacts ──────┘
│                 │
│ Generate Report │
└─────────────────┘
```

### Prerequisites

1. **Hub Configuration:**
   - Same as central mode
   - `repo.default_branch` must be accurate

2. **Permissions:**
   - `contents: read` on target repos
   - `actions: write` on target repos (to dispatch workflows)
   - Token must be a PAT with repo scope, or fine-grained token with Actions permissions

3. **Target Repos:**
   - Must have a workflow file with `workflow_dispatch` trigger that accepts hub inputs
   - **Option A (Recommended):** Use official templates from `templates/java/java-ci-dispatch.yml` or `templates/python/python-ci-dispatch.yml`
   - **Option B:** Create your own workflow calling hub's reusable workflows
   - Workflow must produce `ci-report` artifact for aggregation
   - Configure workflow filename via `repo.dispatch_workflow` (defaults: `java-ci-dispatch.yml` / `python-ci-dispatch.yml`)

4. **Hub Workflow:**
   - `hub-orchestrator.yml` permissions block:
     ```yaml
     permissions:
       contents: read
       actions: write
     ```

### Tools Available

Distributed mode uses REUSABLE WORKFLOWS, which have fewer tools:

**Java:** JaCoCo, Checkstyle, SpotBugs, OWASP DC, PITest, CodeQL
**Python:** pytest, Ruff, Bandit, pip-audit, mypy, CodeQL

**NOT available in distributed:** PMD, Black, isort, mutmut, Hypothesis, Semgrep, Trivy

### When to Use

- When target repos MUST run CI in their own environment
- When repos use self-hosted runners
- When repos need access to their own secrets
- When repos require repo-local build context
- When organizational policy requires repo-owned CI

### Setup Instructions

1. **In each target repo**, add a dispatch workflow:

   **Option A (Recommended):** Copy the official template:
   ```bash
   # Java
   cp templates/java/java-ci-dispatch.yml /path/to/repo/.github/workflows/
   # Python
   cp templates/python/python-ci-dispatch.yml /path/to/repo/.github/workflows/
   ```

   **Option B:** Create your own workflow calling hub's reusable workflows:
   ```yaml
   # .github/workflows/java-ci-dispatch.yml
   name: Hub CI
   on:
     workflow_dispatch:
       inputs:
         # ... (see templates/java/java-ci-dispatch.yml for full inputs)

   jobs:
     ci:
       uses: jguida941/ci-cd-hub/.github/workflows/java-ci.yml@main
       with:
         java_version: ${{ inputs.java_version || '21' }}
         # ...
       secrets: inherit
   ```

2. **In the hub**, configure the repo:
   ```yaml
   # config/repos/my-app.yaml
   repo:
     owner: jguida941
     name: my-app
     language: java
     default_branch: main  # IMPORTANT: must be correct
     dispatch_enabled: true
     dispatch_workflow: java-ci-dispatch.yml  # or python-ci-dispatch.yml
   ```

3. **Set up permissions:**
   - Create a PAT with `repo` and `workflow` scopes
   - Add as `HUB_DISPATCH_TOKEN` secret in hub repo

4. **Run the orchestrator:**
   - Manually: Actions → `Hub Orchestrator` → Run workflow
   - On schedule or config changes

### Security Considerations

- **Token scope:** Requires `actions:write` - can trigger workflows in target repos
- **Blast radius:** If hub is compromised, attacker can trigger (not modify) target workflows
- **Secrets:** Target repo secrets ARE available to their workflows
- **Run IDs:** Captured best-effort; if not captured, aggregation may miss results
- **Timeouts:** If target workflow hangs, hub waits up to 30 minutes before timeout

### Known Limitations

1. **Run ID capture is best-effort** - If dispatch succeeds but run ID isn't captured, aggregation won't find artifacts
2. **No real-time status** - Hub polls periodically, not live updates
3. **Artifact download failures** - If target workflow doesn't produce expected artifact, aggregation shows incomplete data
4. **Permissions complexity** - Managing tokens across orgs is challenging

---

## Decision Flowchart

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

---

## Hybrid Approach

You can use both modes:

1. **Central for most repos** - simple, reliable, all tools
2. **Distributed for specific repos** - only those that truly need repo-local CI

Configure which mode each repo uses in `config/repos/<repo>.yaml`:

```yaml
repo:
  name: special-repo
  mode: distributed  # or "central" (default)
```

> **Note:** Hybrid mode configuration is planned but not yet implemented.

---

## Troubleshooting Modes

### Central Mode Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Clone fails | No access to repo | Check token permissions, repo exists |
| Build fails | Missing dependencies | Repo may need repo-local setup |
| Tools missing | N/A | Central has all tools |

### Distributed Mode Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Dispatch fails | Missing `actions:write` | Check token permissions |
| Dispatch fails | Workflow not found | Add dispatch workflow to target (use templates or check `dispatch_workflow` config) |
| Dispatch fails | Wrong branch | Set correct `default_branch` in config |
| Run ID not captured | Timing issue | Best-effort; check workflow ran |
| Aggregation incomplete | Artifact not found | Ensure workflow uploads `ci-report` |
| Timeout | Workflow too slow | Increase timeout or simplify workflow |

---

## Related Documentation

- [ADR-0001: Central vs Distributed](../adr/0001-central-vs-distributed.md) - Decision rationale
- [ADR-0013: Dispatch Workflow Templates](../adr/0013-dispatch-workflow-templates.md) - Template approach
- [DISPATCH_SETUP.md](DISPATCH_SETUP.md) - Full dispatch setup guide
- [WORKFLOWS.md](WORKFLOWS.md) - Workflow details
- [TEMPLATES.md](TEMPLATES.md) - Available templates
- [TOOLS.md](../reference/TOOLS.md) - Tool availability by mode
- [CONFIG_REFERENCE.md](../reference/CONFIG_REFERENCE.md) - Config options
