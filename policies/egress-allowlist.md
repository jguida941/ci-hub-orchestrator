# Runner Egress Allowlist

Source of truth: runner/proxy policy that backs `HTTP(S)_PROXY`/`NO_PROXY` in `.github/workflows/release.yml` (`DEFAULT_ALLOWLIST`) and any perimeter firewall rules. Keep this table in sync with the workflow and change-management tickets.

## Current Allowlist (from release workflow)
| Destination | Purpose | Notes |
|-------------|---------|-------|
| github.com, api.github.com | GitHub API + actions | Required for workflow/checkout. |
| ghcr.io | OCI registry for images/referrers | Matches release publishing. |
| registry.npmjs.org | npm registry | Tooling installs. |
| pypi.org, files.pythonhosted.org | PyPI registry | Python deps. |
| objects.githubusercontent.com, raw.githubusercontent.com, githubusercontent.com, actions.githubusercontent.com, pipelines.actions.githubusercontent.com, release-assets.githubusercontent.com | GitHub asset delivery | Workflow/downloads. |
| sigstore.dev | Sigstore TUF roots | Cosign verification. |
| storage.googleapis.com | Sigstore/Kind assets | Tool downloads. |
| kind.sigs.k8s.io, dl.k8s.io | kind/Kubernetes binaries | Local/CI clusters. |
| blob.core.windows.net | Action/cache backing store | Runner cache. |

## Environment-specific endpoints (fill these in)
| Destination | Purpose | Notes |
|-------------|---------|-------|
| `<dns-hostname>:53` | DNS resolution | Prefer org DNS or resolver behind the proxy. |
| `<artifacts-hostname>:443` | Upload Evidence Bundle | Enforce mTLS; aligns with `artifacts/evidence/*` publishing. |
| `<secrets-hostname>:8200` | Fetch short-lived credentials | Bound to runner identity; rotate client certs/tokens regularly. |
| `<ntp-hostname>:123` | Time synchronization | Hostname-based allow; pin to fixed-IP NTP relays if required. |

No other outbound connections are permitted. When adding a dependency, update the perimeter controls first, then record the change here with a ticket/approval link.
