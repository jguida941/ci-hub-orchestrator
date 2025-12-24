# Kyverno Deployment Guide

Kyverno policies already live in `policies/kyverno/`, but enforcing them
requires installing Kyverno on the target cluster and applying those
policies in `Enforce` mode. This directory and the accompanying script
provide a repeatable path that works for local kind clusters, shared dev
clusters, and production environments.

## Prerequisites

- `kubectl` with access to the target cluster / kube-context
- Optional but recommended: `helm` or `kustomize` if you prefer to manage
  the Kyverno installation outside the provided script
- Network access to fetch the pinned Kyverno release manifests (defaults
  to `v1.12.5`); override the URL when running in air-gapped environments

## Quick start

```bash
# Set your kube-context once; both make targets read it.
export KUBECTL_CONTEXT=kind-kyverno-ci

# Install Kyverno v1.12.5 + apply policies in one shot
make kyverno/deploy

# Generate deny/allow evidence for change management (writes to artifacts/evidence/kyverno)
make kyverno/verify

# (Optional) End-to-end smoke test on a disposable kind cluster
./scripts/run_kyverno_kind.sh --keep-cluster
```

`scripts/deploy_kyverno.sh` (invoked by `make kyverno/deploy`) applies the pinned
Kyverno release, waits for the controller deployments, renders `deploy/kyverno/`
to confirm every policy stays `validationFailureAction=Enforce`, performs a server-side
dry run, then applies the bundle. By default it pulls the Kyverno manifest from the
official release URL (`DEFAULT_INSTALL_URL`). Set `KYVERNO_USE_LOCAL_MANIFEST=true`
if you explicitly want to use the vendored `deploy/kyverno/install.yaml`.
`scripts/verify_kyverno_enforcement.sh --cluster` (wrapped by `make kyverno/verify`)
creates known-bad fixtures, runs them against the live cluster, and captures results
under `artifacts/evidence/`.

## CI end-to-end verification

The GitHub Actions workflow `.github/workflows/kyverno-e2e.yml` proves the
policies deny violations by:

1. Spinning up a kind cluster
2. Installing Kyverno (if needed) with `scripts/deploy_kyverno.sh --context kind-kyverno-ci`
3. Running `scripts/verify_kyverno_enforcement.sh --cluster --context kind-kyverno-ci`
   to demonstrate deny/allow behaviour

The workflow triggers automatically when Kyverno policies or deployment scripts
change. Use it as a template if you want to run the same validation in your own
CI/CD system.

## Production rollout checklist

1. Export `KUBECTL_CONTEXT=<prod-context>` and run `make kyverno/deploy` from an operator
   workstation to install/update Kyverno and apply the policies.
2. Confirm all Kyverno deployments are Ready:
   ```bash
   kubectl --context <prod-context> -n kyverno get deploy
   ```
3. Execute `make kyverno/verify` (optionally override `KYVERNO_VERIFY_NAMESPACE`
   and `KYVERNO_EVIDENCE_DIR`) to demonstrate deny/allow behaviour on the live cluster.
4. Capture the resulting evidence under `artifacts/evidence/` for audit trails
5. Add observability (alerts, dashboards) to monitor Kyverno health in production

> Tip: run the GitHub Actions workflow first to catch regressions before deploying
> the policies to production clusters. For local parity, use `./scripts/run_kyverno_kind.sh`
> to spin up a throwaway kind cluster, run the make targets, and tear it down automatically.
