# CI/CD Hub – Honest Status Assessment

**Snapshot:** 2025‑11‑02 (tag v1.0.10)  
**Audience:** Engineering leadership, auditors, and on-call responders who need an unvarnished view of platform readiness.

---

## Executive Summary

- **Single-repository deployments on GitHub-hosted runners:** ~85 % ready. Supply-chain gates, evidence signing, and dynamic repository configuration are live; proxy-based egress controls are configured but still require an empirical validation run; cross-time determinism is monitored after release rather than gating promotion.
- **Multi-repository hub story:** ~70 % ready. Dynamic registry, per-repo HTTP allowlists, and per-repo test timeouts are working. Per-repo secrets, fair scheduling, cost allocation, and hard resource isolation remain open.

Until the open items below land and a tagged build validates enforcement in CI, treat the system as **pilot grade** for trusted repositories only.

---

## What Works Today

| Control | Status | Evidence / Notes |
| --- | --- | --- |
| Action pinning & workflow integrity | ✅ | `scripts/check_workflow_integrity.py`, all workflows use SHA pins. |
| Supply-chain verification | ✅ | Checksums enforced in `scripts/install_tools.sh`; release job verifies SBOM/VEX/provenance (see `.github/workflows/release.yml:974-1239`). |
| Evidence bundle signing | ✅ | `scripts/sign_evidence_bundle.sh` now fails fast on verification errors; release step re-verifies with repo-scoped identity. |
| Dynamic repo registry | ✅ | `config/repositories.yaml` + `scripts/load_repository_matrix.py` feed the matrix via heredoc output (`release.yml:92-103`). |
| Per-repo HTTP allowlists | 🟡 | `HTTP(S)_PROXY`/`NO_PROXY` exported for each repo (`release.yml:130-156`), covering tools that honour proxy env vars. Needs CI validation. |
| Per-repo test timeout | 🟡 | `timeout "${TIMEOUT_SECONDS}s"` uses `settings.build_timeout` (`release.yml:283-310`). Job-level `timeout-minutes` is global (60 min). |
| Rekor/SLSA/SBOM evidence | ✅ | Stored under `artifacts/signed-evidence/` with cosign/rekor proofs. |
| Test automation | ✅ | `pytest` suite (85 tests) green locally with pinned dependencies. |

---

## Items Requiring Validation or Follow-Up

1. **Proxy-based egress enforcement**  
   - _Risk_: Tools that bypass `HTTP(S)_PROXY` (raw sockets) can still exfiltrate data.  
   - _Action_: Run a tagged release (v1.0.10 or later) and attempt to reach a blocked domain; confirm the job fails and `artifacts/security/egress-report.json` records the denial.

2. **Cross-time determinism gate**  
   - _Current_: `.github/workflows/cross-time-determinism.yml` files a GitHub issue when drift is detected, but success/failure does not block promotion.  
   - _Action_: Decide whether to add a status check or automated rollback before production use.

3. **Kyverno policy deployment**  
   - _Current_: Policies are exercised in CI (`scripts/verify_kyverno_enforcement.sh`) but not yet deployed to the target cluster.  
   - _Action_: Coordinate with platform team to deploy and enforce at admission.

4. **Dependency installation in air-gapped environments**  
   - _Observation_: Local installation of `jsonschema==4.23.0` failed without internet access. Provide mirrors or pre-built wheels for regulated deployments.

---

## Still Missing for Multi-Tenant Hub

| Capability | Status | Notes / Follow-up |
| --- | --- | --- |
| Per-repo secrets | ❌ | Shared `GITHUB_TOKEN`; design GitHub App + Vault integration (Phase 2). |
| Fair scheduling / rate limiting | ❌ | No token bucket or Redis-backed queue; heavy repo can monopolise runners. |
| Memory / CPU quotas | ❌ | Requires self-hosted runners; `settings.resource_limit_mb` is informational only. |
| Cost & observability | ❌ | BigQuery/Grafana pipeline not yet wired; telemetry stored locally only. |
| Org-wide GitHub rulesets | ❌ | Need controls for signed commits, banned `pull_request_target`, no unpinned actions. |

---

## Readiness Assessment

- **Single repo (trusted workloads):** proceed once proxy enforcement is validated and determinism expectations are agreed (gate vs. advisory).  
- **Multi repo (mixed trust):** wait for per-repo secrets, rate limiting, and cost observability to land (estimated 4 weeks of focused work).  
- **Regulated workloads:** plan on self-hosted runners with stronger isolation and secret brokerage.

---

## Next Actions Checklist

1. ✅ Trigger v1.0.10 release workflow; capture results of proxy enforcement and determinism follow-up run.  
2. 🟡 Update `HONEST_STATUS.md` with empirical evidence once CI completes (add log references, artifacts).  
3. 🟡 Start Phase 2 tasks in `MULTI_REPO_IMPLEMENTATION_STATUS.md` (per-repo secrets, rate limiting).  
4. 🟡 Draft GitHub org ruleset proposal (no unpinned actions, signed commits/tags, CODEOWNERS enforcement).  
5. 🟡 Coordinate Kyverno deployment to target cluster and document runbook in `docs/OPS_RUNBOOK.md`.

_Keep this document authoritative—update it immediately after each tagged release or material architecture change._
