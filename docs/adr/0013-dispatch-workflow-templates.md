# ADR-0013: Dispatch Workflow Templates

- Status: Accepted
- Date: 2025-12-15

## Context

ADR-0011 established that orchestrator mode requires target repos to have dispatchable workflows with `workflow_dispatch` triggers. However, this created friction:

1. Users had to manually create workflow files in each target repo
2. The orchestrator hardcoded workflow names (`java-ci.yml`, `python-ci.yml`)
3. Adding `workflow_dispatch` to existing workflows risked breaking them
4. No standardized templates existed for dispatch-enabled workflows

The goal of the hub is to be a central CI/CD controller - requiring extensive per-repo setup contradicts this.

## Decision

### 1. Provide Official Dispatch Workflow Templates

Create standardized templates that users copy to target repos:

```
templates/
  java/
    java-ci-dispatch.yml    # Java dispatch workflow template
  python/
    python-ci-dispatch.yml  # Python dispatch workflow template
```

These templates:
- Only trigger on `workflow_dispatch` (won't interfere with existing push/PR workflows)
- Accept all inputs the orchestrator sends
- Run comprehensive CI checks matching hub-run-all behavior
- Generate `ci-report` artifacts for aggregation

### 2. Make Workflow Name Configurable

Add `dispatch_workflow` to the repo config schema:

```yaml
repo:
  owner: jguida941
  name: my-repo
  dispatch_enabled: true
  dispatch_workflow: java-ci-dispatch.yml  # Configurable per repo
```

The orchestrator reads this field instead of hardcoding workflow names. Default values:
- Java repos: `java-ci-dispatch.yml`
- Python repos: `python-ci-dispatch.yml`

### 3. Separate Dispatch Workflows from Existing Workflows

The dispatch workflow is a NEW file, not a modification to existing workflows:

```
target-repo/
  .github/workflows/
    ci.yml                  # Existing workflow (untouched)
    java-ci-dispatch.yml    # NEW - only for hub dispatch
```

This ensures:
- Zero risk to existing CI/CD
- Clear separation of concerns
- Users can customize dispatch behavior independently

## Consequences

### Positive

- **Safe onboarding**: Adding dispatch doesn't affect existing workflows
- **Flexible**: Per-repo workflow names allow customization
- **Standardized**: Templates ensure consistent behavior across repos
- **Clear contract**: Templates document exactly what inputs are expected
- **Backward compatible**: Repos can still use `java-ci.yml` if they prefer

### Negative

- **One-time setup**: Users must still copy the template file to each target repo
- **Two workflows**: Repos using dispatch have a separate file from their main CI
- **Maintenance**: Templates must be kept in sync with orchestrator inputs

## Alternatives Considered

1. **Modify existing workflows in target repos**: Rejected - too risky, could break existing CI
2. **Auto-inject workflows via GitHub API**: Rejected - requires elevated permissions, too invasive
3. **Use repository_dispatch instead**: Rejected - requires custom event handling, less standard
4. **Central-only mode exclusively**: Rejected - some repos legitimately need distributed mode

## Implementation

### Files Created/Modified

| File | Change |
|------|--------|
| `templates/java/java-ci-dispatch.yml` | NEW - Java dispatch template |
| `templates/python/python-ci-dispatch.yml` | NEW - Python dispatch template |
| `schema/ci-hub-config.schema.json` | Added `dispatch_workflow` field |
| `.github/workflows/hub-orchestrator.yml` | Reads `dispatch_workflow` from matrix |
| `config/repos/*.yaml` | Added `dispatch_workflow` to dispatchable repos |

### User Workflow

1. Copy template to target repo:
   ```bash
   cp templates/java/java-ci-dispatch.yml /path/to/repo/.github/workflows/
   ```

2. Push to target repo

3. Configure hub (optional - defaults work):
   ```yaml
   repo:
     dispatch_workflow: java-ci-dispatch.yml
   ```

4. Run orchestrator - it will dispatch to the new workflow

## Related ADRs

- ADR-0001: Central vs. Distributed Execution
- ADR-0003: Dispatch and Orchestration
- ADR-0011: Dispatchable Workflow Requirement
