# ADR-0010: Dispatch Token and Skip Flag

**Status**: Accepted  
**Date:** 2025-12-22  
**Developer:** Justin Guida  
**Last Reviewed:** 2025-12-26  

- Updated: 2025-12-23

## Context

Cross-repo dispatch requires a token with `actions: write` and `contents: read` on target repos. Fixtures and some repos should remain central-only to avoid dispatch failures and token requirements. Artifact collisions occurred when multiple dispatch jobs used the same names.

## Decision

- Add `repo.dispatch_enabled` (default true) to config schema; orchestrator skips dispatch when false (used for fixtures/central-only repos).
- Allow orchestration to use a PAT secret (`HUB_DISPATCH_TOKEN`) with `repo` + `workflow` scopes; fallback to GITHUB_TOKEN if unset.
- Make artifact names unique per repo (e.g., `ci-report-${{ matrix.name }}`) to avoid collisions.
- Provide CLI command `cihub setup-secrets` to configure tokens across repos.

## CLI Setup

### HUB_DISPATCH_TOKEN (Required for Distributed Mode)

```bash
# Set HUB_DISPATCH_TOKEN on hub repo with verification (recommended)
cihub setup-secrets --hub-repo owner/hub-repo --verify

# Also push to all connected repos
cihub setup-secrets --hub-repo owner/hub-repo --all --verify
```

The CLI reads connected repos from `config/repos/*.yaml` and sets the secret on each.

### NVD_API_KEY (Required for Java OWASP Scans)

Without an NVD API key, OWASP Dependency Check downloads 300K+ vulnerability records without rate limiting, taking 30+ minutes. With a key, it takes ~2-3 minutes.

```bash
# Set NVD_API_KEY on all Java repos with verification
cihub setup-nvd --verify
```

Get a free NVD API key at: https://nvd.nist.gov/developers/request-an-api-key

The CLI automatically detects Java repos from `config/repos/*.yaml` and sets `NVD_API_KEY` on each.

## Token Requirements

**Classic PAT:** `repo` + `workflow` scopes (covers all owned repos)

**Fine-grained PAT:**
- Repository access: Include hub + all connected repos
- Permissions: Actions (Read and Write), Contents (Read), Metadata (Read)

## Consequences

Positive:
- Avoids dispatch attempts to central-only repos.
- Explicit token path for dispatch; clearer failure mode.
- Reduces artifact name conflicts across jobs.
- CLI automates secret distribution across repos.

Negative:
- Requires managing an extra secret for dispatch-capable repos.
- More config surface (dispatch flag) to maintain.

## CLI Token Verification

The `cihub setup-secrets --verify` command performs two-stage verification:

1. **Authentication check**: Validates token against GitHub API (`/user` endpoint)
2. **Cross-repo access check**: Verifies token can access artifacts from connected repos

```python
# Stage 1: Basic auth
GET https://api.github.com/user
# Returns scopes in X-OAuth-Scopes header

# Stage 2: Cross-repo artifact access (required for orchestrator aggregation)
GET https://api.github.com/repos/{connected_repo}/actions/artifacts
# Must succeed for orchestrator to download reports
```

The cross-repo check uses the first repo from `config/repos/*.yaml`, ensuring it tests the user's actual configuration, not a hardcoded repo.

## Security Considerations

**Token storage**: The CLI passes tokens via stdin (`input=token` in subprocess), never as command-line arguments. This prevents tokens from appearing in:
- Process lists (`ps aux`)
- Shell history
- Log files

**Bug fix (2025-12-23)**: Removed `--body -` flag from `gh secret set` call which caused token corruption during storage. The `gh` CLI reads from stdin by default; the explicit flag conflicted with subprocess stdin handling.

## Alternatives Considered

- Forcing dispatch everywhere: rejected because fixtures/central-only repos lack workflows and would fail.
- Using only GITHUB_TOKEN: rejected because it often lacks cross-repo permissions.
- Passing token via `--body <value>`: rejected because it exposes token in process list.
