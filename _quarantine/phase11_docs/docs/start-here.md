# CI/CD Hub - Prioritized Action Plan

_Last updated: 2025-11-02 (v1.0.10 snapshot)_

## Current Status Summary
- **Single-repository readiness**: ~85 % — supply-chain controls enforced, proxy-based egress allowlists configured, cross-time determinism monitored post-release. Pending: CI validation of proxy enforcement and gating on determinism failures.
- **Multi-repository hub**: ~70 % — dynamic registry + per-repo timeouts in place; per-repo secrets, rate limiting, and cost tracking scheduled for Phase 2.
- **Supply-chain security**: ✔️ Mandatory checksums, signed evidence bundle, Rekor/SLSA proofs captured.
- **Known gaps**: Proxy enforcement unvalidated, no per-repo credentials, cross-time determinism remains advisory, Kyverno policies not deployed to target cluster.

## Immediate Actions (Week 0–1)

1. **Validate proxy-based egress controls in CI**
   - Trigger the release workflow (tag build) and confirm an intentional call to a blocked domain fails.
   - Capture evidence under `artifacts/security/egress-report.json`.

2. **Promote cross-time determinism to a gate**
   - Consume the result of `.github/workflows/cross-time-determinism.yml` in branch protection or block the next release until the previous delayed rebuild passes.

3. **Document actual enforcement posture**
   - Update `HONEST_STATUS.md` after the first successful CI run to include observed egress behaviour and determinism outcome.

4. **Plan per-repo secret delivery**
   - Select GitHub App or Vault approach (see Phase 2 below) and capture design decisions in GitHub Issues (multi-repo/secret labels) + `docs/backlog.md`.

## Near-Term Roadmap

### Phase 2 (Weeks 2–3): Isolation & Secrets
- Implement GitHub App + Vault secret brokerage for per-repo scopes.
- Token bucket rate limiting (Redis-backed) to prevent starvation.
- Extend telemetry to record queue denials and enforcement results.

### Phase 3 (Week 4): Observability & Cost
- Wire BigQuery ingestion for job telemetry.
- Publish per-repo Grafana dashboards with cost allocation.
- Include dashboard references in the evidence bundle.

### Phase 4 (Weeks 5–6): Hardening
- Deploy Kyverno policies to target cluster in enforce mode.
- Integrate cross-time determinism gate into promotion approval.
- Explore self-hosted runners for memory/cgroup enforcement if regulators require deeper isolation.

## Week 2-3: Multi-Repo Foundation

### Priority 1: Isolation & Secrets (40 hours)
- Implement per-repo OIDC federation with Vault/GitHub App
- Create repo-scoped secret paths
- Add basic container isolation (self-hosted runner profile)

### Priority 2: Fair Scheduling (60 hours)
- Implement token-bucket rate limiting
- Add per-repo concurrency budgets (external queue)
- Deploy Redis queue management

### Priority 3: Complete Observability (60 hours)
- Wire BigQuery pipeline (vars currently empty)
- Deploy Grafana dashboards per repo
- Add cost allocation tracking

## Week 4-10: Production Hardening

See `plan.md:1778-1856` for complete 10-week roadmap including:
- Multi-tenant isolation (Firecracker optional)
- Service mesh patterns (future enhancement)
- Deployment orchestration
- Hierarchical configuration

## Documentation Structure

```
plan.md                            - Strategic architecture & roadmap
├── GitHub Issues (security label) - Security audit tracker
├── docs/analysis/multi-repo-analysis.md - Multi-tenancy gaps (6 categories)
├── docs/analysis/index.md         - Quick reference tables
└── docs/start-here.md             - This file (action plan)
```

## Decision Points

### Must Have for v1.0 (In Current Plan)
✅ Already excellent:
- SLSA, Cosign, SBOM/VEX, Rekor
- Cache integrity with signatures
- Telemetry schema (100+ fields)

🔴 Critical gaps:
- Security vulnerabilities (13 found)
- Per-repo secrets/isolation
- Fair scheduling/rate limiting
- Complete BigQuery/dashboard wiring

### Nice to Have (Future Enhancements)
These are NOT in current plan.md:
- API gateway / service mesh
- GitOps (ArgoCD/Flux)
- Hierarchical config service
- Dynamic repo registration

## Success Metrics

**Week 1 Success**:
- All CRITICAL and HIGH vulnerabilities fixed (7 issues total)
- Evidence bundle signature verified in CI
- Egress technically enforced

**Month 1 Success**:
- Per-repo secrets working
- Fair scheduling implemented
- Dashboards deployed

**v1.0 Success** (10 weeks):
- All items in plan.md v1.0 checklist complete
- Support 10+ repos without resource starvation
- Full observability and cost tracking
- Production-grade security posture

## Next Steps

1. **Fix the 5 CRITICAL security issues** (Day 1-2)
2. **Review this plan with stakeholders**
3. **Decide on optional enhancements** (API gateway, GitOps, etc.)
4. **Assign team members to each phase**
5. **Set up weekly progress reviews**

## Contact Points

- Security Issues: See GitHub Issues (`https://github.com/jguida941/ci-cd-hub/issues`) with `security` label
- Architecture Questions: See `plan.md` for design rationale
- Multi-Repo Gaps: See `docs/analysis/multi-repo-analysis.md` for analysis
- Quick Reference: See `docs/analysis/index.md` for navigation
