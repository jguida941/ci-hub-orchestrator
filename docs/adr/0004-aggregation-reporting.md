# ADR-0004: Aggregation and Reporting

- Status: Accepted
- Date: 2025-12-14

## Context

The hub runs CI for multiple repositories. We need a consolidated view of results. Questions:
- What format should the aggregated report use?
- What metrics do we collect?
- How are per-repo results vs aggregates structured?
- Where does the report get published?

## Decision

**Report Format:** JSON file (`hub-report.json`) uploaded as artifact.

**Actual Schema (current implementation):**

```json
{
  "hub_run_id": "12345678",
  "timestamp": "2025-12-14T02:00:00Z",
  "triggered_by": "schedule",
  "total_repos": 3,
  "dispatched_repos": 3,
  "missing_dispatch_metadata": 0,
  "runs": [
    {
      "repo": "owner/repo-a",
      "language": "java",
      "branch": "main",
      "workflow": "hub-java-ci.yml",
      "run_id": "123456",
      "correlation_id": "12345678-1-repo-a",
      "status": "completed",
      "conclusion": "success",
      "coverage": 85,
      "mutation_score": 72
    },
    {
      "repo": "owner/repo-b",
      "language": "python",
      "branch": "main",
      "workflow": "hub-python-ci.yml",
      "run_id": "123457",
      "correlation_id": "12345678-1-repo-b",
      "status": "completed",
      "conclusion": "success",
      "coverage": 78,
      "mutation_score": null
    }
  ],
  "coverage_average": 81.5,
  "mutation_average": 72.0
}
```

**Root-Level Fields:**
- `hub_run_id` (string): GitHub run ID from `${{ github.run_id }}`
- `timestamp` (string): ISO 8601 UTC timestamp (`%Y-%m-%dT%H:%M:%SZ`)
- `triggered_by` (string): Event that triggered hub run (`${{ github.event_name }}`)
- `total_repos` (integer): Total count from config matrix
- `dispatched_repos` (integer): Number of dispatch metadata files received
- `missing_dispatch_metadata` (integer): `max(total_repos - dispatched_repos, 0)`
- `runs` (array): Per-repository run data (see below)
- `coverage_average` (float, optional): Average of numeric coverage values, rounded to 1 decimal
- `mutation_average` (float, optional): Average of numeric mutation_score values, rounded to 1 decimal

**Per-Run Entry Structure (`runs[]` array):**

Each entry contains exactly these fields:
- `repo` (string): Full repository name (e.g., "owner/repo")
- `language` (string): Language from dispatch metadata
- `branch` (string): Branch from dispatch metadata
- `workflow` (string): Workflow file from dispatch metadata
- `run_id` (string or empty): GitHub Actions run ID (empty string if missing)
- `correlation_id` (string): Hub correlation ID for deterministic matching (format: `{hub_run_id}-{run_attempt}-{config_basename}`)
- `status` (string): Run status - one of:
  - `"completed"` - run finished
  - `"in_progress"`, `"queued"`, `"waiting"`, `"pending"` - run still active
  - `"missing_run_id"` - no run_id in metadata
  - `"fetch_failed"` - API error retrieving run
  - `"timed_out"` - polling exceeded 30 minutes
  - `"unknown"` - default/fallback
- `conclusion` (string): Run conclusion - one of:
  - `"success"`, `"failure"`, `"cancelled"`, etc. (GitHub API values)
  - `"unknown"` - default/fallback
  - `"timed_out"` - if polling timed out
- `coverage` (number or null): Coverage percentage from `report.json` `results.coverage`
- `mutation_score` (number or null): Mutation score from `report.json` `results.mutation_score`

**Aggregated Metrics (optional fields):**
- `coverage_average`: Computed from runs where `coverage` is numeric (int or float), rounded to 1 decimal place
- `mutation_average`: Computed from runs where `mutation_score` is numeric (int or float), rounded to 1 decimal place
- Both fields only appear in output if at least one valid value exists
- **NOT USED FOR GATING** - aggregates are supplementary dashboard metrics only

**Why aggregates don't gate:**
- A single repo's failure shouldn't be masked by averaging
- Thresholds are per-repo (e.g., each repo must have 70% coverage)
- Aggregates can hide outliers (one 50% repo hidden by 90% neighbors)

## Alternatives Considered

1. **Object keyed by repo name:** Rejected. Array preserves order; easier iteration.
2. **Separate files per repo:** Rejected. Harder to consume; no single view.
3. **Aggregates in sub-object:** Rejected. Flat structure simpler for current needs.
4. **Database storage:** Rejected for MVP. Files + artifacts sufficient.

## Consequences

**Positive:**
- Single file with complete picture
- Per-repo detail preserved in array
- Easy to parse (JSON)
- Uploaded as artifact for downstream consumption
- GitHub step summary for human-readable view

**Negative:**
- File size grows with repo count
- No historical trending (single point in time)
- Aggregates might be misleading if misunderstood

**Current Limitations:**

1. **Vulnerability rollup NOT YET IMPLEMENTED:**
   - The schema does NOT include vulnerability counts
   - No `vulnerabilities`, `critical_vulns`, `high_vulns`, or similar fields exist in the output
   - Config defines `thresholds.max_critical_vulns` and `thresholds.max_high_vulns`, but aggregation does NOT collect these
   - OWASP Dependency-Check, pip-audit, and Trivy findings are NOT aggregated in `hub-report.json`
   - Vulnerability data exists in per-repo `report.json` artifacts but is NOT rolled up to hub level
   - This is a TODO for future work

2. **Polling implemented but may timeout:**
   - Aggregation polls each dispatched run for up to 30 minutes (lines 484, 517-532)
   - Polls every 10-60 seconds with exponential backoff
   - If run doesn't complete within 30 minutes, `status` set to `"timed_out"`
   - Successful completed runs have artifacts downloaded and metrics extracted (lines 540-564)

## Implementation References

- Aggregation logic: `hub-orchestrator.yml` lines 399-590
- Report generation: lines 543-561
- Artifact download: lines 432-452
- Step summary: lines 563-584

