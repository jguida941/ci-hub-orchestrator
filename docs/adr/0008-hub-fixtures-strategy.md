# ADR-0008: Hub Fixtures Strategy

**Status**: Accepted  
**Date:** 2026-01-02  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The hub needs deterministic, end-to-end validation of workflows, templates, and profiles. Relying on external, changing repos makes CI flaky and slows verification. We created a dedicated fixtures repository (`ci-cd-hub-fixtures`) with passing/failing Java and Python projects to exercise the hub pipelines on demand.

## Decision

1. Maintain a separate fixtures repository (`ci-cd-hub-fixtures`) containing:
   - `java-passing`, `java-failing`
   - `python-passing`, `python-failing`
2. Hub configs `config/repos/fixtures-*.yaml` point to those fixture projects; smoke tests default to them for predictable results.
3. Any new tool/template/profile should be validated against the fixtures via the hub smoke-test workflow before marking requirements as complete.
4. Fixtures remain minimal and stable; intentional failing cases stay failing to assert failure paths.

## Consequences

Positive:
- Predictable smoke results; fast feedback for changes to templates/workflows.
- Clear contract for P0 verification and regression checks.

Negative:
- Extra maintenance to keep fixtures aligned with schema changes.
- Need to update configs if fixture repo moves/renames.

## Alternatives Considered

- Continue using ad hoc public repos: rejected due to flakiness and lack of control.
- In-tree fixtures only: rejected to keep hub repo small and allow independent lifecycle; we keep a local copy for dev convenience but treat the GitHub repo as source of truth.
