# Overview

![CI](#) ![Docs](#) ![License](#)

## Scope

This documentation set covers the tooling and scripts under `/tools` as well as shared architecture notes. GitHub Actions workflows and external integrations are referenced via `/docs/workflows/` when needed.

## Purpose

- Production-grade CI/CD observability and supply-chain assurance toolkit.

## Audience

- Developers, SREs, compliance teams working inside the CI Intelligence Hub.

## Architecture Diagram

```mermaid

flowchart TD
  A[Build & Sign] --> B[SBOM/VEX Referrers]
  B --> C[Policy Gates]
  C --> D[Mutation Observatory]
  D --> E[Cache Sentinel]

```bash

## Metadata

| Key | Value |

| --- | --- |

| Project | CI Intelligence Hub |

| Purpose | CI/CD observability + supply-chain assurance |

| Language | Python 3.12, Bash |

| License | SPDX-ID (MIT or actual) |

| Verified Environment | Python 3.12.x · pip 24.x · Ubuntu 22.04 |

## Canonical Artifact Paths

| Purpose | Path |

| --- | --- |

| Build evidence | artifacts/evidence/ |

| Policy inputs | policy-inputs/ |

| Mutation reports | artifacts/mutation/ |

| Chaos evidence | artifacts/chaos/ |

| DR drill evidence | artifacts/evidence/dr/ |

## Workflows & Modules

- [Agents Catalog](./AGENTS.md)

- [Mutation Observatory](./modules/mutation_observatory.md) → `.github/workflows/mutation.yml`

- [Chaos Runner](./modules/chaos_runner.md) → `.github/workflows/chaos.yml`

- [DR Drill Simulator](./modules/dr_drill.md) → `.github/workflows/dr-drill.yml`

- [Cache Sentinel](./modules/cache_sentinel.md) → release workflow cache evidence

- [Generate VEX](./modules/generate_vex.md)

- [Build Vuln Input](./modules/build_vuln_input.md)

Each workflow emits NDJSON for downstream analytics (GCS landing zone → BigQuery → dbt marts):

- Mutation: `artifacts/mutation/run.ndjson`

- Chaos: `artifacts/chaos/events.ndjson`

- DR drill: `artifacts/evidence/dr/events.ndjson`

## Dependency Matrix

| Module | Python deps | CLI tools | Optional |

| --- | --- | --- | --- |

| cache_sentinel | blake3, hashlib | – | jq |

| release workflow | jsonschema, pyyaml | cosign, syft, grype, oras, opa | – |

## Changelog

- 2025-10-26: Documentation framework initialized.
