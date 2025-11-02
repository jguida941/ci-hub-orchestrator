# Issues Migration Guide

**Date**: November 2, 2025
**Status**: Completed

## Summary

The `issues.md` file has been deprecated and replaced with GitHub Issues for better tracking and collaboration.

## Migration Details

### What Changed
- **Old Location**: `issues.md` (root directory)
- **New Location**: https://github.com/jguida941/ci-cd-hub/issues
- **Reason**: Centralized issue tracking with better collaboration features

### Key Issues Migrated

The following critical issues from issues.md should be tracked in GitHub Issues:

#### High Priority Security Items
1. **Egress Control**: HTTP_PROXY/HTTPS_PROXY environment configuration
2. **Supply Chain Security**: SLSA attestation and provenance
3. **Policy Enforcement**: Kyverno policy implementation
4. **Secrets Management**: Vault integration for multi-repo secrets

#### Multi-Repository Support
1. **Dynamic Matrix**: GitHub Actions matrix strategy from config/repositories.yaml
2. **Repository Health Checks**: Connection verification for each repo
3. **Cross-Repository Dependencies**: Shared configuration management

#### Documentation & Governance
1. **Documentation Structure**: Reorganization under docs/ complete
2. **Link Validation**: Automated link checking in CI
3. **Orphan Detection**: No orphaned documents allowed

### How to Access

All issues are now tracked at: https://github.com/jguida941/ci-cd-hub/issues

### Creating New Issues

When creating new issues in GitHub:
1. Use appropriate labels (bug, enhancement, documentation, security)
2. Reference the plan.md for architectural context
3. Link related PRs and commits
4. Follow the issue templates in .github/ISSUE_TEMPLATE/

### Historical Context

The original issues.md contained unstructured issue tracking that has been formalized into:
- GitHub Issues for active work items
- plan.md for strategic roadmap
- docs/status/ for implementation status
- CHANGELOG.md for completed work

## References

- [Plan](../plan.md) - Strategic roadmap
- [Implementation Status](status/implementation.md) - Current progress
- [GitHub Issues](https://github.com/jguida941/ci-cd-hub/issues) - Active issue tracker