# ADR-0001: Central vs. Distributed Execution

- Status: Accepted
- Date: 2025-12-14

## Context

The hub supports two modes:
- Central: Hub clones target repos and runs Java/Python workflows inside the hub run. Default, keeps repos clean.
- Distributed: Hub dispatches workflows inside target repos (`hub-orchestrator.yml`). Requires repo-side workflow_dispatch and elevated permissions.

Considerations:
- Reliability: Central avoids cross-repo dispatch failures and permissions drift.
- Permissions: Distributed needs `actions:write` on targets and per-repo workflow_dispatch enabled.
- Results: Central has results in one run; distributed requires correlation/artifact download.
- Security: Distributed increases token scope; central limits blast radius.

## Decision

- Central execution remains the default and recommended mode.
- Distributed execution is opt-in, guarded, and only used when repos insist on self-hosted workflows or need repo-local build context.
- Orchestrator must honor per-repo `default_branch`, pass computed inputs, and fail fast on dispatch/aggregation issues.

## Alternatives Considered
- Make distributed the default: rejected due to permissions/fragility.
- Maintain only central mode: rejected; some repos require in-repo workflows/runners.
- Hybrid with reusable workflows only: accepted as primary path for distributed; direct dispatch kept for compatibility.

## Consequences

- Docs and templates emphasize central mode first.
- Orchestrator is maintained but marked optional; requires permissions and validation.
- Aggregation must handle missing run IDs/artifacts gracefully and fail hub run on downstream failure.
- Future dashboards/fixtures should focus on central mode; distributed coverage remains best-effort. 
