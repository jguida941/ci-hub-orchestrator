# ADR-0012: Kyverno Policies for Kubernetes Admission Control

- Status: Accepted
- Date: 2025-12-15

## Context

The CI/CD Hub focuses on build-time quality and security through GitHub Actions. However, for organizations that deploy to Kubernetes clusters, runtime admission control is equally important. Kyverno policies extend the hub's security posture from build-time to deploy-time.

Four policies are included:

| Policy | Purpose | Enforcement |
|--------|---------|-------------|
| `block-pull-request-target` | Block dangerous GHA trigger | Enforce |
| `require-referrers` | Require SBOM/provenance annotations | Audit |
| `secretless` | Block static secrets, enforce OIDC | Audit |
| `verify-images` | Verify Cosign keyless signatures | Audit |

Considerations:
- **Scope:** Hub-release is GitHub Actions-focused; Kyverno is optional for K8s deployments
- **Alignment:** Policies complement build-time tools (Trivy, Semgrep, OWASP) with runtime enforcement
- **Flexibility:** Users can apply policies selectively based on their cluster requirements
- **Testing:** Policies can be validated without a K8s cluster using `kyverno apply --dry-run`

## Decision

- Include Kyverno policies as an **optional feature** for users deploying to Kubernetes
- Policies are stored in `policies/kyverno/` with documentation
- A validation workflow (`kyverno-validate.yml`) validates policy syntax on changes
- Policies default to `Audit` mode (warning only) for safe adoption; users upgrade to `Enforce` when ready
- The `block-pull-request-target` policy uses `Enforce` by default as it's a critical security control

## Alternatives Considered

1. **Remove Kyverno entirely:** Rejected - valuable for users with K8s deployments
2. **Full integration with E2E testing:** Rejected - requires cluster infrastructure beyond hub scope
3. **Make Kyverno mandatory:** Rejected - not all users deploy to Kubernetes

## Consequences

- Users with Kubernetes clusters can apply policies for runtime security
- Policies are validated on every PR to catch syntax errors
- Documentation explains when and how to use policies
- Templates allow customization (image paths, issuer URLs)
- No impact on users who don't deploy to Kubernetes

## Related Files

- `policies/kyverno/*.yaml` - Policy definitions
- `.github/workflows/kyverno-validate.yml` - Syntax validation
- `templates/kyverno/` - Customizable policy templates
- `docs/guides/KYVERNO.md` - User guide

## References

- [Kyverno Documentation](https://kyverno.io/docs/)
- [GitHub Actions Security: pull_request_target](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/)
- [Cosign Keyless Signing](https://docs.sigstore.dev/cosign/keyless/)
