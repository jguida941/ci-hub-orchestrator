CI Intelligence Hub -- Production-Grade CI/CD Architecture

Executive thesis
Build a CI/CD platform that quantifies test effectiveness, explains failures, enforces supply-chain trust, proves determinism, injects controlled faults, and turns pipeline signals into actionable analytics. Align to SLSA L3, DR objectives (RPO/RTO), DORA metrics, and full traceability.

Primary outcomes
- Trust: attested, signed, reproducible builds with policy gates.
- Reliability: resilient pipelines that self-diagnose and recover.
- Insight: first-class metrics, lineage, and executive scorecards.
- Efficiency: predictive scheduling, cache integrity, cost/carbon tracking.

Pillars (modules)
1. Mutation Observatory
   - Run unit + mutation tests on PRs. Compute resilience score and delta vs main.
   - Post PR labels weak-tests, high-confidence. Plot resilience vs coverage.
   - Language mutators: StrykerJS, mutmut, PIT, go-mutesting.
   - Outputs: mutation_runs, mutation_trends, file-level hotspots, EWMA control limits.

2. Pipeline Autopsy
   - Collect logs, parse signatures, classify root causes, propose fixes.
   - Open GitHub issues with summaries and repro steps.
   - Rule-first, ML-second; precision/recall tracked. Redact secrets.
   - Parsers: pytest, jest, maven/gradle, npm/pnpm, cargo, docker, terraform, ansible.
   - Storage: failure_signatures, autopsy_reports.

3. Predictive Build Scheduler
   - Learn runtime from history. Predict per-job duration and select runners or split matrices.
   - Features: {changed_files, test_count, cache_hits, runner_type, queue_ms}.
   - Online updates each run. Target MAPE <= 15% (p50 runtime error < 15%).
   - Storage: prediction_runs.

4. Deterministic DevOps Sandbox
   - Bit-for-bit reproducible builds across OS and time.
   - Pin deps, locale, time zone, seed, artifacts; set TZ=UTC, LC_ALL=C, SOURCE_DATE_EPOCH.
   - Strip timestamps from wheels/archives. Dual-run checksum comparison. Fail on drift.
   - Attach binary diff summary to PR and Evidence Bundle.

5. Chaos-in-the-Pipeline
   - Inject faults (1% PR light; nightly heavy): kill_job, delay_net, drop_net, corrupt_cache, cpu_stress, disk_fill.
   - Require retries, artifact fallback, alerting. Record seed and outcomes.
   - Storage: chaos_trials. Produce resilience report.

6. Ephemeral Data Lab
   - Spin up temporary databases via Docker Compose or Testcontainers in CI.
   - Seed fuzz data (property-based tests). Snapshot DB state as artifact.

7. Compliance-as-Code Validator
   - YAML/rego policies: pinned action SHAs, SPDX license allowlist, least privilege.
   - Enforce per commit. Generate HTML report. Output policy_violations.

8. Self-Healing Build Cache (Cache Sentinel)
   - Distributed cache (S3/MinIO/Redis). BLAKE3 content-addressed keys.
   - Verify checksums on get; quarantine mismatches; scrub and rebuild.
   - Dashboard: hit ratio, health, rebuild cost. Emits cache_events.

9. Infrastructure Replay
   - Record Terraform/Ansible plan/apply/drift. Enable one-command local replay.
   - Track provider versions and tie to commit graph.

10. Metrics Intelligence Dashboard (umbrella product)
   - Centralize pipeline logs, test telemetry, cost, carbon, chaos results into the data lake/warehouse.
   - Dashboards: resilience trends, mutation effectiveness, DORA, cache, chaos, determinism, SLOs.
   - Self-service SQL + notebooks. ChatOps reporting. Executive scorecards. Exportable compliance snapshots.

11. CI/CD Gamification Hub (optional, Phase 4)
   - Scoreboard for builds passed, time reduced, coverage raised.
   - Leaderboard via GitHub Pages. Achievement badges.

High-level architecture

             GitHub/GitLab
                 |
           Webhook Receiver
                 |
             Event Bus (NATS)
                 |
   -------------------------------
   |             |               |
 Orchestrator  Analyzers      Sinks
   |        (modular workers)   |
   |    - Mutation Observatory   |--> PR Comments Service
   |    - Pipeline Autopsy       |--> HTML Reports
   |    - Predictive Scheduler   |--> Dashboard API
   |    - Deterministic Auditor  |
   |    - Chaos Injector         |
   |    - Ephemeral Data Lab     |
   |    - Compliance Validator   |
   |    - Cache Sentinel         |
   |    - Infra Replay           |
   -------------------------------
        |             |           |
   Postgres      Object Store   Traces/Logs
   (metrics,     (artifacts,    (OTel->Loki/Tempo)
   findings)     logs, DB snaps)

Core components
- GitHub App: webhook receiver, PR/issue writer, Checks API integration.
- CI agent CLI (Go or Rust) runs inside pipelines, executes analyzers, uploads events.
- Orchestrator schedules, deduplicates, retries, backfills.
- Analyzer services (gRPC/HTTP): all pillars above.
- Storage: Postgres metadata; S3/MinIO artifacts/logs/snapshots; Redis optional.
- Observability: OpenTelemetry -> Grafana/Loki/Tempo.
- Policy engine: Rego or CEL.
- ML: scikit-learn baseline; pluggable LLM for classification.

Reference stack (pinned)
- Ingest: GCS landing zone -> BigQuery (partition _DATE, cluster repo, pr).
- Transform: dbt models.
- Real-time ops: Grafana with Loki/Prometheus.
- Batch dashboards: Looker Studio.
- Runners: GitHub Actions plus self-hosted label for heavyweight jobs.

Data contracts and lineage

Authoritative NDJSON contract (pipeline_run.v1.2)
- Canonical: flakiness_index is top-level; do not embed under tests.resilience.
- Backward compat: v1.1 -> v1.2 migration and compat view provided.

JSON Schema (pipeline_run.v1.2)
```
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ci-intel.dev/schema/pipeline_run.v1.2.json",
  "title": "pipeline_run v1.2",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema",
    "run_id",
    "repo",
    "commit_sha",
    "branch",
    "started_at",
    "ended_at",
    "status",
    "jobs",
    "tests",
    "cost"
  ],
  "properties": {
    "schema": { "const": "pipeline_run.v1.2" },
    "run_id": { "type": "string", "format": "uuid" },
    "repo": { "type": "string", "pattern": "^[^/]+/[^/]+$" },
    "commit_sha": { "type": "string", "pattern": "^[0-9a-fA-F]{40}$" },
    "branch": { "type": "string" },
    "pr": { "type": ["integer", "null"], "minimum": 1 },
    "started_at": { "type": "string", "format": "date-time" },
    "ended_at": { "type": "string", "format": "date-time" },
    "status": { "type": "string", "enum": ["success", "failed", "canceled", "skipped"] },
    "queue_ms": { "type": "integer", "minimum": 0 },
    "artifact_bytes": { "type": "integer", "minimum": 0 },
    "environment": { "type": "string", "enum": ["preview", "dev", "staging", "prod", "test"] },
    "deployment_id": { "type": "string" },
    "rollout_step": { "type": ["integer", "null"], "minimum": 0 },
    "strategy": { "type": "string", "enum": ["direct", "rolling", "blue-green", "canary"] },
    "image_digest": { "type": "string", "pattern": "^sha256:[0-9a-fA-F]{64}$" },
    "sbom_uri": { "type": "string", "format": "uri" },
    "provenance_uri": { "type": "string", "format": "uri" },
    "signature_uri": { "type": "string", "format": "uri" },
    "release_evidence_uri": { "type": "string", "format": "uri" },
    "runner_os": { "type": "string", "enum": ["linux", "windows", "macos"] },
    "runner_type": { "type": "string", "enum": ["hosted", "self-hosted"] },
    "region": { "type": "string" },
    "spot": { "type": "boolean" },
    "carbon_g_co2e": { "type": "number", "minimum": 0 },
    "energy": {
      "type": "object",
      "additionalProperties": false,
      "properties": { "kwh": { "type": "number", "minimum": 0 } }
    },
    "cache_keys": { "type": "array", "items": { "type": "string" } },
    "flakiness_index": { "type": "number", "minimum": 0, "maximum": 1 },
    "canary_metrics": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "error_rate": { "type": "number", "minimum": 0 },
        "success_rate": { "type": "number", "minimum": 0, "maximum": 1 },
        "latency_p50_ms": { "type": "number", "minimum": 0 },
        "latency_p95_ms": { "type": "number", "minimum": 0 },
        "latency_p99_ms": { "type": "number", "minimum": 0 },
        "reqs_per_s": { "type": "number", "minimum": 0 }
      }
    },
    "rollback_reason": { "type": "string" },
    "jobs": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "name", "status", "duration_ms"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["success", "failed", "canceled", "skipped"] },
          "attempt": { "type": "integer", "minimum": 1 },
          "duration_ms": { "type": "integer", "minimum": 0 },
          "queue_ms": { "type": "integer", "minimum": 0 },
          "cache": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "hit": { "type": "boolean" },
              "key": { "type": "string" }
            }
          },
          "machine": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "class": { "type": "string" },
              "cpu": { "type": "string" },
              "ram_gb": { "type": "number", "minimum": 0 }
            }
          },
          "matrix": {
            "type": "object",
            "additionalProperties": { "type": ["string", "number", "boolean"] }
          },
          "logs_uri": { "type": "string", "format": "uri" }
        }
      }
    },
    "tests": {
      "type": "object",
      "additionalProperties": false,
      "required": ["total", "failed", "duration_ms", "resilience"],
      "properties": {
        "total": { "type": "integer", "minimum": 0 },
        "failed": { "type": "integer", "minimum": 0 },
        "skipped": { "type": "integer", "minimum": 0 },
        "duration_ms": { "type": "integer", "minimum": 0 },
        "coverage": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "lines_pct": { "type": "number", "minimum": 0, "maximum": 1 },
            "branches_pct": { "type": "number", "minimum": 0, "maximum": 1 },
            "statements_pct": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        },
        "resilience": {
          "type": "object",
          "additionalProperties": false,
          "required": ["mutants_total", "killed", "equiv", "timeout", "score"],
          "properties": {
            "mutants_total": { "type": "integer", "minimum": 0 },
            "killed": { "type": "integer", "minimum": 0 },
            "equiv": { "type": "integer", "minimum": 0 },
            "timeout": { "type": "integer", "minimum": 0 },
            "score": { "type": "number", "minimum": 0, "maximum": 1 },
            "delta_vs_main": { "type": "number", "minimum": -1, "maximum": 1 },
            "equivalent_mutants_dropped": { "type": "boolean" }
          }
        }
      }
    },
    "chaos": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["fault", "target", "seed", "outcome"],
        "properties": {
          "fault": {
            "type": "string",
            "enum": ["kill_job", "delay_net", "drop_net", "corrupt_cache", "cpu_stress", "disk_fill"]
          },
          "target": { "type": "string" },
          "seed": { "type": "integer" },
          "rate": { "type": "number", "minimum": 0, "maximum": 1 },
          "started_at": { "type": "string", "format": "date-time" },
          "ended_at": { "type": "string", "format": "date-time" },
          "outcome": { "type": "string", "enum": ["recovered", "degraded", "failed"] },
          "retries": { "type": "integer", "minimum": 0 }
        }
      }
    },
    "autopsy": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "root_causes": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["pattern", "suggestion"],
            "properties": {
              "tool": { "type": "string" },
              "pattern": { "type": "string" },
              "file": { "type": "string" },
              "line": { "type": "integer", "minimum": 1 },
              "message": { "type": "string" },
              "suggestion": { "type": "string" },
              "severity": { "type": "string", "enum": ["info", "warn", "error"] },
              "docs_uri": { "type": "string", "format": "uri" }
            }
          }
        }
      }
    },
    "policies": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "result"],
        "properties": {
          "id": { "type": "string" },
          "result": { "type": "string", "enum": ["allow", "deny", "warn"] },
          "reason": { "type": "string" },
          "docs_uri": { "type": "string", "format": "uri" },
          "time_ns": { "type": "integer", "minimum": 0 }
        }
      }
    },
    "cost": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "usd": { "type": "number", "minimum": 0 },
        "cpu_seconds": { "type": "number", "minimum": 0 },
        "gpu_seconds": { "type": "number", "minimum": 0 }
      }
    }
  }
}
```

Example record (pipeline_run.v1.2)
```
{"schema":"pipeline_run.v1.2","run_id":"1b7c2e4a-6b54-4e3b-9f1e-4e0d9ea9b1a1","repo":"org/app","commit_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","branch":"feature/x","pr":123,"started_at":"2025-10-23T12:00:00Z","ended_at":"2025-10-23T12:04:10Z","status":"success","queue_ms":5000,"artifact_bytes":7340032,"environment":"staging","deployment_id":"deploy-20251023-1200","rollout_step":2,"strategy":"canary","image_digest":"sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd","sbom_uri":"https://gcs.example.com/sbom/aaaa.json","provenance_uri":"https://gcs.example.com/prov/aaaa.intoto","signature_uri":"https://gcs.example.com/sig/aaaa.sig","release_evidence_uri":"https://gcs.example.com/evidence/manifest.json","runner_os":"linux","runner_type":"hosted","region":"us-central1","spot":false,"carbon_g_co2e":0.07,"energy":{"kwh":0.03},"cache_keys":["pip-3.12","pytest"],"flakiness_index":0.02,"canary_metrics":{"error_rate":0.001,"success_rate":0.999,"latency_p50_ms":45,"latency_p95_ms":88,"latency_p99_ms":140,"reqs_per_s":120},"jobs":[{"id":"build","name":"build","status":"success","attempt":1,"duration_ms":70000,"queue_ms":2000,"cache":{"hit":true,"key":"pip-3.12"},"machine":{"class":"standard","cpu":"4","ram_gb":16},"logs_uri":"https://gcs.example.com/logs/build.log"},{"id":"test","name":"pytest","status":"success","attempt":1,"duration_ms":120000,"queue_ms":1000,"cache":{"hit":false,"key":"pytest"},"machine":{"class":"standard","cpu":"4","ram_gb":16},"logs_uri":"https://gcs.example.com/logs/pytest.log"}],"tests":{"total":1240,"failed":2,"skipped":10,"duration_ms":118000,"coverage":{"lines_pct":0.86,"branches_pct":0.79,"statements_pct":0.84},"resilience":{"mutants_total":900,"killed":810,"equiv":30,"timeout":12,"score":0.9,"delta_vs_main":0.03,"equivalent_mutants_dropped":true}},"chaos":[{"fault":"kill_job","target":"pytest","seed":42,"rate":0.01,"started_at":"2025-10-23T12:01:10Z","ended_at":"2025-10-23T12:01:30Z","outcome":"recovered","retries":1}],"autopsy":{"root_causes":[{"tool":"pytest","pattern":"AttributeError: NoneType","file":"tests/x_test.py","line":42,"message":"AttributeError: NoneType","suggestion":"ensure setup returns object or add __init__.py","severity":"warn","docs_uri":"https://docs.example.com/autopsy/attrerror"}]},"policies":[{"id":"two_person_prod","result":"allow","reason":"Distinct approvers met two-person rule"}],"cost":{"usd":1.23,"cpu_seconds":420,"gpu_seconds":0}}
```

Metrics dictionary (docs/metrics.md)
- Resilience: killed / max(1, mutants_total - equivalent); ratio 0-1; persist delta_vs_main and control-limit metadata; label weak-tests by thresholds.
- Flake index: flaky_runs / total_runs per suite (excludes quarantined tests); 30-day rolling view.
- MTTR: median time from failure detection to successful rerun/deploy; minutes; per environment.
- Cost/run: USD per pipeline run; aggregate by repo and pipeline.
- Carbon/run: grams CO2e; aggregate weekly.
- Burn rate: actual_error_minutes / allowed_minutes over 1h, 6h, 24h windows.

Schema CI gate and compat
- schema-ci workflow validates NDJSON against pipeline_run.v1.2; fail PRs on mismatch.
- dbt compat view pipeline_runs_all coalesces v1.1 and v1.2; tests unique(run_id), accepted_values(status), conditional not_null(release_evidence_uri) when environment in ('staging','prod') and status='success'.
- Backfill script populates policy[] and security defaults for historical runs.

Security, supply chain, and governance
- OIDC to cloud; no static keys.
- SLSA L3 path: SBOM, provenance, cosign signatures, Rekor verify; block deploy on missing or invalid attestation.
- Policies enforced at merge and deploy: pinned action SHAs, SPDX license allowlist, least-privilege permissions, IaC and secret scanning.
- Threat model (STRIDE) documented in docs/THREAT_MODEL.md, updated quarterly.
- Evidence links embedded in PR comments, dashboards, and release_evidence_uri.

Release Evidence Bundle
```
{
  "run_id": "uuid",
  "image_digest": "sha256:...",
  "sbom_uri": "gs://.../sbom.json",
  "provenance_uri": "gs://.../prov.intoto",
  "signature_uri": "gs://.../cosign.sig",
  "rekor_uuid": "uuid",
  "vex_uri": "gs://.../vex.json",
  "tests": {"matrix": "json", "resilience": 0.87, "flake_index": 0.012},
  "perf": {"latency_p95_ms": 210, "budget_pass": true},
  "policies": [{"id": "two_person_prod", "result": "allow"}],
  "drill": {"type": "rollback", "rpo_s": 60, "rto_s": 300, "result": "pass"}
}
```

Observability, SLOs, and acceptance gates
- OpenTelemetry spans for build/test/deploy; trace IDs appear in PR comments and dashboards.
- Golden signals per environment; SLO/error-budget gating triggers auto-rollback when burn rate spikes.

Success criteria (ship gates)
- Ingest freshness P95 <= 5 minutes from workflow completion to warehouse.
- Dashboard query P95 <= 10 seconds on 30-day window.
- Resilience trend power >= 0.8 across 10 PRs.
- Deterministic builds produce identical artifacts across paired runners.
- Supply chain: 100% releases meet SLSA L3 with Rekor verification.
- DR: RPO <= 1 minute, RTO <= 5 minutes, validated weekly with archived evidence.
- Quality: resilience >= 0.75; flake index reduced 50% in 30 days.
- Performance: canary p95 latency budgets green; block on failure.
- Automation: >= 90% deployments auto-promote.

Phased delivery plan

Phase 0 -- Alignment
- Define personas (executive, engineering, SRE, compliance) and KPI targets: resilience, mutation delta, DORA, cache hit %, cost, carbon.
- Decide on data freshness expectations, hosting model, and metric access guardrails.
- Freeze scope until the umbrella dashboard ships.

Phase 1 -- Hermetic build path + CD essentials
- Rootless/distroless builder pinned by digest; produce SBOM + provenance; register attestations in Rekor.
- Dual-run determinism check for every release build.
- Enforce OIDC-only identity; deny static keys.
- Deploy Rego packs: two-person approvals, pinned action SHAs, egress allowlists.
- GitOps dev deploy with smoke tests; rollback automation; generate Evidence Bundle.
- Emit NDJSON v1.2 from unit.yml, mutation.yml, chaos.yml.

Phase 2 -- Ingestion and storage
- Instrument workflows to emit structured events (JSON artifacts, test telemetry, chaos outcomes, cache stats).
- Configure transport (Kafka/Kinesis/Pub/Sub or direct ingest) with schema validation and retry/backfill logic.
- Load to BigQuery raw partitioned by repo/pipeline/date; curate marts with dbt/SQLMesh: pipeline_runs, test_resilience, cost_usage, chaos_events, ownership dimensions.

Phase 3 -- Policy, gates, and analytics
- PR gates: OpenAPI/GraphQL diff, performance budgets (k6/Locust), diff coverage + test-impact selection, fuzz/property smoke tests.
- Publish dashboards: Run Health, Efficiency, Quality, Chaos/Determinism, Sustainability.
- Alerting correlates regressions to commits/teams/infra changes; ChatOps integrations push summaries.
- Schema-CI, compat view, and migration tests fully operational.

Phase 4 -- Reliability hardening and chaos
- Nightly heavy chaos; 1% PR chaos with kill-switch and fault allowlist.
- Backup/restore pipelines with weekly DR drills recorded in warehouse.
- Runner autoscaling and queue failover in place.
- Infrastructure Replay service active.

Phase 5 -- Advanced analytics and optional gamification
- Notebook workspace (Jupyter/Hex) for anomaly detection (Prophet/ARIMA) and goal tracking.
- Executive scorecards, compliance exports, weekly digests.
- Gamification hub launched if core SLOs sustained.

Roadmap notes: CD essentials start in Phase 1; canary rollout and policy gates mature in Phase 2-3; heavy chaos and replay in Phase 4; leaderboards Phase 5.

Critical delivery adds
- Delivery path: signed artifact -> GitOps environment repo -> progressive rollout -> automatic rollback on SLO burn with smoke + synthetic checks at every stage.
- Preview environments: per-PR stack with TTL, seeded database, unique URL + chaos toggle + mutation summary posted in PR comment.
- Supply chain gate: SBOM, provenance, signature verification enforced before deploy.
- Policy gates: Rego checks at merge and deploy (pinned SHAs, SPDX allowlist, least privilege).
- Observability: OTel spans across build/test/deploy; trace IDs in PR comments and dashboards.
- SLO enforcement: error-budget burn policies gating promotion; weekly rollback drill recorded to warehouse.
- Privacy: secret scanning and log redaction before Autopsy upload.
- Cost/carbon telemetry: per-run cost, cache savings, region, grams CO2e surfaced in dashboards.
- DR + idempotency: backfill re-ingest pipeline, immutable artifact storage, disaster recovery runbook.
- Developer experience: local pipeline emulator, Makefile targets, ChatOps /promote and /rollback commands.

Tightened specs
- Mutation: diff-only on PRs, full mutation nightly; exclude equivalent mutants; publish control limits; highlight file-level hotspots.
- Autopsy: rule-first, ML-second; track precision/recall; attach repro commands; redact secrets per policy.
- Predictive scheduler: features {changed_files, test_count, cache_hits, runner_type, queue_ms}; online update each run; target MAPE <= 15%.
- Chaos: 1% PR chaos, nightly heavy suite; kill-switch and fault allowlist; record seed for replay.
- Cache sentinel: BLAKE3 content-addressed keys, checksum on get, quarantine and scrub job on mismatch.

Minimal CD acceptance proof points
- A1: signed + attested images required; deploy rejects missing/invalid signatures.
- A2: GitOps PR merges to dev; smoke passes; promotion PR opens for staging.
- A3: 20% canary evaluates metrics; auto-promote or rollback with reason captured.
- A4: dashboard shows commit->deploy trace including cost and grams CO2e.

Gate implementations
```
- name: Gate on resilience
  run: |
    SCORE=$(jq -r '.tests.resilience.score' artifacts/pipeline_run.ndjson)
    MIN=0.75
    if awk "BEGIN{exit !($SCORE < $MIN)}"; then
      echo "Resilience $SCORE < $MIN"
      exit 1
    fi
```
```
cosign verify --key cosign.pub "$IMAGE_DIGEST"
opa eval -i deploy/context.json -d policies 'data.allow' | grep -q true
```

Rego: two-person rule
```
package deploy

default allow = false

valid_env { input.env == "prod" }
fresh(d) { time.now_ns() - d.time_ns < 15 * 60 * 1e9 }
distinct(as) { count(as) == count({a | a := as[_]}) }

allow {
  valid_env
  distinct(input.approvers)
  count(input.approvers) >= 2
  forall input.approvals[i] { fresh(input.approvals[i]) }
}
```

Determinism and chaos control flow
```
flowchart TD
  P[CI job step] --> Q[Chaos injector\nseed, rate]
  Q --> R{Fault triggers?}
  R -- no --> S[Continue job]
  R -- yes --> T[Job fails or degrades]
  T --> U[Retry policy\nbackoff, max N]
  U --> V{Recovered?}
  V -- yes --> W[Mark recovered\nrecord chaos event]
  V -- no --> X[Fail stage\nemit artifacts and logs]
  W --> Y[Emit chaos event\nNDJSON]
  X --> Y
  Y --> Z[Alerting\nPR comment and Slack]
  X --> AA[Autopsy parser]
  AA --> AB[Root cause classification]
  AB --> AC[Suggested fix\nopen issue or update PR]
  AC --> AD[Dashboard updates\nresilience and chaos stats]
```

Data flow (CI -> analytics stack)
```
flowchart LR
  subgraph Dev["Developer repos"]
    A[GitHub Actions\nemitters produce NDJSON artifacts]
  end
  A -->|upload-artifact| B[Artifact bundle]
  B -->|OIDC upload| C[GCS landing bucket\nraw/ndjson/YYYY=MM=DD/]
  C --> D[Ingestion job\nbatch or streaming loader]
  D --> E[BigQuery dataset: raw\npipeline_run_raw]
  E --> F[dbt models]
  F --> G[BigQuery dataset: marts\npipeline_runs\ntest_resilience\nchaos_events\ncost_usage]
  G --> H[Dashboards\nLooker Studio]
  G --> I[Ops dashboards\nGrafana via Loki/Prometheus]
  E -. audit, lineage .- J[Provenance, SBOM, signatures in GCS]
  G --> K[ChatOps reports\nSlack or Teams]
```

CI wiring (GitHub Actions)
```
name: ci-intelligence
on:
  pull_request:
  push:
jobs:
  agent:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      checks: write
      issues: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Start agent
        uses: docker://ghcr.io/ci-intel/agent:latest
        with:
          args: >
            run
            --mods=mutation,autopsy,compliance,predict
            --upload-artifacts
```

CD skeleton (GitHub Actions)
```
name: release
on:
  push:
    tags: ["v*.*.*"]
jobs:
  build_sign:
    runs-on: ubuntu-22.04
    permissions: { id-token: write, contents: read }
    steps:
      - uses: actions/checkout@<pin>
      - run: ./scripts/build.sh
      - run: ./scripts/sbom.sh > sbom.json
      - run: cosign sign --yes $IMAGE
      - run: ./emitters/build_ndjson.py
      - uses: actions/upload-artifact@<pin>
        with: { name: pipeline_run, path: artifacts/pipeline_run.ndjson }

  promote_dev:
    needs: build_sign
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@<pin>
        with: { repository: org/gitops, token: ${{ secrets.GITOPS_TOKEN }} }
      - run: ./scripts/bump-image.sh $IMAGE_DIGEST envs/dev
      - run: git commit -am "Promote to dev" && git push

  verify_dev:
    needs: promote_dev
    runs-on: ubuntu-22.04
    steps:
      - run: ./scripts/wait-rollout.sh dev
      - run: ./scripts/smoke.sh dev

  promote_staging:
    if: success()
    needs: verify_dev
    runs-on: ubuntu-22.04
    steps:
      - run: ./scripts/open-promotion-pr.sh staging

  canary_prod:
    needs: promote_staging
    runs-on: ubuntu-22.04
    steps:
      - run: ./scripts/wait-rollout.sh prod --canary 20
      - run: ./scripts/verify-canary.sh
      - run: ./scripts/promote-or-rollback.sh
```

Minimal viable surface
- Three GitHub Actions emitters (unit.yml, mutation.yml, chaos.yml) output NDJSON artifacts.
- ingest/ingest.py uploads NDJSON to GCS and loads BigQuery.
- Dashboards: Run Health Overview, Mutation Effectiveness.
- Pipeline Autopsy v0: regex classifier with suggestion table.

Determinism hooks
- TZ=UTC, LC_ALL=C, SOURCE_DATE_EPOCH = commit timestamp.
- Strip timestamps from wheels/archives; compare SHA256 across duplicate jobs; fail on drift.

Repository layout
- /.github/workflows/ -- workflow emitters.
- /emitters/ -- action helpers and NDJSON builders.
- /ingest/ -- loader scripts and schema definitions.
- /models/ -- dbt project.
- /dashboards/ -- Looker Studio or LookML definitions.
- /autopsy/ -- patterns.json, classifier code.
- /docs/ -- ADRs, data-contract.md, runbooks.
- /apps/github-app/, /agent/, /services/, /pkg/, /deploy/, /ui/.

Autopsy rule example
```
- id: py.initpkg.missing
  tool: pytest
  match: "ImportError: attempted relative import.*"
  hint: "Add __init__.py to package directories."
```

Issue template
```
🚨 Build #128 root causes
- pytest: AttributeError: NoneType in tests/x.py:42
- Fix: ensure setup() returns object. Consider adding __init__.py in tests/

Artifacts: logs, junit, repro steps
```

Docs and developer experience
- Runbooks and ADRs; local pipeline emulator; Makefile targets.
- ChatOps commands (/rerun, /promote, /rollback, /chaos on).
- One-command bootstrap for local setup and demo replay.
- Repo badges: SLSA, SBOM, CI, Coverage, Mutation.
- Three designed-to-fail PRs: API break, perf budget failure, policy deny.

Testing matrix
- Pre-merge: lint, unit, diff-only mutation, contract tests, preview deploy, smoke.
- Pre-prod: full mutation, integration, load, end-to-end, security scanning, IaC plan validation.
- Post-prod: canary verification, synthetic probes, drift detection, automated rollback test.

DR, idempotency, and retention
- Backfill re-ingest pipeline; immutable artifact storage; disaster recovery runbook.
- Weekly rollback/restore drills stored in warehouse and shown as DR SLO card; block promotion if last drill > 7 days.
- Data retention: raw logs 30 days, NDJSON 180 days, marts 400 days; row-level security with 400-day audit log retention; ingest enforces PII ban list.

Cost and sustainability
- Track per-run cost and carbon; cache savings; region; queue vs compute time.
- Enforce per-repo concurrency and cost caps; surface minutes and dollars saved in dashboard.
- Egress allowlist tests ensure package managers hit pinned mirrors; fail on unexpected domains.
- Enforce budgets: block PRs exceeding cost or CO₂e limits without explicit override.

Preview environments
- Per-PR ephemeral stack with app + database + seeded data; TTL and auto teardown on merge/close.
- PR comment shows unique URL, chaos toggle, and mutation summary for that diff.

Synthetic data generator
- Deterministic faker /tools/synthetic_runs.py emits NDJSON streams by repo/language.
- Seed dashboards and tests with /fixtures/seed.ndjson; documented in docs/data-generation.md.

Analytics deep dives
- Resilience: exclude equivalent mutants, compute control limits, label weak-tests.
- Coverage vs resilience: diff-weighted scatter plots and hotspot tables by owner.
- Flakiness: per-test flake rate with retry metadata and quarantine list.
- Policy: allowlists for action SHAs, licenses, CVE budgets, deploy-time attestations.
- Rollbacks: automated, weekly tested, audited in dashboards.
- RBAC: warehouse row-level security per team/service.

Risks and controls
- Flakiness: quarantine and publish stability index.
- Vendor lock-in: GitHub first, GitLab driver later; modules use generic events.
- Runner hermeticity: validate hosted runner isolation; fall back to self-hosted Firecracker/gVisor if necessary.
- Traffic shadowing deferred to v1.1 due to cost.

High-leverage next steps
1. Wire hermetic rootless builds with SBOM, provenance, cosign, Rekor; fail deploys on missing attestation.
2. Add API diff and perf budget PR gates; extend PR formatter with Evidence Bundle links.
3. Generate the Release Evidence Bundle and surface it in dashboards and PR artifacts.
- Schedule Rekor monitoring job and attach inclusion proofs to Evidence Bundle.
- Implement Kyverno admission policy and OCI referrer verification gates.

Minimal recruiter-ready deliverables
- Public screencast: PR -> gates -> evidence -> deploy -> auto-promote/rollback.
- Sanitized dashboards: supply chain posture, run health, DR SLOs, cost/carbon.
- Documentation: SECURITY.md, SUPPLY_CHAIN.md, DR_RUNBOOK.md, POLICIES.md, EVIDENCE_BUNDLE.md with real examples.
- Workflow YAML pinned to action SHAs with OIDC permissions.

Demo script
1. Open PR -> preview environment spins up; PR comment shows resilience delta and cache stats.
2. Inject chaos -> Autopsy posts root cause and fix.
3. Merge -> build emits SBOM and signature; NDJSON ingested.
4. GitOps promotes to dev -> smoke passes.
5. Staging runs load and security scans.
6. Prod canary at 20% -> promote or rollback with reason captured.
7. Dashboard shows trace, DORA, cost, and carbon.

Sample configs
```
mutation:
  lang: auto
  include: ["src/**"]
  tests: ["tests/**"]
  diff_only: true
  thresholds:
    score_warn: 0.7
    score_fail: 0.6
```

Agent commands
- ci-agent mutation run --targets src/ --tests tests/ --lang auto --upload
- ci-agent autopsy collect --logs '**/*.log' --junit '**/junit*.xml' --upload
- ci-agent replay --env staging --plan plan.json --apply apply.json

Scope discipline (ship v1.0 first)
- Keep: SLSA L3 path, API/perf gates, Release Evidence Bundle, OIDC-only, policy gates, DR drills, RBAC/RLS, dashboards.
- Defer to v1.1: traffic shadowing, Bazel/RBE monorepo, Backstage plugin, work-stealing scheduler, GitLab driver.

Focus decisions
- Prioritize analytics/AI-enhanced CI fused with resilience signals.
- Dedicated showcase repo (no dependency on other products).
- Next: produce data flow and chaos->recovery->Autopsy diagrams (already defined above).

Runtime enforcement upgrades
- Enforce keyless Cosign + SLSA provenance at cluster admission via Kyverno verifyImages with Sigstore bundle; require issuer/subject regex match (issuer/subject gate implemented, Kyverno policies pending).
- Store SBOM and provenance as OCI 1.1 referrers; gate deploys on their presence using registry-native discovery.
- Emit CycloneDX and SPDX SBOMs, sign and attach as referrers; verify at deploy (SPDX for license, CycloneDX for vuln workflows).
- Monitor Rekor consistency and new entries for tracked subjects; alert on missing inclusion proofs (rekor-monitor) — TODO: wire `tools/rekor_monitor.sh` into CI and Evidence Bundle.
- Standardize on SLSA v1.0 provenance predicate (in-toto); validate required fields before promotion.
- Enforce secretless CI: forbid long-lived keys in job env, require OIDC subject/issuer allowlist, verify short TTLs.
- Cross-architecture determinism checks (x86_64 vs ARM64) with base-image digests pinned via CAS; fail on ELF/PT_GNU_BUILD_ID drift.
- Enforce VEX-aware gating ✅ (implemented): generate CycloneDX VEX statements from `fixtures/supply_chain/vex_exemptions.json` via `tools/generate_vex.py`, push them with the SBOM/referrers, scan the CycloneDX SBOM with Grype inside the policy-gates job, normalize the findings via `tools/build_vuln_input.py`, and require SBOM/VEX policy approval (next: source signed VEX referrers from the real vuln-management system).
- Establish schema registry with semver, compatibility tests, ownership ADRs, and deprecation windows for every event topic.
- Autopsy governance: record LLM model ID/digest/prompts/temperature; prohibit LLM-only gate decisions.
- Runner isolation: ephemeral self-hosted runners with egress policy, read-only workspaces, cache restore provenance verification.
- Cost/carbon enforcement: turn telemetry into budgets that gate PRs exceeding limits.
- Disaster recovery proof: quarterly artifact recall drill using provenance/SBOM/pinned mirrors; publish diff in Evidence Bundle.
- Scheduler upgrades: pre-warm runners based on predictions, deterministic fallback when MAPE > threshold, publish fairness metrics per team.
- GitHub organization controls: Rulesets enforcing required status checks, signed commits/tags, CODEOWNERS approval on critical paths, conversation resolution, no force-push, protected releases (only builder identity signs tags).
- Admission policy trio: per-environment image digest allowlists, required provenance, required SBOM referrers; deny deploy on missing attestations.
- Base-image SLO: block builds when base image gains critical CVE without VEX “not exploitable”.
- Builder hardening: ephemeral isolated builders with OIDC identity, provenance capturing parameters, pinned source URI, reproducible toolchain versions, environment hash recorded in provenance and Evidence Bundle.
- Determinism hardening: cross-arch and cross-time reruns (24h), fail on BUILD_ID/JAR Implementation-Version drift even if SHA identical.
- Language-specific reproducibility hooks: PYTHONHASHSEED=0 + pip --require-hashes; Go -trimpath + GOMODSUMDB=on; Java reproducible builds plugin; Node npm ci with lockfile v3; Rust --remap-path-prefix.
- Cache integrity: sign cache manifests, verify signature/BLAKE3 before restore, quarantine on failure, emit cache_quarantine events.
- Secretless CI gate: deny jobs with long-lived keys/plain env secrets; allow only OIDC-federated tokens with issuer/subject allowlist and short TTL.
- Egress policy: default deny; mirrors/registries allowlisted and tested in CI.
- SBOM diff gate: fail on new high-risk dependencies unless VEX says “not affected”; risk score = max(CVSS, EPSS percentile).
- Static/dynamic analysis normalization: ingest SAST/DAST/SCA as SARIF; gate on findings-per-KLoC, newly introduced highs.
- Data governance: schema registry ownership, semver bumps, compatibility tests, MERGE-based exactly-once ingest (run_id + load_id), PII DLP scan pre-ingest.
- DR & compliance: WORM buckets with cross-region replication; quarterly artifact recall; SOC2/ISO27001 control mapping appendix.
- Canary analysis: Kayenta-style weighted score (error rate, p95 latency, saturation) with guardrail thresholds; record decision and query links.

Additional gates and jobs
- Implement referrer presence gate (SBOM + provenance) prior to deploy.
- Enforce Kyverno admission policy requiring valid attestations.
- Schema compatibility gate backed by registry-based schema registry.
- Schedule Rekor monitor job; attach inclusion proofs to Evidence Bundle.
- Admission attestations gate denies issuer/subject mismatch or missing Rekor inclusion proof.
- Determinism gate fails cross-arch or BUILD_ID drift.
- Secretless gate fails on non-OIDC credentials in env/logs.
- SBOM diff gate blocks unmitigated high-risk dependencies.

Immediate commit objectives
1. OCI referrers + signing: push CycloneDX/SPDX SBOMs and SLSA provenance as signed referrers; verify in CI.
2. Cluster admission policy: ship Kyverno verifyImages deny-by-default sample with keyless issuer/subject regex and required provenance.
3. Rekor monitoring job: run rekor-monitor with checkpoints; alert on gaps; store proofs in evidence.
- 7-day cut: (1) enforce GitHub Rulesets/branch protections, (2) add referrer-presence gate + provenance admission, (3) wire language reproducibility flags, (4) enable SBOM diff + VEX gate, (5) stand up schema registry CI check, (6) enable WORM + replication, (7) add determinism/Rekor monitors to Evidence Bundle.

Must-fix nits
- Preview env RBAC: read-only prod registries for deployers; write credentials scoped to CI builds only with separate principals.
- Time source: record monotonic clock, timezone, kernel/containerd digests in provenance; alert on >100 ms skew alongside SOURCE_DATE_EPOCH.
- Data quality: expand dbt tests to rowcount deltas, freshness SLA, null-rate thresholds per mart; fail ingest on breach.
- Canary evidence: store metric queries and window parameters as artifacts; hash references within Evidence Bundle.
- Orchestrator backpressure: enforce per-repo concurrency, queue SLOs, fairness budgets; deny bursts violating caps.
- Artifact ACLs: WORM plus object-level least privilege IAM and short-lived signed URLs for logs/artifacts.
- SARIF hygiene: deduplicate findings across tools/versions; suppression requires justification and expires in 30 days.
- Postmortems: `/docs/POSTMORTEM.md` template referencing Autopsy IDs, Rekor proofs, gate decisions; mandatory after rollbacks.

v1.0 exit checklist
- Keyless Cosign, SLSA v1.0 provenance, OCI referrers present and verified at admission.
- Kyverno policies enforce issuer/subject regex, provenance required, SBOM referrers required, deny-by-default.
- Determinism gates: cross-arch and cross-time; fail on ELF BUILD_ID/JAR version drift.
- Secretless CI: OIDC-only credentials; non-OIDC secrets blocked; egress default-deny with allowlisted mirrors.
- SBOM + VEX gate blocks new high-risk dependencies unless marked "not affected".
- Cache Sentinel signs/verifies manifests; quarantine path emits `cache_quarantine` events.
- Schema registry check passes; NDJSON v1.2 valid; compat view tests green.
- Ingest freshness P95 ≤ 5 min; dashboard query P95 ≤ 10 s on 30-day window.
- DR drill evidence stored in warehouse; RPO ≤ 60 s, RTO ≤ 300 s.
- Canary scorer decision and inputs embedded in Evidence Bundle.
- GitHub Rulesets enforced: signed commits/tags, required checks, CODEOWNERS on critical paths, no force-push.
- Cost/CO₂e budgets enforced with override workflow and audit trail.

Final three PRs
1. `supply-chain-enforce/`: Kyverno policies + OCI referrer gate + Rekor inclusion proof upload integrated with release job.
2. `determinism-and-repro/`: cross-arch/time checks, language-specific reproducible flags, tools/determinism_check.sh updates, Evidence Bundle additions.
3. `data-quality-and-dr/`: dbt freshness/rowcount/null-rate tests, WORM + replication documentation, DR recall script with artifact diff.
