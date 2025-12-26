# ADR-0030: Dependabot for Automated Dependency Updates

**Status**: Accepted
**Date:** 2025-12-26
**Developer:** Justin Guida
**Last Reviewed:** 2025-12-26

## Context

OpenSSF Scorecard flagged the repository for missing a dependency update tool
(Dependency-Update-Tool check). Keeping dependencies current is critical for:

- Security: patching known CVEs promptly
- Compliance: meeting supply-chain security requirements
- Maintainability: avoiding large version jumps

GitHub's Dependabot provides automated version updates with minimal configuration
and integrates natively with GitHub's security features.

## Decision

Enable Dependabot for automated dependency updates in the hub repository with
the following configuration:

### Ecosystems Covered

1. **GitHub Actions** (`github-actions`)
   - Updates action versions in `.github/workflows/`
   - Critical for supply-chain security (pinned SHA updates)

2. **Python pip** (`pip`)
   - Updates dependencies in `requirements.txt`, `pyproject.toml`
   - Keeps security and dev dependencies current

### Update Policy

- **Schedule**: Weekly (Monday) to batch updates and reduce PR noise
- **Grouping**: Dependencies grouped by ecosystem to minimize PR count
- **Commit prefix**: `chore(deps):` for conventional commit compatibility
- **Labels**: `dependencies` + ecosystem-specific label for filtering

### Not Yet Covered (Backlog)

The following ecosystems are tracked for future implementation when those
workflows are migrated to the hub pattern:

- Java (Maven/Gradle) in satellite repos
- Additional Python repos using hub workflows

## Consequences

**Positive:**
- Satisfies Scorecard Dependency-Update-Tool check
- Automated security patching for dependencies
- Reduced manual maintenance burden
- Consistent update cadence

**Negative:**
- Weekly PR volume (mitigated by grouping)
- Requires CI to validate updates before merge
- May surface breaking changes in dependencies

## References

- `.github/dependabot.yml`
- [GitHub Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [OpenSSF Scorecard Dependency-Update-Tool](https://github.com/ossf/scorecard/blob/main/docs/checks.md#dependency-update-tool)
