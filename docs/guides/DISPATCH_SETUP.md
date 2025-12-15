# Dispatch Setup (Reusable Workflows)

Use this guide to enable cross-repo dispatch from the hub orchestrator.

## When to use dispatch
- You need the target repo's runners/secrets or prefer repo-owned CI.
- You want CI results to appear in the target repo's Actions tab.
- Target repos have custom build requirements beyond hub capabilities.
- If a repo is central-only (no workflows), set `repo.dispatch_enabled: false` in its hub config.

## Dispatch Workflow Templates (Recommended)

The hub provides official dispatch workflow templates. Copy these to target repos to enable orchestrator dispatch without modifying existing workflows.

### Available Templates

| Template | Location | For |
|----------|----------|-----|
| Java | `templates/java/java-ci-dispatch.yml` | Java/Maven/Gradle repos |
| Python | `templates/python/python-ci-dispatch.yml` | Python repos |

### Setup Steps

1. **Copy template to target repo:**
   ```bash
   # Java
   cp templates/java/java-ci-dispatch.yml /path/to/your-repo/.github/workflows/

   # Python
   cp templates/python/python-ci-dispatch.yml /path/to/your-repo/.github/workflows/
   ```

2. **Push to target repo:**
   ```bash
   cd /path/to/your-repo
   git add .github/workflows/*-ci-dispatch.yml
   git commit -m "Add hub dispatch workflow"
   git push
   ```

3. **Configure hub (optional - defaults work):**
   ```yaml
   # config/repos/your-repo.yaml
   repo:
     dispatch_enabled: true
     dispatch_workflow: java-ci-dispatch.yml  # or python-ci-dispatch.yml
   ```

The templates:
- Only trigger on `workflow_dispatch` (won't affect existing push/PR workflows)
- Accept all inputs the orchestrator sends
- Generate `ci-report` artifacts for hub aggregation

## Create a token (PAT)
1. Go to GitHub → Settings → Developer settings → Personal access tokens.
2. Classic PAT (simple): Generate new token (classic) → scopes: check `repo` and `workflow`.
   Fine-grained PAT (stricter):
   - Resource owner: your account
   - Repository access: include `ci-hub-orchestrator` and all target repos
   - Permissions: Actions Read/Write, Contents Read, Metadata Read
3. Generate and copy the token.

## Add the secret to the hub repo
- GitHub UI: `ci-hub-orchestrator` → Settings → Secrets and variables → Actions → New repository secret → Name `HUB_DISPATCH_TOKEN` → paste token.
- CLI: `gh secret set HUB_DISPATCH_TOKEN -R jguida941/ci-hub-orchestrator`

## Configure repos
- Hub config: set `repo.dispatch_enabled: false` for central-only repos (e.g., fixtures). Default is true.
- Set `repo.dispatch_workflow` to specify the workflow file to dispatch to (default: `java-ci-dispatch.yml` or `python-ci-dispatch.yml` based on language).
- Dispatchable repos must have a workflow with `workflow_dispatch` that accepts the hub inputs (use the official templates).
- Use `repo.run_group` (full/fixtures/smoke) and the `run_group` workflow input to limit which configs the hub runs.

## Artifact naming
- Orchestrator uploads artifacts with repo-specific names to avoid collisions; keep unique names if adding artifacts.

## Troubleshooting
- `Workflow does not have 'workflow_dispatch' trigger`: Target repo workflow missing `workflow_dispatch` trigger. Copy the official template to the target repo.
- `Unexpected inputs provided`: Target workflow doesn't accept the inputs the hub sends. Use the official templates which accept all hub inputs.
- `Resource not accessible by integration`: token lacks `actions:write`/`contents:read` on target repo.
- `404 workflow` / `Not Found`: target repo has no dispatchable workflow, or `dispatch_workflow` config points to wrong filename.
- Artifact `409 Conflict`: artifacts are now named with repo/run id; keep names unique if adding more.
- Multiple entries for same repo: hub-run-all and orchestrator include `config_basename` and `subdir` in job/artifact names to disambiguate when multiple configs point to the same repo.

## Related
- [ADR-0013: Dispatch Workflow Templates](../adr/0013-dispatch-workflow-templates.md)
- [TEMPLATES.md](TEMPLATES.md) - All available templates
