# CI/CD Hub Multi-Repository Architecture Analysis - Index

Purpose: navigation hub for deeper analysis docs. Mirrors the current readiness source of truth (`docs/status/honest-status.md`) and avoids duplicating roadmap/backlog details from `plan.md` and `docs/backlog.md`.

## Current Readiness (aligned with honest status)
- Single-repo on GitHub-hosted runners: ~85 % ready, pending empirical egress validation and a decision on cross-time determinism enforcement (gate vs informational).
- Multi-repo hub: ~70 % ready; proxy allowlists and per-repo timeouts exist, while per-repo secrets, fair scheduling, and cost/observability remain open.

## Primary Analysis Docs
- [Multi-repo architecture deep dive](multi-repo-analysis.md) — gaps/controls for hub-scale use.
- [Scalability notes](scalability.md) — queueing models, budgets, and scale limits.
- [Plan](../plan.md) — strategic roadmap and phased outcomes.
- [Start here](../start-here.md) — day-one actions and critical fixes.
- [Status (SoT)](../status/honest-status.md) — authoritative readiness snapshot.

## Open Analysis Questions
- Per-repo isolation hardening (secrets, runners, fair scheduling).
- Enforcement posture for cross-time determinism (informational vs gate).
- Egress enforcement validation method and acceptance criteria.
- Cost/observability data sources and dashboards for multi-repo rollouts.
