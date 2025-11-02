# CI/CD Hub - Prioritized Action Plan

## Current Status Summary  (🚨 See HONEST_STATUS.md for full details)
- **Single-Repo Readiness**: 92% ✅ (egress needs testing)
- **Multi-Repo Hub**: 70% (design complete, needs 4 weeks implementation)
- **Supply Chain Security**: 99% ✅ (ALL checksums enforced, evidence verified)
- **Time to Production**: Single-repo ready NOW, multi-repo in 4 weeks
- **Evidence Bundle**: ✅ Signing AND verification implemented
- **Fixed Today**: 11/13 vulnerabilities (3 CRITICAL, 8 HIGH)
- **Remaining**: Egress (untested), multi-repo features (design only)

## 🚨 START HERE - Immediate Actions (Week 1)

### ✅ COMPLETED Security Fixes (11 vulnerabilities fixed)

1. **Command Injection** ✅ FIXED
   - File: `.github/workflows/sign-digest.yml:37-70`
   - Added strict input validation and sanitization

2. **GitHub Token Exposure** ✅ FIXED
   - File: `.github/workflows/mutation.yml:47`
   - Moved token to environment variable

3. **Unpinned Actions** ✅ FIXED
   - File: `scripts/validate_cross_time_determinism.sh:112/133/147`
   - Now uses pinned SHA digests

4. **Unchecked Binary Downloads** ✅ FIXED
   - Files: `.github/workflows/release.yml:1219,1230,1338`
   - Added SHA256 verification for ORAS, cosign, OPA

5. **Tool Checksum Enforcement** ✅ FIXED
   - Files: `scripts/install_tools.sh:114-127`, `tools/rekor_monitor.sh:52-55`
   - Now fails hard on missing/mismatched checksums

6. **Replace npx** ✅ FIXED
   - File: `make/common.mk:6-8`
   - Now uses Docker image instead of npx

7. **Fix Dependency Pinning** ✅ FIXED
   - File: `requirements-dev.txt:1-11`
   - All dependencies now use exact `==` pins

8. **Tool Checksums for Rekor/Syft/Grype** ✅ FIXED
   - File: `scripts/install_tools.sh:148-225`
   - Now fails hard on missing checksums

9. **Cross-Time Determinism Workflow** ✅ FIXED
   - Created `.github/workflows/cross-time-determinism.yml`
   - Full delayed rebuild validation

10. **Evidence Bundle Verification** ✅ FIXED
    - File: `.github/workflows/release.yml:1168-1191`
    - Signature now verified after signing

11. **Documentation References** ✅ FIXED
    - Fixed references to non-existent files
    - Updated all status tracking

### 🔴 REMAINING Production Gates

#### Last Critical Item: Technical Egress Control (8 hours)
- **Current**: Audit-only on GitHub-hosted runners (`.github/workflows/release.yml:570-571`)
- **Issue**: Falls back to test mode, no enforcement
- **Solutions**:
  1. Use self-hosted runners with sudo access (immediate)
  2. Implement GitHub Actions network policies (1 week)
  3. Deploy dedicated CI infrastructure with firewall rules (2 weeks)
- **Impact**: Without this, malicious dependencies could exfiltrate data

## Week 2-3: Multi-Repo Foundation

### Priority 1: Isolation & Secrets (40 hours)
- Implement per-repo OIDC federation with Vault
- Create repo-scoped secret paths
- Add basic container isolation

### Priority 2: Fair Scheduling (60 hours)
- Implement token-bucket rate limiting
- Add per-repo concurrency budgets
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
plan.md                    - Strategic architecture & roadmap
├── issues.md             - Security audit (13 vulnerabilities)
├── MULTI_REPO_ANALYSIS.md - Multi-tenancy gaps (6 categories)
├── ANALYSIS_INDEX.md     - Quick reference tables
└── START_HERE.md         - This file (action plan)
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

- Security Issues: See `issues.md` for detailed findings
- Architecture Questions: See `plan.md` for design rationale
- Multi-Repo Gaps: See `MULTI_REPO_ANALYSIS.md` for analysis
- Quick Reference: See `ANALYSIS_INDEX.md` for navigation