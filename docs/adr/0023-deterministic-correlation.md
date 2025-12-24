# ADR-0023: Deterministic Run Correlation

- Status: Accepted
- Date: 2025-12-24

## Context

The hub orchestrator dispatches workflows to target repositories and must correlate the triggered runs with their artifacts during aggregation. The original implementation used **time-window polling** to discover run IDs:

```javascript
// Old approach: match runs created within 10 seconds of dispatch
const recent = runs.data.workflow_runs.find((run) => {
  const created = new Date(run.created_at).getTime();
  return created >= startedAt - 10000;
});
```

**Problems with time-based matching:**

1. **Race conditions:** Multiple concurrent dispatches could match the wrong run
2. **Timing sensitivity:** GitHub API latency, queued workflows, or slow startup could cause mismatches
3. **No verification:** No way to confirm the matched run is actually the one we triggered
4. **Retry fragility:** Re-runs could match stale runs from previous attempts

## Decision

Implement **deterministic correlation** using a unique ID that flows through the entire dispatch → execution → aggregation chain.

### Correlation ID Format

```
{hub_run_id}-{run_attempt}-{config_basename}
```

Example: `12345678-1-smoke-test-python`

Components:
- `hub_run_id`: GitHub run ID of the hub orchestrator (unique per run)
- `run_attempt`: Run attempt number (handles retries)
- `config_basename`: Config file name without extension (unique per repo config)

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Hub Orchestrator                                                            │
│                                                                             │
│  1. Generate correlation ID                                                 │
│     correlationId = `${runId}-${runAttempt}-${configBasename}`             │
│                                                                             │
│  2. Pass as workflow input                                                  │
│     inputs.hub_correlation_id = correlationId                              │
│                                                                             │
│  3. Store in dispatch metadata artifact                                     │
│     { "correlation_id": correlationId, "run_id": capturedRunId }           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Target Workflow (hub-python-ci.yml / hub-java-ci.yml)                       │
│                                                                             │
│  1. Receive hub_correlation_id input                                        │
│                                                                             │
│  2. Embed in report.json artifact                                           │
│     { "hub_correlation_id": inputs.hub_correlation_id, "results": {...} }  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Aggregation Phase                                                           │
│                                                                             │
│  1. If run_id missing: search runs by correlation ID in artifacts          │
│     find_run_by_correlation_id(owner, repo, workflow, correlationId)       │
│                                                                             │
│  2. If run_id present: validate correlation ID matches                      │
│     if report.hub_correlation_id != expected: search for correct run       │
│                                                                             │
│  3. Extract metrics only from verified artifacts                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

Correlation logic is extracted into a testable module: `scripts/correlation.py`

```python
def find_run_by_correlation_id(owner, repo, workflow_id, correlation_id, token):
    """Search recent runs and match by hub_correlation_id in artifact."""
    runs = gh_get(f"/.../workflows/{workflow_id}/runs?per_page=20")
    for run in runs["workflow_runs"]:
        artifact = get_ci_report_artifact(run["id"])
        if artifact:
            report = download_and_parse(artifact)
            if report.get("hub_correlation_id") == correlation_id:
                return run["id"]
    return None

def validate_correlation_id(expected, actual):
    """Validate correlation ID matches, handling edge cases."""
    if not expected:
        return True  # No expected ID, skip validation
    return expected == actual

def generate_correlation_id(hub_run_id, run_attempt, config_basename):
    """Generate deterministic correlation ID."""
    return f"{hub_run_id}-{run_attempt}-{config_basename}"
```

### Schema Changes

Added `hub_correlation_id` to report schema (`schema/ci-report.v2.json`):

```json
{
  "properties": {
    "hub_correlation_id": {
      "type": "string",
      "description": "Correlation ID from hub orchestrator for reliable run matching"
    }
  }
}
```

## Alternatives Considered

1. **Tighter time window (2s instead of 10s):** Reduces but doesn't eliminate race conditions. Still fragile.

2. **Branch-based matching:** Match by branch name + status. Insufficient for same-branch concurrent runs.

3. **Commit SHA matching:** Use commit SHA as correlation. Doesn't work for workflow_dispatch (no commit).

4. **GitHub check suites:** Use check suite API for correlation. More complex, not needed for workflow_dispatch.

5. **Database/external storage:** Store correlation mapping externally. Adds infrastructure dependency.

## Consequences

**Positive:**

- No race conditions — correlation is deterministic
- Self-healing — finds correct run even if initial time-based capture failed
- Retry-safe — `run_attempt` in ID handles re-runs
- Auditable — correlation chain visible in artifacts
- Testable — logic extracted to `scripts/correlation.py` with unit tests

**Negative:**

- Additional API calls to search runs and download artifacts
- Target workflows must accept and propagate `hub_correlation_id` input
- Slightly more complex aggregation logic
- 20-run search window may miss very old runs (mitigated by typical CI timing)

**Trade-offs:**

- API cost vs reliability: More API calls but guaranteed correct matching
- Complexity vs correctness: More code but eliminates entire class of bugs

## Testing

Unit tests in `tests/test_correlation.py`:

- `TestGenerateCorrelationId`: Format and component handling
- `TestValidateCorrelationId`: Match/mismatch/edge cases
- `TestExtractCorrelationIdFromArtifact`: Artifact parsing
- `TestFindRunByCorrelationId`: Run search with mocked API

Integration testing via hub orchestrator runs against canary repos.

## Implementation References

| Component | Location | Description |
|-----------|----------|-------------|
| Correlation module | `scripts/correlation.py` | Extracted testable functions |
| Unit tests | `tests/test_correlation.py` | Correlation logic tests |
| Orchestrator dispatch | `hub-orchestrator.yml:398` | Generate and pass correlation ID |
| Orchestrator aggregation | `hub-orchestrator.yml:719-753` | `find_run_by_correlation_id()` |
| Python workflow | `python-ci.yml` | Accept `hub_correlation_id` input |
| Java workflow | `java-ci.yml` | Accept `hub_correlation_id` input |
| Report schema | `schema/ci-report.v2.json` | `hub_correlation_id` field |

## Related ADRs

- ADR-0003: Dispatch and Orchestration — updated with correlation flow
- ADR-0004: Aggregation and Reporting — updated with correlation_id field
