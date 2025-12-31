# ADR-0013: Dispatch Workflow Templates

> **Status: Superseded by [ADR-0014: Reusable Workflow Migration](./0014-reusable-workflow-migration.md)**
>
> This ADR established dispatch templates that users copy to repos. ADR-0014 replaces this with reusable workflows + minimal callers to eliminate template drift and ensure consistent reporting.
>
> **Note:** Legacy dispatch templates are archived under `templates/legacy/`.

**Status**: Superseded  
**Date:** 2025-12-15  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

- Superseded by: ADR-0014 (2025-12-17)

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

## Comprehensive Reporting (Updated 2025-12-15)

### report.json Schema

The dispatch templates generate a comprehensive `report.json` artifact that the orchestrator aggregates. The schema captures ALL tool results:

```json
{
  "repo": "owner/repo-name",
  "branch": "main",
  "run_id": "12345678",
  "language": "java|python",
  "timestamp": "2025-12-15T14:00:00Z",
  "results": {
    // Common quality metrics
    "coverage": <number|null>,
    "mutation_score": <number|null>,

    // Java-specific tools
    "checkstyle_violations": <number|null>,
    "spotbugs_bugs": <number|null>,
    "pmd_violations": <number|null>,
    "owasp_critical": <number|null>,
    "owasp_high": <number|null>,
    "owasp_medium": <number|null>,

    // Python-specific tools
    "tests_passed": <number|null>,
    "tests_failed": <number|null>,
    "ruff_errors": <number|null>,
    "black_issues": <number|null>,
    "isort_issues": <number|null>,
    "mypy_errors": <number|null>,
    "bandit_high": <number|null>,
    "bandit_medium": <number|null>,
    "pip_audit_vulns": <number|null>,

    // Cross-language security tools
    "semgrep_findings": <number|null>,
    "trivy_critical": <number|null>,
    "trivy_high": <number|null>
  },
  "tools_ran": {
    // Booleans indicating which tools executed
    "jacoco": true,
    "checkstyle": false,
    // ... etc
  }
}
```

### Key Design Decisions

1. **`null` vs `0`**: Fields are `null` if the tool didn't run, `0` if it ran and found nothing. This allows the summary to show `-` for skipped tools.

2. **`tools_ran` section**: Explicitly tracks which tools executed, independent of results.

3. **Language-specific sections**: Java and Python repos have different tool sets, reported in separate tables in the hub summary.

4. **Aggregation**: The orchestrator sums all vulnerability counts across repos and tools to provide total security posture.

### Hub Summary Output

The orchestrator generates separate tables for Java and Python repos:

**Java:**
| Config | Status | Cov | Mut | CS | SB | PMD | OWASP | Semgrep | Trivy |

**Python:**
| Config | Status | Cov | Mut | Tests | Ruff | Black | isort | mypy | Bandit | pip-audit | Semgrep | Trivy |

Tools that didn't run show `-` in the table.

## Related ADRs

- ADR-0001: Central vs. Distributed Execution
- ADR-0003: Dispatch and Orchestration
- ADR-0011: Dispatchable Workflow Requirement
