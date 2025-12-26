# ADR-0011: Dispatchable Workflow Requirement

**Status**: Accepted  
**Date:** 2026-01-15  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

Dispatch mode only works if the target repo has a `workflow_dispatch` entry point. Central-only repos (e.g., fixtures) should not be dispatched. Previous runs failed with `Resource not accessible by integration` when dispatch was attempted without permissions or a workflow present.

## Decision

- Orchestrator requires target repos to host a dispatchable workflow (e.g., calling reusable `java-ci.yml`/`python-ci.yml`).
- Hub configs can set `repo.dispatch_enabled: false` to skip dispatch for central-only repos.
- A dispatch token (`HUB_DISPATCH_TOKEN`) with `repo`+`workflow` scopes is required for cross-repo dispatch; otherwise, run in central mode.
- Artifact names include the repo/run id to avoid collisions in dispatch runs. Matrix entries carry `config_basename` to disambiguate configs pointing at the same repo.

## Consequences

Positive:
- Clear contract for dispatch: workflow must exist; token must allow dispatch.
- Central-only repos avoid noisy failures.
- Reduced artifact name conflicts.

Negative:
- More configuration for users (dispatch flag + workflow setup).
- Extra secret management (PAT).

## Alternatives Considered

- Attempt dispatch for all repos: rejected due to failures on repos without workflows or permissions.
- Forcing users to split fixtures into separate repos: rejected; central mode covers them cleanly.
