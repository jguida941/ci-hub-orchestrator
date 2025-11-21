# Backlog (Source of Truth)

All work items live in GitHub Issues; this file groups the themes and points to the canonical trackers. Create or link issues when you pick up an item and reference the labels noted below.

Add an Issue link for each row (fill in once created).

## Supply-chain enforcement
| Item | Issue | Notes |
| --- | --- | --- |
| Validate proxy-based egress denial in CI and record evidence under `artifacts/security/` | TBD – create GH Issue | security/egress |
| Promote Kyverno/OPA policies from audit-only to enforce in the target cluster; include rollout runbook | TBD – create GH Issue | policy/kyverno |
| Add Dependabot/Renovate and locked dependency policies (pip `--require-hashes`, no `npx`) for reproducibility | TBD – create GH Issue | supply-chain |

## Determinism & evidence
| Item | Issue | Notes |
| --- | --- | --- |
| Elevate cross-time determinism from advisory to gating and surface failures as required checks | TBD – create GH Issue | determinism |
| Sign and publish the evidence bundle as an OCI artifact; verify at admission | TBD – create GH Issue | evidence |

## Multi-repo isolation & fairness
| Item | Issue | Notes |
| --- | --- | --- |
| Implement per-repo secret brokerage (GitHub App + Vault) replacing shared `GITHUB_TOKEN` | TBD – create GH Issue | multi-repo/secrets |
| Add token-bucket rate limiting / fairness with Redis-backed queueing for matrix jobs | TBD – create GH Issue | multi-repo/scheduling |
| Enforce per-repo concurrency/memory budgets on self-hosted runners where feasible | TBD – create GH Issue | multi-repo/isolation |

## Observability & cost
| Item | Issue | Notes |
| --- | --- | --- |
| Wire pipeline telemetry to BigQuery (or chosen warehouse) and publish per-repo dashboards | TBD – create GH Issue | observability/cost |
| Emit queue-denial and gate outcomes as metrics/NDJSON for SLOs | TBD – create GH Issue | observability |

## Environment-specific wiring
| Item | Issue | Notes |
| --- | --- | --- |
| Release workflow: set real Dockerfile/build context; registry creds; SLSA provenance path; pinned installs; populate `fixtures/supply_chain/vex_exemptions.json` | TBD – create GH Issue | release/supply-chain |
| Registry publishing: confirm oras/cosign versions and publish VEX JSON via `tools/publish_referrers.sh` | TBD – create GH Issue | release/supply-chain |
| Rekor monitor: supply real Rekor log URL; integrate alerting destinations | TBD – create GH Issue | security/observability |
| Rego policies: tune issuer/subject regex and risk thresholds; add digest-allowlist/SBOM completeness rules | TBD – create GH Issue | policy |
| Schema registry: keep `schema/registry.json` ownership/compatibility metadata current | TBD – create GH Issue | schema |
| Runner isolation config: connect `config/runner-isolation.yaml` to runner orchestration + Vault roles; emit queue metrics | TBD – create GH Issue | multi-repo/isolation |
| Canary evidence: replace sample SQL and point `scripts/capture_canary_decision.py` at live metrics URIs | TBD – create GH Issue | release/observability |
| Determinism/DR scripts: extend parity checks and DR recall automation (`tools/determinism_check.sh`, `data-quality-and-dr/dr_recall.sh`) | TBD – create GH Issue | determinism/dr |
| dbt tests: align `models/tests/data_quality.yml` thresholds to your warehouse | TBD – create GH Issue | data/dbt |
| Docs: fill in real registry/bucket/IAM/SOC2/ISO mappings in `docs/SUPPLY_CHAIN.md`, `docs/SECURITY.md`, `docs/DR_RUNBOOK.md` | TBD – create GH Issue | docs |

## Documentation governance
| Item | Issue | Notes |
| --- | --- | --- |
| Keep README status and `docs/status/honest-status.md` in lockstep; update dates/readiness together | TBD – create GH Issue | docs |
| Regenerate `docs/index.md` and `STRUCTURE.md` in CI; fail builds on broken links/orphan docs | TBD – create GH Issue | docs/tooling |
| Consolidate or archive duplicate doc directories/backups; exclude generated artifacts summaries from SoT | TBD – create GH Issue | docs |
