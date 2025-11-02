# CI/CD Hub Multi-Repository Service Architecture Analysis

## Executive Summary

The CI/CD hub is now a **single-hub, multi-repo pilot**: repositories are discovered dynamically from `config/repositories.yaml`, per-repo HTTP allowlists are applied via proxy environment variables, and per-repo test timeouts are honoured. However, the platform still lacks several pieces required for true multi-tenant operation—namely secret scoping, fair scheduling, strong runtime isolation, and cost tracking.

**Current capability (v1.0.10)**: Matrix-based execution with dynamic repo configuration, proxy-based egress allowlists, per-repo test timeouts, shared telemetry and evidence bundles.
**Missing for v1.0**: Per-repo secrets, rate limiting, hard resource isolation, cross-repo dependency management, hierarchical config inheritance, cost allocation, GitOps orchestration.

---

## 1. MULTI-TENANCY FEATURES

### 1.1 Repo Isolation Mechanisms

**Status**: ⚠️ PARTIAL - Logical separation with proxy egress, but shared runtime

#### What Exists:
- **Matrix-based segmentation** driven by `scripts/load_repository_matrix.py` using `config/repositories.yaml`
  - Each repo checked out under `project/${{ matrix.path }}`
  - Per-repo cache keys scoped by `matrix.name`
  - Proxy-based egress allowlists exported per repo (`.github/workflows/release.yml:130-156`)
  - Per-repo test timeouts enforced with `timeout "${TIMEOUT_SECONDS}s"` (`release.yml:283-310`)

#### What's Missing:
- **No container-level or process isolation** – all matrix entries share the same GitHub-hosted runner
- **Proxy enforcement covers only HTTP-aware tooling** – raw sockets can bypass the allowlist
- **Shared credentials** – `GITHUB_TOKEN` remains common across all repos (no per-repo secret scoping)
- **No sandbox/firecracker** – isolation requires self-hosted runners (Phase 2 roadmap)

### 1.2 Per-Repo Configuration Capabilities

**Status**: ⚠️ PARTIAL - Dynamic registry with limited overrides

#### What Exists:
- **Dynamic registry** (`config/repositories.yaml`) feeding the workflow matrix
- **Configurable knobs per repo**:
  - `path`, `package` flag for build/install behavior
  - `build_timeout` parsed into `matrix.timeout_minutes`
  - `allowed_egress` merged into per-repo proxy allowlists

#### What's Missing:
- **Per-repo secrets/vars mapping** – still pending (shared `GITHUB_TOKEN`)
- **Per-repo environment selection/branch rules** – single release path
- **Inheritance/defaults** – no schema/version negotiation or templating
- **Schema enforcement for repositories.yaml** – input validation TODO

### 1.3 Tenant/Repo Segregation in Caching, Artifacts

**Status**: ⚠️ PARTIAL - Naming-based only

#### Cache Segregation:
- **Keyed by repo owner + runner OS + repo-specific paths**:
  ```yaml
  key: ${{ github.repository_owner }}-${{ runner.os }}-pip-${{ hashFiles('project/**/requirements*.txt', 'project/**/pyproject.toml') }}
  ```
  - Fork caches isolated via `github.repository_owner` prefix
  - Per-repo path included in hash
  - ✅ Cache manifests signed per-repo with cosign

#### Missing:
- **No cache quotas per repo** - All repos share 5GB GitHub Actions cache
- **No cache eviction policy** - LRU/TTL not configurable per repo
- **No cache deduplication across repos** - If two repos need numpy, stored twice
- **No cross-repo cache sharing** - Can't declare "repo X may use repo Y's cache"
- **No cache tampering audit trail** - Only per-job, not per-repo-across-time

#### Artifact Segregation:
- **Per-job named uploads** (`artifacts/logs/${{ matrix.name }}.log`):
  ```yaml
  name: project-test-logs-${{ matrix.name }}-${{ github.run_attempt }}
  name: cache-manifest-${{ matrix.name }}
  name: job-telemetry-${{ matrix.name }}-${{ github.run_attempt }}
  ```
  - ✅ Artifacts namespace-keyed by repo name
  - ✅ Per-repo telemetry emitted separately

#### Missing:
- **No per-repo retention controls** - GitHub default 90-day retention applies to all
- **No artifact encryption** - Artifacts world-readable in GitHub
- **No artifact signing chain** - Only final release artifacts signed
- **No quarantine mechanism for cross-repo artifacts** - If repo X's artifact is poisoned, only affects X, but no isolation boundary
- **No artifact cost tracking per repo**

### 1.4 Repo-Level Permissions/RBAC

**Status**: ❌ ABSENT - All-or-nothing GitHub token

#### What Exists:
- **Workflow-level permissions**:
  ```yaml
  permissions:
    contents: read
    id-token: write  # For keyless signing
    actions: read
  ```
  - Least-privilege OIDC-only (no PATs)
  - Shared GITHUB_TOKEN for all matrix jobs

#### Missing:
- **No per-repo access control** - Same token reads all repos
- **No role-based approval gates** - All maintainers can release all repos
- **No tenant admin/viewer separation** - No RBAC model
- **No cross-org multi-tenancy** - Only single org supported
- **No repo-specific secrets access list** - All repos can request all secrets (if exposed)
- **No audit log per-repo** - Only GitHub's audit log, not hub's

---

## 2. SCALABILITY PATTERNS

### 2.1 Queue Management, Rate Limiting

**Status**: ⚠️ BASIC - Workflow-level only

#### What Exists:
- **Concurrency budgets** (`config/runner-isolation.yaml`):
  ```yaml
  workflows:
    release.yml:
      max_in_progress: 1
  workflows:
    project-tests:
      max_parallel: 2
  ```
  - `max_in_progress: 1` - Only one release run at a time
  - `max_parallel: 2` - Only 2 matrix jobs in parallel
  - Enforced via GitHub API query in `scripts/enforce_concurrency_budget.py`

#### What's Missing:
- **No per-repo concurrency budget** - All repos share `max_parallel: 2`
- **No queue length monitoring** - No backpressure metrics
- **No fair queuing** - First-come-first-served (no priority queue)
- **No queue denial telemetry** - Denials not recorded for SLO tracking (mentioned in plan.md as "near-term")
- **No rate limiting on GitHub API calls** - Could hit rate limits during high load
- **No sharding by repo** - Can't split heavy repos to separate runners
- **No adaptive concurrency** - Fixed limits regardless of runner utilization
- **No pub/sub or job queue** - Tight coupling to GitHub Actions

**Gap**: Looks like `token-bucket` throttling mentioned in plan.md line 51 is not implemented

### 2.2 Concurrency Controls Across Repos

**Status**: ⚠️ BASIC - Global controls only

#### What Exists:
- **Release workflow concurrency**:
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```
  - Cancel in-progress run when new tag pushed
  - Per-workflow grouping

#### Missing:
- **No per-repo queue depth limit** - If repo X submits 100 tags, all queue globally
- **No repo starvation prevention** - Repo X could starve repo Y if repo X tags rapidly
- **No priority lanes** - Can't say "critical repos get 50% of runners"
- **No fair sharding** - Can't say "repo X gets 1 runner, repo Y gets 1 runner"
- **No backoff retry logic** - On failure, workflow retries immediately
- **No circuit breaker** - If repo X is poisoned, doesn't cascade
- **No graceful degradation** - All-or-nothing: if release fails, entire hub blocks

### 2.3 Resource Allocation/Budgeting Per Repo

**Status**: ❌ ABSENT

#### Missing:
- **No CPU/memory quotas** - All repos on ubuntu-22.04 (shared 4 CPU, 16 GB)
- **No runner size selection per repo** - All use same runner type
- **No cost budgets** - No per-repo cost tracking or limits
- **No spot vs. on-demand per repo** - All use GitHub-hosted (no spot option)
- **No artifact size limits** - All repos can upload unlimited artifacts
- **No build timeout per repo** - Global 6-hour limit
- **No caching quota** - All repos share 5 GB cache

**Gap**: Predictive scheduler (`tools/predictive_scheduler.py`) recommends runner sizes but:
- Not integrated into release workflow
- No enforcement of recommendations
- No resource reservation
- No cost impact calculation

### 2.4 Fairness Mechanisms

**Status**: ❌ ABSENT

#### Missing:
- **No token bucket** - Plan mentions "runner fairness: token-bucket throttling" (plan.md:51) but not implemented
- **No weighted queue** - Can't assign weights to repos
- **No SLO enforcement** - No "repo X must finish in 10min" with enforcement
- **No starvation detection** - Can't alert if repo Y hasn't run in 7 days
- **No throttle metrics** - No `queue_denials` metric mentioned in plan.md:51
- **No age-based reordering** - Older queued jobs don't get priority
- **No fair scheduling algorithm** - No round-robin, LCM, or deficit round-robin

---

## 3. SERVICE MESH CAPABILITIES

### 3.1 API Gateway Patterns

**Status**: ❌ ABSENT - No API gateway

#### What Exists:
- **GitHub Actions as orchestrator** - Uses GitHub's API for workflow dispatch
- **HTTPS-only communication** - Enforced in Python scripts

#### Missing:
- **No HTTP API gateway** - No REST endpoint to trigger releases (only GitHub webhook)
- **No authentication layer** - No token/OAuth for external consumers
- **No rate limiting at gateway** - No request throttling layer
- **No request validation** - No schema validation of inputs
- **No circuit breaker** - No graceful fallback if downstream service fails
- **No request routing** - No dynamic routing of repos to different backends
- **No observability middleware** - No gateway-level metrics
- **No timeout enforcement** - No gateway-level timeout override

**Gap**: Plan mentions "Published reusable `workflow_call` pipelines" but:
- Only as GitHub composite actions, not as API
- No centralized entry point
- No rate limiting on workflow_call invocations

### 3.2 Service Discovery Mechanisms

**Status**: 🟡 PARTIAL - YAML-backed registry, no control plane

#### What Exists:
- **Git-based registry** (`config/repositories.yaml`)
  - Repos enabled/disabled without editing workflows
  - Settings injected into matrix via `scripts/load_repository_matrix.py`

#### Missing:
- **No dynamic service discovery** beyond Git (no Consul/Eureka/etcd)
- **No health checks** or auto-deregistration when repos fail repeatedly
- **No query API** – consumers must read YAML directly
- **No weighted routing/load balancing** for heavy repos
- **No service mesh control plane** or policy-aware discovery

### 3.3 Inter-Repo Dependency Handling

**Status**: ❌ ABSENT

#### Missing:
- **No dependency DAG** - No way to declare "repo X depends on repo Y's artifacts"
- **No dependency ordering** - All repos tested in parallel (matrix), not sequentially
- **No artifact cascading** - If repo X produces artifact A and repo Y needs A, no automatic propagation
- **No cross-repo testing** - Can't test "repo Y against repo X's latest release"
- **No shared state management** - No way to coordinate state across repos (e.g., "release only if all repos passed")
- **No orchestration workflow** - Monolithic release.yml, not choreography

**Example Gap**: 
```
Repo: vector-space
  depends_on: 
    - learn-caesar-cipher (latest release)
But currently: vector-space can't specify this dependency
```

### 3.4 Centralized Configuration Management

**Status**: ⚠️ MINIMAL - GitOps-style config without validation

#### What Exists:
- **Checked-in configs**:
  - `config/repositories.yaml` – dynamic registry + per-repo knobs
  - `config/runner-isolation.yaml` – workflow-level concurrency budgets
  - `.github/workflows/*.yml` – orchestration definitions
  - `schema/pipeline_run.v1.2.json` – telemetry schema

#### Missing:
- **No config server or API** – updates require Git PRs
- **No schema validation** for `repositories.yaml` (future enhancement)
- **No configuration inheritance/templating**
- **No automated rollback** on config failure
- **No feature flags / partial rollouts**
- **No overrides per environment** - Same config for all environments (prod/staging/dev)

**Gaps**:
- No way to say "for repo X, use runner ubuntu-latest instead of ubuntu-22.04"
- No way to say "repo X uses PostgreSQL, repo Y uses MySQL" (test config per repo)
- No way to override secrets per repo
- Plan mentions "Copier/Cookiecutter" for downstream sync but not implemented

---

## 4. OBSERVABILITY FOR MULTI-REPO

### 4.1 Per-Repo Metrics/Dashboards

**Status**: ⚠️ PARTIAL - Telemetry collection exists, dashboards TBD

#### What Exists:
- **Per-repo telemetry recording** (`scripts/record_job_telemetry.py`):
  ```python
  record: {
    "job": args.job_name,  # e.g., "learn-caesar-cipher"
    "duration_ms": args.duration_ms,
    "queue_ms": args.queue_ms,
    "status": args.status,
    "cache_hit": args.cache_hit,
    "runner_type": args.runner_type,
    "runner_size": args.runner_size,
  }
  ```
  - NDJSON telemetry appended to artifacts
  - Job name includes repo name
  - Duration, cache hit, status tracked

- **Per-repo logs uploaded**:
  ```yaml
  name: project-test-logs-${{ matrix.name }}-${{ github.run_attempt }}
  name: job-telemetry-${{ matrix.name }}-${{ github.run_attempt }}
  ```

#### Missing:
- **No time-series DB** - Telemetry stored as NDJSON artifacts, not queryable DB
- **No dashboards** - plan.md mentions dashboards/ but empty
- **No visualization** - No Grafana, DataDog, Prometheus
- **No alerts per repo** - No "alert if repo X fails 3 times in a row"
- **No SLO dashboards** - No "repo X meets 99.9% uptime SLO"
- **No cost per repo** - `carbon_g_co2e` and `energy_kwh` in schema but not aggregated per repo
- **No custom metrics** - Only job-level, not business metrics (e.g., "deployments per day per repo")

**Data Pipeline Exists but Incomplete**:
- ✅ Telemetry emitted (scripts/emit_pipeline_run.py)
- ✅ NDJSON schema defined (schema/pipeline_run.v1.2.json)
- ✅ dbt staging/marts models written (models/staging, models/marts)
- ❌ No BigQuery integration (vars: CI_INTEL_BQ_PROJECT, CI_INTEL_BQ_DATASET not configured)
- ❌ Dashboards not implemented

### 4.2 Cross-Repo Analytics

**Status**: ⚠️ PARTIAL - Schema supports it, implementation TBD

#### What Exists:
- **Unified schema for all repos**:
  ```json
  {
    "repo": "string",  // "owner/repo"
    "jobs": [...],     // all jobs in run
    "tests": {...}     // aggregate test counts
  }
  ```
  - Single schema version (v1.2) for all repos
  - All pipeline runs stored in same NDJSON

#### Missing:
- **No cross-repo aggregation** - No SQL to say "compare success rate across all repos"
- **No benchmarking** - No "repo X is 2x slower than repo Y"
- **No correlation analysis** - Can't detect "when repo X fails, repo Y also fails 80% of the time"
- **No outlier detection** - No "repo X duration is 3 sigma above mean"
- **No trend analysis** - No "repo X test count increasing 2% per week"
- **No root cause analysis** - No automated anomaly investigation
- **No variance analysis** - No explanation of why repo X is slower

### 4.3 Centralized Logging with Repo Context

**Status**: ⚠️ PARTIAL - Logs captured, centralization TBD

#### What Exists:
- **Per-repo logs uploaded**:
  ```
  artifacts/logs/${{ matrix.name }}.log
  artifacts/logs/${{ matrix.name }}.duration
  artifacts/logs/${{ matrix.name }}.changed
  ```
  - Structured NDJSON for job telemetry
  - Duration and changed file count recorded

#### Missing:
- **No log aggregation** - Logs stored in GitHub artifacts, not ELK/Splunk/CloudLogging
- **No log parsing** - Raw logs not structured for search
- **No log retention policy** - GitHub artifacts kept indefinitely
- **No log encryption** - Logs world-readable in GitHub
- **No trace context** - No `traceparent` or OpenTelemetry trace ID propagation (mentioned in plan.md but not implemented)
- **No full-text search** - Can't search logs across repos
- **No log sampling** - All logs kept (cost inefficient at scale)
- **No automated incident correlation** - Can't link logs to incidents

### 4.4 Cost Allocation Per Repo

**Status**: ⚠️ MINIMAL - Schema supports it, not implemented

#### What Exists:
- **Schema fields for cost tracking**:
  ```json
  {
    "carbon_g_co2e": "number",
    "energy": { "kwh": "number" },
    "cost": "..."  // present in schema
  }
  ```
  - Fields in pipeline_run.v1.2.json
  - `emit_pipeline_run.py` accepts `--carbon-g-co2e` and `--energy-kwh`

#### Missing:
- **No cost calculation** - No script to calculate cost from duration/runner size
- **No cost per repo aggregation** - No "repo X cost $500/month"
- **No cost forecasting** - No trend analysis or budget alerts
- **No chargeback model** - No per-team billing
- **No cost optimization recommendations** - No automated "repo X could save 20% by using spot runners"
- **No cost vs. SLO trade-off** - Can't make informed decisions about runner size
- **No RI/commitment analysis** - No recommendation to buy GitHub Actions compute RI

---

## 5. DEPLOYMENT ORCHESTRATION

### 5.1 Deployment Ordering/Dependencies

**Status**: ❌ ABSENT - All repos in parallel

#### Current State:
- All repos tested in **parallel** via GitHub matrix:
  ```yaml
  strategy:
    fail-fast: false
    max-parallel: 2
    matrix:
      include:
        - learn-caesar-cipher
        - vector-space
  ```

#### Missing:
- **No sequential deployment** - Can't deploy repo A before repo B
- **No dependency DAG** - No way to declare "vector-space depends on learn-caesar-cipher"
- **No blocking stages** - All stages run in parallel
- **No approval gates between repos** - No "stop and wait for approval before deploying repo Y"
- **No resource coordination** - If both repos need scarce resource, not managed
- **No failure cascading** - One repo's failure doesn't stop the other

**Example Gap**:
```
Desired: vector-space needs learn-caesar-cipher v1.2.5
Current: No way to express this; vector-space tests against whatever is already released
```

### 5.2 Rollout Strategies Across Repos

**Status**: ⚠️ PARTIAL - Single strategy only

#### What Exists:
- **Canary decision capture** (`scripts/capture_canary_decision.py`):
  ```python
  {
    "decision": "promote|rollback|hold",
    "window": { "start": "...", "end": "..." },
    "metrics_uri": "...",
  }
  ```
  - Can record promote/rollback decisions
  - Window-based (not percentage-based)
  - Embedded in pipeline_run.v1.2

#### Missing:
- **No multi-repo canary** - Canary applied to single release artifact, not across repos
- **No progressive rollout** - Can't say "deploy to 10% of repos first, then 90%"
- **No blue-green per repo** - Schema supports it (strategy: "blue-green") but no orchestration
- **No A/B testing framework** - No way to split repos 50/50 and measure
- **No traffic shifting** - No gradual % traffic switch
- **No automatic rollback threshold** - Rollback decision is manual, not automated
- **No feature flags for repos** - Can't enable feature only for repo X
- **No canary metrics aggregation** - Each repo would need separate decision

### 5.3 Environment Promotion Across Repos

**Status**: ⚠️ MINIMAL - Schema supports it, no orchestration

#### What Exists:
- **Environment field in schema**:
  ```json
  "environment": "enum: preview|dev|staging|prod|test"
  ```
  - Single environment per run
  - Can emit telemetry with environment

- **Deployment ID tracking**:
  ```json
  "deployment_id": "string"
  ```

#### Missing:
- **No promotion workflow** - No "deploy to dev, then staging, then prod"
- **No approval gates** - No manual promotion from staging to prod
- **No environment-specific configs** - Same config for prod and staging
- **No env-specific secrets** - All repos use same secrets
- **No automated env promotion** - Must manually trigger next stage
- **No env promotion queue** - If staging saturated, no backpressure
- **No environment rollback** - No automated rollback from prod to staging
- **No environment isolation** - No separate GitHub environments

**Gap**: release.yml has hardcoded `environment: staging` in emit_pipeline_run.py, no prod promotion path

### 5.4 GitOps Patterns

**Status**: ❌ ABSENT - Workflow dispatch and GitHub Actions only

#### Missing:
- **No Flux** - No declarative desired state in git
- **No ArgoCD** - No Application resources for repos
- **No GitOps manifests** - Repos defined in hardcoded YAML, not git-driven
- **No pull-based sync** - Webhook-driven, not poll-based
- **No image update automation** - Renovate/Dependabot mentioned but not integrated
- **No promotion commit** - No commits to release branch when promoting
- **No rollback via git revert** - Rollback is manual, not via git
- **No monorepo orchestration** - No Kustomize, Helm, or Kpt

---

## 6. CONFIGURATION MANAGEMENT

### 6.1 Hierarchical Config (Org → Repo)

**Status**: ❌ ABSENT - Flat structure only

#### What Exists:
- **Org-level config files**:
  - `config/repositories.yaml` - repo list
  - `config/runner-isolation.yaml` - concurrency limits
  - `.github/workflows/*.yml` - workflow definitions

#### Missing:
- **No org defaults** - Can't define "all repos use ubuntu-latest by default"
- **No repo overrides** - Can't say "repo X uses ubuntu-22.04 instead"
- **No layering** - No org → team → repo hierarchy
- **No inheritance chain** - Each repo repeats full config
- **No partial overrides** - Must override entire section, not single field
- **No schema inheritance** - No way to extend base schema per repo

**Example Gap**:
```yaml
# Desired:
org_defaults:
  runner: ubuntu-latest
  timeout: 6h
teams:
  platform:
    runner: ubuntu-22.04
repos:
  vector-space:
    timeout: 12h

# Current:
hardcoded per workflow
```

### 6.2 Configuration Inheritance

**Status**: ❌ ABSENT

#### Missing:
- **No base configs** - No templates to inherit from
- **No mixin support** - Can't compose configs from multiple files
- **No vars interpolation** - Can't reference other config values
- **No conditional includes** - Can't conditionally include sections
- **No schema validation** - No JSON Schema validation of config
- **No version compatibility** - No detection of incompatible config versions

### 6.3 Override Mechanisms

**Status**: ⚠️ MINIMAL - ENV vars only

#### What Exists:
- **GitHub Actions env vars**:
  ```yaml
  env:
    INGEST_PROJECT: ${{ vars.CI_INTEL_BQ_PROJECT || secrets.CI_INTEL_BQ_PROJECT || '' }}
  ```
  - Can override via secrets or vars
  - Fallback to empty string if not set

#### Missing:
- **No runtime overrides** - Can't override at job start time
- **No config server integration** - Can't fetch config from remote server
- **No feature flag override** - Can't toggle features at runtime
- **No secrets rotation without redeployment** - Secrets are static in GitHub
- **No per-repo secret mapping** - Can't say "repo X uses secret Y, repo Z uses secret W"

### 6.4 Templating Capabilities

**Status**: ⚠️ MINIMAL - GitHub Actions syntax only

#### What Exists:
- **GitHub Actions templating**:
  ```yaml
  strategy:
    matrix:
      include:
        - name: ${{ matrix.name }}
  ```
  - Context interpolation (github.*, env.*, matrix.*)
  - Conditionals (if:)

#### Missing:
- **No Jinja2/Mustache** - No template language
- **No variable substitution loops** - Can't loop over repos and generate config
- **No schema generation** - Can't generate TypeScript types from YAML
- **No config as code** - No way to generate configs programmatically
- **No DSL** - No domain-specific language for multi-repo config

---

## SUMMARY: GAPS FOR PRODUCTION MULTI-REPO SERVICE

| Category | Feature | Status | Impact | Priority |
|----------|---------|--------|--------|----------|
| **Tenancy** | Container isolation | ❌ | No process/network boundaries | CRITICAL |
| **Tenancy** | Secrets per-repo | ❌ | Token sharing risk | HIGH |
| **Tenancy** | Dynamic repo registration | ❌ | Must edit code to add repos | HIGH |
| **Tenancy** | RBAC per-repo | ❌ | All maintainers can release all repos | HIGH |
| **Scalability** | Per-repo queue budgets | ❌ | Starvation risk | MEDIUM |
| **Scalability** | Fair scheduling | ❌ | No SLO enforcement | MEDIUM |
| **Scalability** | Resource quotas | ❌ | No cost limits | MEDIUM |
| **Scalability** | Rate limiting | ❌ | Can exhaust GitHub API | MEDIUM |
| **Service Mesh** | API gateway | ❌ | Tightly coupled to GHA | HIGH |
| **Service Mesh** | Service discovery | ⚠️ | Static only | MEDIUM |
| **Service Mesh** | Dependency DAG | ❌ | No orchestration | MEDIUM |
| **Service Mesh** | Config server | ❌ | All configs hardcoded | HIGH |
| **Observability** | Dashboards | ❌ | No visibility | MEDIUM |
| **Observability** | Cost allocation | ❌ | No chargeback | LOW |
| **Observability** | Log aggregation | ❌ | Logs in GitHub artifacts | LOW |
| **Observability** | Cross-repo analytics | ❌ | No correlation | MEDIUM |
| **Deployment** | Dependency ordering | ❌ | All parallel, no DAG | MEDIUM |
| **Deployment** | Progressive rollout | ❌ | All-or-nothing | MEDIUM |
| **Deployment** | GitOps | ❌ | Imperative only | MEDIUM |
| **Deployment** | Environment promotion | ⚠️ | Manual only | MEDIUM |
| **Config** | Hierarchical config | ❌ | Flat YAML only | MEDIUM |
| **Config** | Config inheritance | ❌ | Copy-paste configs | MEDIUM |
| **Config** | Per-repo overrides | ❌ | Can't customize per repo | MEDIUM |
| **Config** | Templating DSL | ❌ | No code generation | LOW |

---

## RECOMMENDATIONS

### ALIGNED WITH CURRENT PLAN.MD (Production-Critical)

These items are already in plan.md and should be prioritized:

#### Phase 1: Security & Isolation (Weeks 1-2) - IN PLAN
1. **Fix critical security vulnerabilities** (plan.md:36-38, issues.md:41-105)
2. **Per-repo secrets via OIDC** - Already planned in plan.md:107-109
3. **Token-bucket rate limiting** - Mentioned in plan.md:51, 111-114
4. **Optional Firecracker isolation** - Stretch goal in plan.md:1788-1792

#### Phase 2: Observability (Weeks 3-4) - IN PLAN
1. **Complete BigQuery pipeline** - Variables empty, needs wiring (plan.md:121-124)
2. **Per-repo telemetry** - Schema supports it, dashboards missing
3. **Cost/carbon tracking** - Already in plan.md:1658, 1768

#### Phase 3: Fair Scheduling (Weeks 5-6) - IN PLAN
1. **Runner fairness budgets** - plan.md:51, 105-107
2. **Concurrency enforcement** - Partial implementation exists
3. **Queue depth monitoring** - Telemetry schema ready

### FUTURE ENHANCEMENTS (Not in Current Plan)

These are valuable but go beyond the current plan.md scope:

#### Optional: Service Mesh Patterns (Post-v1.0)
1. **API gateway** - Not mentioned in plan.md, could be future enhancement
2. **Config server** - Would require architecture change
3. **Service registry** - Dynamic registration not in current scope

#### Optional: Advanced Orchestration (Post-v1.0)
1. **GitOps/ArgoCD** - Not in plan.md, imperative model currently used
2. **Dependency DAG** - Could extend matrix pattern
3. **Progressive rollout** - Canary exists but not multi-repo

#### Optional: Hierarchical Configuration (Post-v1.0)
1. **Config inheritance** - Would be major enhancement
2. **Dynamic templating** - Not in current architecture

---

## FILES REQUIRING CHANGES

**Core Multi-Tenancy**:
- `.github/workflows/release.yml` - Add per-repo isolation, secrets mapping, resource limits
- `config/repositories.yaml` - Add schema for per-repo config overrides
- `scripts/enforce_concurrency_budget.py` - Implement token-bucket fairness

**Service Mesh**:
- New: `tools/config_server.py` - Config server client
- New: `tools/repo_registry.py` - Dynamic repo registration
- New: `services/api_gateway.py` - HTTP API gateway
- `scripts/load_repository_matrix.py` - Extend to support remote/validated config sources

**Observability**:
- `models/marts/repo_analytics.sql` - New mart for cross-repo analytics
- New: `dashboards/repo_health.json` - Grafana dashboard
- `scripts/record_job_telemetry.py` - Add cost calculation

**Deployment Orchestration**:
- New: `tools/dependency_dag.py` - Topological sort of repos
- New: `.github/workflows/orchestrate.yml` - Multi-stage orchestration
- `scripts/capture_canary_decision.py` - Extend to multi-repo

**Configuration Management**:
- New: `config/schema.json` - JSON Schema for hierarchical config
- New: `tools/config_template.py` - Config templating engine
- `Makefile` - Add config validation targets

---

## CONCLUSION

The hub is **not yet production-grade for multi-repo enterprise use**. It successfully orchestrates evidence collection across repos but lacks:

1. **Isolation boundaries** (containers, networks, secrets)
2. **Fair scheduling** (queue depth limits, SLO enforcement, rate limiting)
3. **Service mesh patterns** (gateway, discovery, orchestration)
4. **Observability infrastructure** (dashboards, cost allocation, alerting)
5. **Deployment orchestration** (GitOps, progressive rollout, promotion gates)
6. **Configuration management** (hierarchy, inheritance, per-repo overrides)

Recommend **2-month sprint** (10 weeks) to reach true multi-repo SaaS readiness, starting with isolation & fair scheduling (blocking production use), then service mesh foundation, then observability and orchestration.
