# ADR-0027: Hub Production CI Policy

**Status**: Accepted  
**Date:** 2025-12-25  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

## Context

The hub repo is production-grade and intended for commercial use. Its CI must be
deterministic, security-hardened, and auditable. Recent changes introduced a
dedicated hub production CI workflow with expanded security checks, mutation
testing, and strict gates. This ADR documents the policy to keep those choices
stable and enforced over time.

## Decision

Adopt a hardened hub production CI workflow with strict gates and pinned
actions. The workflow must provide explicit pass/fail visibility for every
critical check and enforce security/supply-chain standards.

### Policy Requirements

1. **Pinned actions only**
   - All `uses:` references must be pinned to a commit SHA.
2. **Explicit pass/fail reporting**
   - CI summary must show pass/fail (or skipped) for all gates.
3. **Hard gates for critical checks**
   - Workflow/security checks must fail the run on error.
   - Dependency review and scorecard must fail when they run and report errors.
4. **Mutation testing required**
   - Mutation testing runs on `cihub/` with a minimum threshold.
5. **Artifacted reports**
   - Security and test outputs must be uploaded for review.

## Consequences

**Positive:**
- Clear, auditable CI outcomes
- Strong supply-chain posture
- Consistent enforcement across changes

**Negative:**
- CI can be stricter than local dev defaults
- Requires maintenance of pinned SHAs

## References

- `docs/development/archive/ARCHITECTURE_PLAN.md`
- `.github/workflows/hub-production-ci.yml`
