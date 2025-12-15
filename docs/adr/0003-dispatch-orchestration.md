# ADR-0003: Dispatch and Orchestration

- Status: Accepted
- Date: 2025-12-14

## Context

In distributed mode, the hub triggers CI workflows in target repositories and collects results. Questions:
- How do we trigger workflows in other repos?
- How do we know when they complete?
- How do we collect their artifacts?
- What permissions are required?

## Decision

### Dispatch Mechanism

**Implementation:** `actions/github-script@v7` with `github.rest.actions.createWorkflowDispatch()`

The orchestrator uses GitHub's REST API via `github-script` to trigger workflows (lines 249-351):

```javascript
// Line 302-308
await github.rest.actions.createWorkflowDispatch({
  owner,
  repo,
  workflow_id: workflowId,  // 'java-ci.yml' or 'python-ci.yml' (line 297)
  ref: branch,
  inputs,
});
```

**Error Handling:** Dispatch failures are caught and set job status to failed (lines 309-312):
```javascript
catch (err) {
  core.setFailed(`Dispatch failed for ${owner}/${repo}: ${err.message}`);
  throw err;
}
```

### Run ID Capture

After dispatch succeeds, the orchestrator attempts to capture the triggered run's ID using exponential backoff polling (lines 314-346):

**Parameters:**
- `MAX_POLL_MS`: 30 minutes (1,800,000 ms) - line 267
- Initial delay: 5000 ms (5 seconds) - line 315
- Backoff multiplier: 2x per iteration - line 340
- Max delay: 30000 ms (30 seconds) - line 340
- Time window: Looks for runs created ≥ `startedAt - 10000` (10 second grace period) - line 331

**Algorithm (lines 318-341):**
```javascript
let runId = '';
let pollDelay = 5000;
const deadline = startedAt + MAX_POLL_MS;

while (Date.now() < deadline) {
  await new Promise((resolve) => setTimeout(resolve, pollDelay));
  const runs = await github.rest.actions.listWorkflowRuns({
    owner,
    repo,
    workflow_id: workflowId,
    event: 'workflow_dispatch',
    branch,
    per_page: 5,
  });

  const recent = runs.data.workflow_runs.find((run) => {
    const created = new Date(run.created_at).getTime();
    return created >= startedAt - 10000;
  });

  if (recent) {
    runId = String(recent.id);
    core.info(`Captured run id ${runId} for ${repo}`);
    break;
  }

  pollDelay = Math.min(pollDelay * 2, 30000); // backoff up to 30s
}
```

**Failure Behavior:** If run ID cannot be captured within 30 minutes, the job fails (lines 343-346):
```javascript
if (!runId) {
  core.setFailed(`Dispatched ${workflowId} for ${repo}, but could not determine run id.`);
  return;
}
```

Outputs are still set (lines 348-350), and metadata is saved with `job.status` reflecting the failure (lines 363-384).

### Completion Polling

**DOES NOT EXIST in trigger-builds job.** The orchestrator dispatches workflows and captures run IDs, but does NOT wait for them to complete. The `trigger-builds` job ends after capturing the run ID.

**However:** The `aggregate-reports` job DOES poll to completion (lines 513-538):

**Parameters:**
- `poll_timeout_sec`: 1800 seconds (30 minutes) - line 484
- Initial delay: 10 seconds - line 516
- Backoff multiplier: 1.5x per iteration - line 533
- Max delay: 60 seconds - line 533
- Pending statuses: `{"queued", "in_progress", "waiting", "pending"}` - line 483

**Algorithm (lines 517-538):**
```python
url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
start_poll = time.time()
delay = 10
while True:
    run = gh_get(url)
    status = run.get("status", "unknown")
    conclusion = run.get("conclusion", "unknown")
    run_status["status"] = status
    run_status["conclusion"] = conclusion

    if status not in pending_statuses:
        break

    if time.time() - start_poll > poll_timeout_sec:
        run_status["status"] = "timed_out"
        run_status["conclusion"] = "timed_out"
        break

    time.sleep(delay)
    delay = min(delay * 1.5, 60)
```

If a run times out or fails to fetch, it's recorded and the job ultimately fails (lines 622-626).

### Artifact Collection

After run completion, if `status == "completed"` and `conclusion == "success"`, the aggregator downloads artifacts (lines 540-563):

1. Lists artifacts via API: `GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts`
2. Prefers artifact named `"ci-report"`, otherwise first artifact (lines 546-548)
3. Downloads via `archive_download_url` with bearer token authentication (lines 449-469)
4. Extracts ZIP and searches for `report.json` (lines 553-554)
5. Parses coverage and mutation score from `results` object (lines 558-559)

**Retry Logic:** The `gh_get()` function has built-in retry with exponential backoff (lines 427-447):
- Max retries: 3
- Backoff multiplier: 2.0
- Sleep time: `backoff * attempt` (2s, 4s, 6s)

### Permissions

**Hub orchestrator workflow (lines 38-40):**
```yaml
permissions:
  contents: read
  actions: write
```

**Authentication:**
- Uses `${{ secrets.GITHUB_TOKEN }}` by default (line 253)
- For cross-repo dispatch to private repos, requires PAT with `repo` scope
- `actions: write` permission enables `createWorkflowDispatch()` and `listWorkflowRuns()`

**Requirements for Target Repos:**
1. Workflow file must exist (`.github/workflows/java-ci.yml` or `python-ci.yml`)
2. Workflow must have `workflow_dispatch` trigger with expected inputs
3. Token must have write access to target repo's Actions

### Failure Behavior

**Dispatch failures (lines 309-312):** Set job to failed immediately, throw exception

**Run ID capture failures (lines 343-346):** Set job to failed, return early (no run ID output)

**Aggregation failures (lines 622-626):** Job fails if:
- Any run has `status` in `{"missing_run_id", "fetch_failed", "timed_out"}`
- Any completed run has `conclusion != "success"`
- Any run is not `status == "completed"`
- Dispatch metadata files are missing (`missing > 0`)

**Matrix strategy (line 148):** `fail-fast: false` - all repos are triggered even if one fails

## Alternatives Considered

1. **`gh workflow run` CLI:** Rejected. GitHub Script provides better error handling, typed API, and programmatic access to response data.
2. **Repository dispatch events:** Rejected. Less standardized; harder to pass typed inputs; requires custom event handling.
3. **Webhook-based triggers:** Rejected. Requires webhook infrastructure; overkill for this use case.
4. **Push-based reporting:** Target repos push to hub. Rejected - adds complexity to target repos; requires hub API.

## Consequences

**Positive:**
- Standard GitHub mechanism (REST API via `workflow_dispatch`)
- Typed inputs passed to target workflows (lines 266-295)
- Exponential backoff prevents API rate limiting (dispatch run ID capture: line 340; aggregation polling: line 533)
- No changes required to target repos beyond having the workflow
- Parallel dispatch via matrix strategy (lines 147-149)
- Aggregation polls to completion with configurable timeout

**Negative:**
- Run ID capture may fail under heavy GitHub API load or timing issues
- Two-phase polling: trigger-builds captures run ID (no completion wait), aggregate-reports polls to completion
- Requires PAT for private cross-repo access (not included in workflow - must be configured)
- Target workflows must define `workflow_dispatch` trigger with exact input names
- 30-minute timeout may be insufficient for slow builds (both run ID capture and completion polling)
- Aggregation failure logic is strict: any non-success conclusion fails the entire hub run (lines 572-576, 622-626)

## Implementation References

| Component | Lines | Description |
|-----------|-------|-------------|
| Dispatch step | 249-351 | Full `github-script` action invocation |
| Dispatch API call | 302-308 | `createWorkflowDispatch()` invocation |
| Dispatch error handling | 309-312 | Catch block with `core.setFailed()` |
| Run ID capture loop | 318-341 | Polling with exponential backoff |
| Run ID failure handling | 343-346 | Job failure if run ID not captured |
| Completion polling (aggregation) | 517-538 | Python polling loop in aggregate job |
| Artifact download | 449-469 | `download_artifact()` function |
| Artifact parsing | 540-563 | Extract coverage/mutation from report.json |
| Aggregation failure logic | 622-626 | Exit 1 if any run failed or data missing |
| Permissions | 38-40 | Workflow-level permissions |
| Max poll timeout (run ID) | 267 | `MAX_POLL_MS = 30 * 60 * 1000` |
| Max poll timeout (completion) | 484 | `poll_timeout_sec = 30 * 60` |
| Retry logic | 427-447 | `gh_get()` with backoff |

## Future Work

- **Configurable timeouts:** Allow per-repo timeout settings for both run ID capture and completion polling
- **Retry logic for dispatch:** Retry transient dispatch failures (network errors, rate limits) - currently any failure is terminal
- **Graceful degradation:** Option to continue aggregation even if some runs fail (currently strict: any failure = hub failure)
- **Unified polling:** Consider consolidating run ID capture and completion polling into single phase
- **PAT documentation:** Document PAT setup for cross-repo private access (currently undocumented)

