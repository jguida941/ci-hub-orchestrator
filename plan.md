CI Intelligence Hub -- Production-Grade CI/CD Architecture

Executive thesis
Build a CI/CD platform that quantifies test effectiveness, explains failures, enforces supply-chain trust, proves determinism, injects controlled faults, and turns pipeline signals into actionable analytics. Align to SLSA L3, DR objectives (RPO/RTO), DORA metrics, and full traceability.

Primary outcomes

- Trust: attested, signed, reproducible builds with policy gates.

- Reliability: resilient pipelines that self-diagnose and recover.

- Insight: first-class metrics, lineage, and executive scorecards.

- Efficiency: predictive scheduling, cache integrity, cost/carbon tracking.

Needs Update – Gap Tracker
--------------------------

Use this section as the running ledger of high-priority gaps and the precise controls we still need to land so work-in-progress items do not disappear in the longer narrative below.

Short Answer — Harden Now
-------------------------

Strong plan. Harden these gaps now and remove contradictions.

Priority fixes (blockers)

- [ ] Rekor gate regression coverage: document the enforced inclusion-proof gate, add failing-path admission and unit tests, and keep Evidence Bundle guidance in sync with `tools/verify_rekor_proof.py`.
- [ ] Schema vs example mismatch: align the sample payloads with `schema/pipeline_run.v1.2.json`, fix typos in the example JSON, and add the canonical example as a fixture in `schema-ci.yml` to prevent drift.
- [ ] Cache Sentinel hardening: verify signature + BLAKE3 before restore, quarantine mismatches, segregate caches for forks, and record `cache_quarantine` telemetry.
- [ ] Secretless enforcement at runtime: extend secret scanning to live job environments (`env` + `/proc/*/environ`) and fail on high-risk keys while redacting uploads.
- [ ] Egress control test: prove default-deny by curling only approved mirrors/registries, and fail when unexpected DNS/IP destinations respond.
- [ ] pull_request_target policy: forbid workflows using `pull_request_target` unless on an explicit allowlist enforced via policy.
- [ ] SLSA verification completeness: run `slsa-verifier` with `--source-uri`, `--workflow`, `--source-tag`, and pinned builder ID to assert provenance claims.
- [ ] Admission policy depth: move Kyverno/Sigstore checks to deny-by-default with issuer/subject/rekor bundle validation plus SBOM/provenance referrers per digest.

High-leverage hardening (near-term)

- [ ] Single source of truth for gap status: replace duplicated tracker text with `docs/gaps.yaml` rendered into README to avoid drift.
- [ ] Evidence Bundle attestation: sign the bundle itself as an attestation on the release digest and verify during admission.
- [ ] KEV/EPSS-aware SBOM diff gate: incorporate KEV + EPSS risk scoring, block risk ≥ 7 unless covered by signed VEX (`not_affected` with TTL).
- [ ] Registry compatibility fallback: support ORAS annotations when OCI 1.1 referrers are unavailable and gate promotion on either path.
- [ ] DR drill freshness gate: enforce weekly drills with a hard fail when `now - last_drill_ts > 7d`.
- [ ] Multi-arch parity gate: compare package inventories and SBOM component counts across manifests before promote.
- [ ] Runner fairness: implement token-bucket throttling per repo/team and emit `queue_denials` metrics once SLOs exceed thresholds.
- [ ] Policy test coverage: add `opa test` and `kyverno apply --audit-warn=false` fixtures in CI and report coverage.
- [ ] SARIF hygiene: deduplicate findings by `ruleId@tool@path@commit` and expire suppressions after 30 days with an owner.
- [ ] LLM governance: require a deterministic rule path for gates and forbid ML-only denials; continue recording model metadata.

Highest-risk gaps

- ⏳ Phase 1 — Admission control rollout: Kyverno `verifyImages`, SBOM/provenance referrer, and secretless policies have fixtures plus failing-path coverage (`scripts/test_kyverno_policies.py`, `tools/tests/test_kyverno_policy_checker.py`), but cluster enforcement remains audit-only until deny-by-default is live.
- ✅ Phase 1 — GitHub Actions supply chain: every workflow pins action SHAs and Rulesets block drifting references (`scripts/check_workflow_integrity.py`, `.github/workflows/security-lint.yml`).
- ✅ Phase 1 — Secretless pipelines: OIDC-only credentials with CI sweeps for env secrets and over-scoped `GITHUB_TOKEN` usage (`security-lint`, `policies/kyverno/secretless.yaml`).
- ✅ Phase 1 — Determinism proof: release workflow runs cross-arch/time manifest comparisons and fails on hash drift (`tools/determinism_check.sh`, `.github/workflows/release.yml`).
- ✅ Phase 2 — Schema discipline: registry metadata, fixture validation, and dbt QA run in `schema-ci.yml` (`scripts/check_schema_registry.py`, `scripts/validate_schema.py`, `scripts/run_dbt.py`).
- ✅ Phase 1 — Rekor anchoring: Evidence Bundle now captures UUID + inclusion proof and the release gate fails when proofs are missing (`tools/rekor_monitor.sh`, `tools/verify_rekor_proof.py`, `.github/workflows/release.yml`).
- ⏳ Phase 4 — Runner isolation: optional. Current posture runs entirely on GitHub-hosted `ubuntu-22.04` runners. Self-hosted Firecracker/Vault deployment remains a stretch goal for regulated environments.
- ✅ Phase 3 — Canary decision auditability: release workflow captures promote/rollback query evidence and embeds the decision in `pipeline_run.v1.2` (`scripts/capture_canary_decision.py`, `.github/workflows/release.yml`).

Performance and ops risks

- [x] Cache poisoning: cache provenance captured; manifests signed, bundles verified before restore, and quarantine telemetry emitted.
- [ ] Backpressure and fairness: workflow concurrency is enforced; orchestration telemetry/denial logic for queue bursts still needs to ship.
- ✅ Rekor anchoring: release workflow runs `tools/verify_rekor_proof.py` and fails when inclusion proofs or UUIDs are missing; keep regression tests in place to guard the gate.
- [ ] Supply-chain automation: Dependabot/Renovate configuration for weekly security updates has not been added (currently manual updates).

Current security posture

- ✅ CI guardrails: actions pinned by commit SHA, least-privilege permissions, OIDC-only auth, SBOM/VEX referrers, Cosign signing, determinism harness, and policy gates (Kyverno/OPA) are running today.
- ✅ Quality/security checks: CodeQL, Ruff/Bandit, secret scanning, mutation tests, schema-ci, and dbt build/test run on every PR/tag.
- ✅ Rekor inclusion proofs: monitor plus `tools/verify_rekor_proof.py` now fail releases when inclusion proofs are missing or malformed.
- ⏳ Automated dependency updates: Dependabot/Renovate and org-wide pinning policies still need to be configured.
- ✅ Cache restore hardening: cache manifests are signed with cosign, bundles are verified before BLAKE3 checks, mismatches are quarantined, and fork caches are isolated.
- ⏳ Runner fairness telemetry: need queue metrics + denial logic beyond the current workflow-level concurrency.
- ⏳ Runtime risk automation: canary decisions are recorded; SLO/feature-flag driven rollbacks still in the backlog.
- ⏳ Validation suite: extended reproducibility/provenance/SBOM/regression tests (see "Hardening validation backlog") are defined but not yet automated.

Blockers to ship v1.0

1. Cache integrity enforced — cache manifests are signed keylessly, bundles are verified before restore, mismatches are quarantined, and fork caches are segregated.
2. Admission policies are still audit-only — Kyverno verifyImages/referrer policies must deny on missing Cosign bundle, wrong issuer, or absent SBOM/provenance referrers.
3. SLSA verification is incomplete — provenance checks do not yet assert source repo, workflow path, source tag, or builder ID via `slsa-verifier`.
4. Secretless runtime enforcement is missing — workflows scan manifests, but we do not sweep live job environments or processes for leaked secrets.
5. Egress allowlist not enforced — CI jobs require default-deny egress with explicit allowlist (registry, GitHub, Rekor, etc.) and an audit that fails on unexpected domains.
6. `pull_request_target` remains allowed — add policy/Ruleset guardrails or an explicit allowlist.

High-leverage upgrades (next)
------------------------------

1. **Ship reusable hub workflow** (`.github/workflows/hub.yml`) with a pinned revision, documented inputs/outputs, and a conformance run proving SBOM/VEX/provenance gates fail when evidence is missing.
2. **Enforce policy gating at CI boundary** — fail PRs when SPDX/CycloneDX/SLSA referrers are absent or VEX thresholds (CVSS/EPSS) are exceeded; Kyverno enforcement follows once cluster-side wiring lands.
3. **Harden determinism** — standardize `SOURCE_DATE_EPOCH`, locale, timezone, umask; pin build toolchains/base images; fail the release when diff reports are non-empty.
4. **Immutable evidence bundle** — package, sign, and publish the bundle as an OCI artifact; record its digest in release notes and promotion approvals.
5. **DR/chaos tied to SLOs** — expand scenarios (registry outage, GH API quota, cache poisoning, flaky network), define RPO/RTO budgets, and fail the pipeline when drills exceed limits; persist drill manifests with checksums.
6. **Provenance verification gate** — assert attestation issuer/subject against allowlists and verify `subject[].digest.sha256` matches the promoted digest.
7. **Runner isolation budgets** — maintain concurrency throttles, document GH-hosted runner constraints, enforce OIDC-only secrets, and capture org Rulesets preventing PATs/unpinned actions.
8. **SBOM coverage & VEX rigor** — validate component counts/transitives, require VEX states for highs/criticals, and fail on missing or stale states.
9. **Analytics chain of custody** — sign dbt manifests, record job inputs and Git SHAs in telemetry, and treat data tests as gates.
10. **Operational guardrails** — add promotion environments with manual approvals + digest verification, release rollback playbooks, and ChatOps commands surfacing evidence digests.
11. **Two-week hardening sprint (v1.0 GH-hosted)**  
    - *PR-1 (CI boundary gates)*  
      Files: `.github/workflows/release.yml`, `.github/workflows/security-lint.yml`, `tools/slsa_verify.sh`, `tools/referrer_gate.sh`, `tools/egress_allow.sh`, `policies/workflows.rego`.  
      Steps: enforce SLSA verify, referrer presence, egress allowlist, and ban `pull_request_target`.  
    - *PR-2 (Determinism + cache integrity blockers)*  
      Files: `tools/determinism_check.sh`, `tools/cache_sentinel.py`, `.github/workflows/release.yml`.  
      Steps: enforce fixed env, dual-run diff, pre-restore cache verification/quarantine telemetry.  
    - *PR-3 (Immutable evidence bundle + schema lock)*  
      Files: `tools/pack_evidence.sh`, `.github/workflows/schema-ci.yml`, `schema/fixtures/pipeline_run.v1.2.example.ndjson`, README (evidence digest reference).  
      Steps: tar/sign/push evidence bundle to OCI, require canonical schema fixtures via AJV.  
    - *Truth table gates (all must pass)*: Rekor proof, SLSA attestation issuer/subject/workflow/tag/builder, referrer presence (SPDX/CycloneDX/in-toto), determinism diff empty, cache verification/quarantine event, telemetry schema v1.2 validated, egress allowlist enforced, `pull_request_target` banned.  
    - *Org controls*: enforce Rulesets (no unpinned actions, signed commits/tags, required checks, CODEOWNERS on `.github/**`), enable Dependabot/Renovate weekly security updates.

High-risk gaps to schedule next

- Org-wide PAT prevention and Rulesets for "no unpinned actions" across repos.
- Runner isolation posture: GitHub-hosted runners accepted for now; Firecracker/Vault profile remains optional for regulated workloads.
- Dependabot/Renovate automation with SBOM diff gates and allowlists.
- DR freshness enforcement (block release when drill > 7 days) — implementation in place; verify guard rails.
- Analytics tamper resistance (NDJSON signatures/checksums + WORM storage) still pending.

Inconsistencies to resolve in docs & code

- Rekor messaging must stay aligned with the enforced gate — document the CI step, keep failing-path tests in `tools/tests/test_verify_rekor_proof.py`, and surface regression alerts.
- Referrer gate is described as both "concrete" and "next step" — clarify the current dry-run posture and track the deny-by-default changeover.
- Cross-arch determinism is enforced; cross-time reruns remain future work — clarify and separate controls.
Concrete gates to wire immediately

Referrer presence before deploy:

```bash
oras discover "$IMAGE" --artifact-type application/spdx+json | grep -q digest
oras discover "$IMAGE" --artifact-type application/vnd.in-toto+json | grep -q digest
```

Provenance verification:

```bash
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-oidc-issuer-regex 'https://token.actions.githubusercontent.com' \
  "$IMAGE"
```

SBOM + VEX gate:

```bash
grype sbom:sbom.json -q -o json \
  | ./tools/build_vuln_input.py --vex vex.json \
  | jq -e '.policy.allow==true' >/dev/null
```

Schema CI:

```bash
jq -e 'select(.schema != "pipeline_run.v1.2") | halt_error(1)' artifacts/pipeline_run.ndjson
ajv validate -s schema/pipeline_run.v1.2.json -d artifacts/pipeline_run.ndjson
```

Secretless CI sweep:

```bash
! grep -R -E 'AWS_SECRET|_KEY=|TOKEN=' -n .github/workflows || (echo "Secret found"; exit 1)
```

Rekor proof and SLSA verification (release job):

```bash
cosign verify \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  --certificate-identity-regexp "^https://github.com/ORG/REPO/.github/workflows/release.yml@refs/tags/.*$" \
  "$IMAGE_DIGEST"

python3 tools/verify_rekor_proof.py --evidence-dir artifacts/evidence --digest "$IMAGE_DIGEST"

slsa-verifier verify-attestation \
  --artifact "$IMAGE_DIGEST" \
  --provenance "$PROVENANCE_PATH" \
  --source-uri "github.com/ORG/REPO" \
  --workflow ".github/workflows/release.yml" \
  --source-tag "$GITHUB_REF_NAME" \
  --builder-id "https://github.com/actions/runner"
```

Referrer presence with subject check:

```bash
SUBJECT=$(oras manifest fetch "$IMAGE_DIGEST" | jq -r '.subject.digest // empty')
test -z "$SUBJECT" || { echo "subject must be empty for a top-level image"; exit 1; }

oras discover "$IMAGE_DIGEST" --artifact-type application/spdx+json -o json \
  | jq -e --arg d "$IMAGE_DIGEST" 'any(.manifests[]; .subject.digest == $d)'

oras discover "$IMAGE_DIGEST" --artifact-type application/vnd.in-toto+json -o json \
  | jq -e --arg d "$IMAGE_DIGEST" 'any(.manifests[]; .subject.digest == $d)'
```

Cache Sentinel verify-before-restore:

```bash
set -euo pipefail
META="cache/meta.json"
SIG="cache/meta.sig"
KEYRING="keys/cache-pubkeys.pem"

blake3 --quiet cache/archive.tar.zst | awk '{print $1}' > cache/archive.b3
jq -e '.digest == input' "$META" < cache/archive.b3

cosign verify-blob --key "$KEYRING" --signature "$SIG" --bundle cache/meta.bundle "$META"

unzstd -dc cache/archive.tar.zst | tar -xf -
```

Quarantine on mismatch:

```bash
trap 'mv cache "cache.quarantine.$(date -u +%s)"; echo "{\"event\":\"cache_quarantine\"}" > artifacts/cache_quarantine.ndjson' ERR
```

Egress allowlist smoke test:

```bash
ALLOWED_DOMAINS='pypi.my-mirror.example.com npm.example.com ghcr.io'

for d in pypi.org registry.npmjs.org crates.io golang.org; do
  if curl -sSf --connect-timeout 2 "https://$d" >/dev/null; then
    echo "Unexpected egress to $d"; exit 1
  fi
done

for d in $ALLOWED_DOMAINS; do
  curl -sSf "https://$d" >/dev/null
done
```

Ban `pull_request_target` by policy:

```rego
package workflows

default allow = false

deny[msg] {
  input.on == "pull_request_target"
  msg := "pull_request_target is disallowed; use pull_request with minimal permissions"
}
```

DR drill freshness gate:

```bash
LAST=$(jq -r '.drill.last_success_rfc3339' artifacts/evidence/summary.json)
NOW=$(date -u +%s)
LIMIT=$((7 * 24 * 3600))
test $(( NOW - $(date -u -d "$LAST" +%s) )) -le "$LIMIT" || {
  echo "DR drill older than seven days"; exit 1;
}
```

SLO-driven auto-rollback gate:

```bash
SCORE=$(jq -r '.canary.score' artifacts/evidence/canary/decision.json)
MIN_SCORE=95
[ "$SCORE" -ge "$MIN_SCORE" ] || { echo "Canary score $SCORE below $MIN_SCORE"; ./scripts/rollback.sh; exit 1; }
```

Pinning, permissions, and concurrency guardrails

- Pin every GitHub Action by SHA; add org Rulesets that refuse PRs referencing tags/branches.
- Standard job permissions:

```yaml
permissions:
  contents: read
  id-token: write
  pull-requests: write
```

- Workflow-level cancellation to avoid stampedes:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Determinism harness (bake into release + nightly)

- Required env: `TZ=UTC`, `LC_ALL=C`, `PYTHONHASHSEED=0`, `SOURCE_DATE_EPOCH=$GIT_COMMIT_TIME`.
- Dual-run checksum check:

```bash
./scripts/build.sh && sha256sum dist/* > A.txt
./scripts/build.sh && sha256sum dist/* > B.txt
diff -u A.txt B.txt || { echo "Non-deterministic"; exit 1; }
```

Evidence Bundle required artifacts

- `sbom_uri`, `provenance_uri`, `signature_uri`, Rekor UUID + inclusion proof, canary query text and window, determinism diff hash, and policy decisions with their inputs.

Analytics integrity

- dbt must assert freshness SLAs, rowcount deltas, and null-rate caps; ingestion jobs fail fast on breach to prevent stale dashboards.

Packaging and distribution

- Publish PyPI + OCI artifacts with provenance/signatures, supply `pipx` entrypoints, and wrap the OCI image in composite actions so downstream repos only reference a single `workflow_call`.

DR proof

- [x] Weekly restore drill pipeline pulls artifacts by digest, verifies provenance/SBOM, replays deploy, records deltas, and blocks prod if the drill is older than seven days.

Org-level controls

- GitHub Rulesets enforcing signed commits/tags, required checks, no force pushes, CODEOWNERS, and locked release branches stay on the mandatory list.
- Deny changes to `.github/workflows/**` unless CODEOWNERS approve through a protected path rule.
- Require signed and annotated tags for all release patterns; reject lightweight tags.
- Forbid untrusted third-party actions unless mirrored internally and pinned by SHA.

Telemetry and traceability
--------------------------

- Enforce `OTEL_RESOURCE_ATTRIBUTES=service.name,service.version,git.sha` across jobs; propagate tracing metadata into Evidence Bundles.
- Inject `traceparent` into PR comments and artifacts to stitch CI spans with downstream services.
- Record kernel version, containerd build, and image layer digests in provenance; alert on skew > 100 ms or drift across redundant runners.

Data-quality gates
------------------

- Add dbt expectations for rowcount deltas, null caps, and distribution checks on core marts; promote failures from warn to block for scorecard tables.
- Integrate Great Expectations (or dbt-expectations) for metric distribution drift to detect silent dashboard regressions.

Exit-criteria adjustments
-------------------------

- Add “Example fixtures validate” to the v1.0 checklist to ensure schema samples stay in sync.
- Require admission to deny images missing both SBOM and provenance referrers whose subjects match the exact image digest.
- Ensure cache verification/quarantine emits `cache_quarantine` telemetry and alerting before sign-off.
- Disallow `pull_request_target` unless explicitly justified and recorded with CODEOWNERS approval.

7-day plan
----------

1. Reconcile schema/example divergence and wire the canonical fixture into `schema-ci.yml`.
2. Lock Rekor inclusion as a hard gate (release step landed) and add failing-path units for missing UUID/inclusion proofs.
3. Wire `slsa-verifier` with explicit source, workflow, tag, and builder-ID assertions.
4. Implement cache verify-before-restore plus quarantine workflow and surface metrics.
5. Add the egress allowlist smoke test and enforce the `pull_request_target` ban.
6. Sign the Evidence Bundle as an attestation targeting the release digest.

30-day plan
-----------

1. Deliver token-bucket fairness with queue SLO enforcement and denial metrics.
2. Enforce multi-arch parity gates comparing packages and SBOM component counts across manifests.
3. Add policy coverage reporting: `opa test` and `kyverno apply --audit-warn=false` over golden fixtures.
4. Launch KEV/EPSS-aware SBOM diff gating with signed VEX TTL enforcement.
5. Automate DR freshness enforcement with dashboards and blocking rules.

Minimal workflow/test suite to ship now

- `unit.yml` ✅ runs unit tests, emits `pipeline_run.v1.2`, captures coverage.
- `mutation.yml`: PR diff-only mutant run, full nightly run, publishes resilience deltas.
- `release.yml`: build, SBOM, provenance, sign, referrer gate, Kyverno `verifyImages` dry-run.
- `rekor-monitor.yml` ✅ poll Rekor, upload inclusion proofs, alarm on gaps.
- `security-lint.yml` ✅ (ruff/Bandit/pip-audit/dependency review + workflow guard rails).
- `codeql.yml` ✅ (nightly CodeQL scan with SARIF upload).

Summary of additional guardrails: lean on CodeQL for AI-assisted security analysis, expand linting with ESLint and YAML linters, bring in Dependabot/Snyk plus Trivy for dependency/container coverage, and evaluate free DeepSource/Codacy reviews to keep PR feedback tight.

Security Tooling Matrix
-----------------------

| Language/Surface | Tool | Enforce as Gate | Budget/Threshold | Phase Introduced |
| --- | --- | --- | --- | --- |
| Python | Black | Yes | `black --check .` must pass | Phase 1 |
| Python | `ruff check --select S` | Yes | Zero new S-class violations relative to baseline | Phase 2 |
| Python | Bandit | Yes | High severity budget 0; medium ≤ existing baseline with 14-day SLA | Phase 2 |
| Python | pip-audit | Yes | Block CVEs with CVSS ≥ 7 unless covered by approved VEX | Phase 2 |
| Python | mypy | Yes | Zero new type errors; strict mode for new packages | Phase 2 |
| Python | coverage.py | Report | Fail lane if total coverage < agreed floor; publish HTML/XML artifact | Phase 2 |
| JavaScript/TypeScript | npm audit | Yes | No critical/high vulnerabilities without exemption | Phase 2 |
| JavaScript/TypeScript | OWASP Dependency-Check | No (report) | Surface license/CVE deltas for policy review | Phase 2 |
| JavaScript/TypeScript | ESLint | Yes | Block new lint violations in modified files | Phase 2 |
| Configuration | yamllint | Yes | Enforce lint-clean YAML across workflows and charts | Phase 2 |
| Go | gosec | Yes | Block new medium/high GDF findings | Phase 2 |
| Go | govulncheck | Yes | Fail builds on vulnerable modules lacking patched versions or documented VEX | Phase 2 |
| C/C++ | clang-tidy / cppcheck | Yes | Zero new high-severity diagnostics; document suppressions | Phase 3 |
| C/C++ | Sanitizers (ASan/TSan/UBSan) | Report | Run in nightly matrix; fail on detected issues | Phase 3 |
| Polyglot | Semgrep security pack | No (report) | Flag high-confidence CWE findings for triage | Phase 2 |
| IaC | Checkov / KICS / tfsec | Yes | Critical = 0; High ≤ 3 with owner and remediation ticket | Phase 2 |
| Containers | Trivy / Grype / Snyk | Yes | Disallow critical/high image vulns without VEX linkage | Phase 2 |
| Dependencies | Dependabot / Snyk | Yes | Auto-open PRs for CVSS ≥ 7; require approval or documented VEX | Phase 1 |
| Dynamic app security | OWASP ZAP / Nessus | Report | Run against staging weekly; fail on untriaged Highs | Phase 3 |
| Runtime fuzzing | libFuzzer / OSS-Fuzz | Report | Capture crashes; require bug filed before promote | Phase 3 |
| Supply chain | GitHub dependency-review action | Yes | Block new dependencies violating SPDX allowlist or raising high CVEs | Phase 1 |
| Cross-language | GitHub CodeQL (nightly) | No (report) | Triage SLA 2 days; gate promotion once backlog cleared | Phase 3 |
| PR assistance | DeepSource / Codacy (free tier) | No (assist) | Surface suggested fixes; human review required | Phase 3 |

Deferred (post-SLSA tranche)

- Traffic shadowing, gamification hub, and the work-stealing scheduler remain out-of-scope until SLSA/SBOM/admission/determinism/schema items above are green.

Pillars (modules)

1. Mutation Observatory
   - Run unit + mutation tests on PRs. Compute resilience score and delta vs main.
   - Post PR labels weak-tests, high-confidence. Plot resilience vs coverage.
   - Emit Markdown/HTML reports with per-target tables and top surviving mutants; publish as artifacts and link via PR comments.
   - Auto-generate NDJSON + SARIF-style annotations listing surviving mutants/tests to add; enforce thresholds defined in `.ci-intel/config.yml`.
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
   - YAML/rego policies: pinned action SHAs, SPDX license allowlist, least privilege; see the [Security Tooling Matrix](#security-tooling-matrix) for language-specific enforcement gates.
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

```text
             GitHub/GitLab
                 |
           Webhook Receiver
                 |
             Event Bus (NATS)
                 |
   ---------------------------------------
   |                |                     |
 Orchestrator     Analyzers           Sinks
   |          (modular workers)         |
   |    - Mutation Observatory          |--> PR Comments Service
   |    - Pipeline Autopsy              |--> HTML Reports
   |    - Predictive Scheduler          |--> Dashboard API
   |    - Deterministic Auditor         |--> Evidence Registry
   |    - Chaos Injector                |--> Warehouse Loader
   |    - Ephemeral Data Lab            |      (BigQuery / dbt)
   |    - Compliance Validator          |--> Alerting / ChatOps
   |    - Cache Sentinel                |
   |    - Infra Replay                  |
   |    - Evidence Collector            |
   |    - Warehouse Loader              |
   ---------------------------------------
        |             |           |                 |
   Postgres      Object Store   Traces/Logs    Warehouse
   (metrics,     (artifacts,    (OTel->        (BigQuery,
   findings)     logs, DB snaps) Loki/Tempo)   Evidence Lake)
```

Core components

- GitHub App: webhook receiver, PR/issue writer, Checks API integration.

- CI agent CLI (Go or Rust) runs inside pipelines, executes analyzers, uploads events.

- Orchestrator schedules, deduplicates, retries, backfills.

- Analyzer services (gRPC/HTTP): all pillars above.

- Storage: Postgres metadata; S3/MinIO artifacts/logs/snapshots; Redis optional.

- Observability: OpenTelemetry -> Grafana/Loki/Tempo.

- Policy engine: Rego or CEL.

- ML: scikit-learn baseline; pluggable LLM for classification.

Production runner isolation blueprint

- Jobs that require hardened hosts declare a `self_hosted_profile` in `config/runner-isolation.yaml`.
- Orchestrator brings up a Firecracker/gVisor sandbox per job with Vault-issued short-lived tokens.
- `scripts/cache_provenance.sh` captures SHA256/BLAKE3 manifests and cosign signatures for restored caches.
- Egress allowlist lives in `policies/egress-allowlist.md`; guard enforces labels + `max-parallel`.
- Evidence bundle links runner guard logs, cache provenance JSON/NDJSON, and attested build artifacts.

Canary decision evidence pipeline

- Release workflow routes 5–20% of traffic through a canary pool.
- `fixtures/canary/payments_canary.sql` (or service-specific query) compares canary vs baseline error rate and latency over the prior 10 minutes.
- `scripts/capture_canary_decision.py` records decision, query text, evaluation window, metrics dashboard URI, and notes.
- Evidence JSON/NDJSON stored under `artifacts/evidence/canary/`; `scripts/emit_pipeline_run.py` embeds the payload in `pipeline_run.v1.2` so downstream analytics can audit promote/rollback choices.

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

```json
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

Example record (pipeline_run.v1.2)

```json
{
  "schema": "pipeline_run.v1.2",
  "run_id": "1b7c2e4a-6b54-4e3b-9f1e-4e0d9ea9b1a1",
  "repo": "org/app",
  "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "branch": "feature/x",
  "pr": 123,
  "started_at": "2025-10-23T12:00:00Z",
  "ended_at": "2025-10-23T12:04:10Z",
  "status": "success",
  "queue_ms": 5000,
  "artifact_bytes": 7340032,
  "environment": "staging",
  "deployment_id": "deploy-20251023-1200",
  "rollout_step": 2,
  "strategy": "canary",
  "image_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd",
  "sbom_uri": "https://gcs.example.com/sbom/aaaa.json",
  "provenance_uri": "https://gcs.example.com/prov/aaaa.intoto",
  "signature_uri": "https://gcs.example.com/sig/aaaa.sig",
  "release_evidence_uri": "https://gcs.example.com/evidence/manifest.json",
  "runner_os": "linux",
  "runner_type": "hosted",
  "region": "us-central1",
  "spot": false,
  "carbon_g_co2e": 0.07,
  "energy": { "kwh": 0.03 },
  "cache_keys": ["pip-3.12", "pytest"],
  "flakiness_index": 0.02,
  "canary_metrics": {
    "error_rate": 0.001,
    "success_rate": 0.999,
    "latency_p50_ms": 45,
    "latency_p95_ms": 88,
    "latency_p99_ms": 140,
    "reqs_per_s": 120
  },
  "canary": {
    "decision": "promote",
    "recorded_at": "2025-10-23T12:04:20Z",
    "window": {
      "start": "2025-10-23T11:59:20Z",
      "end": "2025-10-23T12:04:20Z"
    },
    "query": "SELECT * FROM canary_metrics WHERE rollout = 'prod';",
    "metrics_uri": "https://gcs.example.com/canary/run-123.json"
  },
  "jobs": [
    {
      "id": "build",
      "name": "build",
      "status": "success",
      "attempt": 1,
      "duration_ms": 70000,
      "queue_ms": 2000,
      "cache": {
        "hit": true,
        "key": "pip-3.12"
      },
      "machine": {
        "class": "standard",
        "cpu": "4",
        "ram_gb": 16
      },
      "logs_uri": "https://gcs.example.com/logs/build.log"
    },
    {
      "id": "test",
      "name": "pytest",
      "status": "success",
      "attempt": 1,
      "duration_ms": 120000,
      "queue_ms": 1000,
      "cache": {
        "hit": false,
        "key": "pytest"
      },
      "machine": {
        "class": "standard",
        "cpu": "4",
        "ram_gb": 16
      },
      "logs_uri": "https://gcs.example.com/logs/pytest.log"
    }
  ],
  "tests": {
    "total": 1240,
    "failed": 2,
    "skipped": 10,
    "duration_ms": 118000,
    "coverage": {
      "lines_pct": 0.86,
      "branches_pct": 0.79,
      "statements_pct": 0.84
    },
    "resilience": {
      "mutants_total": 900,
      "killed": 810,
      "equiv": 30,
      "timeout": 12,
      "score": 0.9,
      "delta_vs_main": 0.03,
      "equivalent_mutants_dropped": true
    }
  },
  "chaos": [
    {
      "fault": "kill_job",
      "target": "pytest",
      "seed": 42,
      "rate": 0.01,
      "started_at": "2025-10-23T12:01:10Z",
      "ended_at": "2025-10-23T12:01:30Z",
      "outcome": "recovered",
      "retries": 1
    }
  ],
  "autopsy": {
    "root_causes": [
      {
        "tool": "pytest",
        "pattern": "AttributeError: NoneType",
        "file": "tests/x_test.py",
        "line": 42,
        "message": "AttributeError: NoneType",
        "suggestion": "ensure setup returns object or add __init__.py",
        "severity": "warn",
        "docs_uri": "https://docs.example.com/autopsy/attrerror"
      }
    ]
  },
  "policies": [
    {
      "id": "two_person_prod",
      "result": "allow",
      "reason": "Distinct approvers met two-person rule"
    }
  ],
  "cost": {
    "usd": 1.23,
    "cpu_seconds": 420,
    "gpu_seconds": 0
  }
}
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

- Policies enforced at merge and deploy: pinned action SHAs, SPDX license allowlist, least-privilege permissions, IaC and secret scanning (see the [Security Tooling Matrix](#security-tooling-matrix) for scanner coverage and gate posture).

- Threat model (STRIDE) documented in docs/THREAT_MODEL.md, updated quarterly.

- Evidence links embedded in PR comments, dashboards, and release_evidence_uri.

Release Evidence Bundle

```bash

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

```bash

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

Phase 0 — Alignment

- Define personas (executive, engineering, SRE, compliance) and KPI targets: resilience, mutation delta, DORA, cache hit %, cost, carbon.

- Decide on data freshness expectations, hosting model, and metric access guardrails.

- Freeze scope until the umbrella dashboard ships.

<a id="phase-1-hermetic-build-path-cd-essentials"></a>
Phase 1 — Hermetic build path + CD essentials

- Rootless/distroless builder pinned by digest; produce SBOM + provenance; register attestations in Rekor.

- Dual-run determinism check for every release build.

- Enforce OIDC-only identity; deny static keys.

- Deploy Rego packs: two-person approvals, pinned action SHAs, egress allowlists.

- GitOps dev deploy with smoke tests; rollback automation; generate Evidence Bundle.

- Emit NDJSON v1.2 from unit.yml, mutation.yml, chaos.yml.

- Pin every GitHub Action by commit SHA, set least-privilege permissions/id-token scopes, enable workflow `concurrency` cancellation, and add the secret-scan CI job so unpinned steps or static secrets fail PRs immediately.

- Add Black formatting enforcement (`black --check .`) to the lint lane so Python code style stays consistent before merges.

- Publish reusable `workflow_call` pipelines and composite actions for lint, test, release, and security so downstream repos can consume the same gated templates without copy/paste.

- Standardize dependency and secret hygiene across repos with a shared Dependabot/Renovate configuration, SPDX allowlists, and org-wide secret-scanning baselines that alert on drift.

- Enforce Rekor inclusion proof check in the release gate so missing UUIDs fail the Evidence Bundle step.

- Ship a developer onboarding kit (repo template, CI cheat sheet, runbook index) so new services adopt the hub guardrails on day one.

Phase 2 — Ingestion and storage

- Instrument workflows to emit structured events (JSON artifacts, test telemetry, chaos outcomes, cache stats).

- Configure transport (Kafka/Kinesis/Pub/Sub or direct ingest) with schema validation and retry/backfill logic.

- Load to BigQuery raw partitioned by repo/pipeline/date; curate marts with dbt/SQLMesh: pipeline_runs, test_resilience, cost_usage, chaos_events, ownership dimensions.

- Expand quality automation: run `mypy` for static type coverage, execute `pytest` with `coverage.py` reports, and fail the lane if type errors surface or coverage drifts below negotiated guardrails; publish the coverage artifact through GitHub Actions for reporting.

Phase 3 — Policy, gates, and analytics

- PR gates: OpenAPI/GraphQL diff, performance budgets (k6/Locust), diff coverage + test-impact selection, fuzz/property smoke tests.

- Enforce referrer presence, cosign provenance verification, SBOM+VEX policy gates, and Kyverno `verifyImages` deny-by-default policies with an accompanying failing-path test + alert.

- Publish dashboards: Run Health, Efficiency, Quality, Chaos/Determinism, Sustainability.

- Alerting correlates regressions to commits/teams/infra changes; ChatOps integrations push summaries.

- Schema-CI, compat view, and migration tests fully operational.

- Layer in dynamic security coverage: schedule fuzzers against critical binaries, run OWASP ZAP active scans (and Nessus where licensed) in staging, wire Dependabot/Snyk advisory PRs with required review, and scan Terraform/Kubernetes via Checkov/tfsec before promotion. Surface results as GitHub Action reports and evaluate free AI-assisted PR feedback (CodeQL code scanning, DeepSource/Codacy) alongside ESLint/YAML lint gates for ancillary stacks.

- Expand analytics marts with a repository catalogue capturing ownership, criticality, SLOs, coverage, and security posture so the warehouse can drive fleet scorecards and stale-pipeline alerts.

- Institute recurring threat-model reviews and CIS/SOC2 control mapping, tying findings to policy-gate evidence bundles per repo.

<a id="phase-4-reliability-hardening-and-chaos"></a>
Phase 4 — Reliability hardening and chaos

- Nightly heavy chaos; 1% PR chaos with kill-switch and fault allowlist.

- Backup/restore pipelines with weekly DR drills recorded in warehouse.

- Runner autoscaling and queue failover in place.

- Infrastructure Replay service active.

- Runner isolation enhancements (optional stretch goal): Firecracker/gVisor hosts, egress allowlists, zero local persistence, cache manifest signing, and backpressure budgets to prevent poisoning or queue starvation.

Phase 5 — Advanced analytics and optional gamification

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

Hardening validation backlog
----------------------------

End-state goal: every release runs these verification suites automatically. Items marked ⏳ are defined but not yet implemented.

1. Determinism & reproducibility (⏳)
   - Bit-for-bit rerun comparison (`diffoscope`, dual clean builds)
   - Hermetic build check (egress denied except registry/cache)
   - Locale/clock stability (consistent hashes under varied TZ/locale)

2. Provenance & SLSA verification (⏳)
   - Cosign `verify-attestation` + `slsa-verifier`
   - Rekor inclusion proof required for promotion

3. SBOM/VEX correctness (⏳)
   - CycloneDX/SPDX schema validation and cross-tool parity
   - VEX ↔ SBOM referential integrity checks

4. Policy tests (⏳)
   - `opa test` / `conftest` coverage
   - `kyverno apply` simulation with golden resources

5. Security scanning gates (⏳)
   - Grype/Trivy fail-on-high scans
   - Secret/supply-chain linters (gitleaks, pinned-action checker)

6. Workflow idempotency & replay safety (⏳)
   - Double workflow_dispatch with same inputs → identical artifacts
   - Rerun failed job → no state leakage

7. Cache integrity (⏳)
   - Salted cache miss scenarios
   - Malicious cache injection (fork isolation)

8. Multi-arch parity (⏳)
   - `crane manifest/digest` mapping + SBOM component parity across arches

9. DR & chaos drills (⏳)
   - Fault injection SLO assertions (latency, registry 5xx)
   - Restore-from-evidence job producing byte-identical artifacts

10. Analytics spine correctness (⏳)
    - NDJSON schema validation (`ajv`)
    - dbt data tests & KPI expectations

11. Cost & performance regression checks (⏳)
    - Workflow duration budgets (p95 alerting)
    - Artifact size ceilings

12. Access & OIDC trust chain (⏳)
    - Verify no PATs/long-lived secrets; id-token scope enforcement

Where AI can assist (optional stretch)
- Generate Rego unit tests, determinism workflows, NDJSON fuzzers, SBOM/VEX diff runners, cosign/rekor verification scripts, dbt expectation seeds, chaos drill matrices, and evidence-summary reports.

- DR + idempotency: backfill re-ingest pipeline, immutable artifact storage, disaster recovery runbook.

- Developer experience: local pipeline emulator, Makefile targets, ChatOps /promote and /rollback commands.

- Canary governance: persist the raw promote/rollback queries with their evaluation windows, hash + attach them to the Evidence Bundle, and require sign-off before altering thresholds.

Minimum evidence bundle to declare "secure enough"
--------------------------------------------------

All items must be automated and attached per release before v1.0 sign-off:

- Cosign `verify-attestation` output (issuer/subject regex enforced) ✅ today.
- Rekor UUID + verified inclusion proof (`tools/verify_rekor_proof.py` enforces gate) ✅.
- OCI referrers discovered for CycloneDX/SPDX SBOM + provenance (✅ generator/run; ⏳ hard gate).
- Determinism report: dual-build hashes, diffoscope summary, env invariants (✅ multi-arch; ⏳ cross-time).
- Policy transcripts: OPA + Kyverno evaluation logs with inputs (✅ concept; ⏳ formalized evidence attachment).
- SBOM scan normalized with VEX decision (✅ grype+build_vuln_input; ⏳ enforced allow check).
- DR drill result in SLA with replay verification (✅ workflow; ensure fail on stale run >7d).
- Schema-CI + dbt results + freshness SLA (✅ jobs; ensure metrics archived in evidence bundle).

Tests to wire before calling v1.0
---------------------------------

- Supply chain: referrer presence gate, Cosign bundle verification (including Rekor inclusion), base image CVE budget with VEX overrides.
- Determinism: cross-arch and cross-time reruns, locale/TZ variation, hermetic build with egress deny.
- Policy: `opa test` coverage and `kyverno apply` golden resources.
- Cache: signed manifest verification on restore, fork-isolation negative test, quarantine pipeline.
- Access: org-wide PAT scan, Rulesets to block unpinned actions and enforce least-privilege tokens.
- Analytics: NDJSON signature/checksum chain, `ajv` validation, dbt uniqueness/freshness expectations used as gates.
- Cost/carbon: enforce budgets in PR gate; evidence archive.
- Canary: store query text/window, deterministic scorer/thresholds under version control.

7-day enablement checklist (GitHub-hosted runners)
--------------------------------------------------

1. Keep the Rekor gate enforced, add regression coverage (missing UUID/proof), and surface alerting on gate failure.
2. Enforce OCI referrer presence + Cosign bundle verification.
3. Add iptables-based egress allowlist, with audit that fails on unexpected domains.
4. Sign cache manifests and verify before restore; quarantine mismatches.
5. Promote Kyverno policies from audit to enforce at deploy target.
6. Wire cross-time determinism job (24h spaced) and attach diffoscope summary.
7. Enable Dependabot/Renovate and dependency-review gates.

30-day hardening (optional stretch)
-----------------------------------

- Self-hosted Firecracker/Vault runner profile + attestation (optional for regulated environments).
- API diff and performance budget gates; fuzz/property testing for critical components.
- SARIF normalization and suppression expiry automation.
- WORM artifact storage with cross-region replication and periodic integrity checks.
- Org-level "no unpinned actions" Ruleset + pre-receive checks.

Acceptable risk statement
-------------------------

With Rekor gating, cache verification, egress allowlist, policy enforcement, and the evidence bundle finalized, the platform meets SLSA L3-equivalent integrity on GitHub-hosted runners. For regulated workloads, layer in the Firecracker/Vault profile and WORM+replication before go-live.

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

```bash

- name: Gate on resilience
  run: |
    SCORE=$(jq -r '.tests.resilience.score' artifacts/pipeline_run.ndjson)
    MIN=0.75
    if awk "BEGIN{exit !($SCORE < $MIN)}"; then
      echo "Resilience $SCORE < $MIN"
      exit 1
    fi

```bash

```bash

cosign verify --key cosign.pub "$IMAGE_DIGEST"
opa eval -i deploy/context.json -d policies 'data.allow' | grep -q true

```bash

Rego: two-person rule

```bash

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

```bash

Determinism and chaos control flow

```bash

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

```bash

Data flow (CI -> analytics stack)

```bash

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

```bash

CI wiring (GitHub Actions)

```bash

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

```bash

CD skeleton (GitHub Actions)

```bash

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

```bash

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

```bash

- id: py.initpkg.missing
  tool: pytest
  match: "ImportError: attempted relative import.*"
  hint: "Add __init__.py to package directories."

```bash

Issue template

```bash

🚨 Build #128 root causes

- pytest: AttributeError: NoneType in tests/x.py:42

- Fix: ensure setup() returns object. Consider adding __init__.py in tests/

Artifacts: logs, junit, repro steps

```bash

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

8. Scheduled `chaos.yml` run injects faults and uploads chaos NDJSON; `dr-drill.yml` simulates backup/restore and attaches evidence.

Sample configs

```bash

mutation:
  lang: auto
  include: ["src/**"]
  tests: ["tests/**"]
  diff_only: true
  thresholds:
    score_warn: 0.7
    score_fail: 0.6

```bash

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

- Hermetic release image ✅ (Dockerfile pinned to python:3.12-slim@sha256:e97cf9a..., project sources fixed to commit fafa48a, dependencies installed via pip==24.2) to keep builds reproducible across stages.

- Monitor Rekor consistency and new entries for tracked subjects; alert on missing inclusion proofs (rekor-monitor) ✅ — `collect-evidence` runs `tools/rekor_monitor.sh` and stores proofs in `artifacts/evidence/`.

- Standardize on SLSA v1.0 provenance predicate (in-toto); validate required fields before promotion.

- Enforce secretless CI: forbid long-lived keys in job env, require OIDC subject/issuer allowlist, verify short TTLs.

- Cross-architecture determinism checks (x86_64 vs ARM64) with base-image digests pinned via CAS; fail on ELF/PT_GNU_BUILD_ID drift.

- Enforce VEX-aware gating ✅ (implemented): generate CycloneDX VEX statements from `fixtures/supply_chain/vex_exemptions.json` via `tools/generate_vex.py`, push them with the SBOM/referrers, scan the CycloneDX SBOM with Grype inside the policy-gates job, normalize the findings via `tools/build_vuln_input.py`, and require SBOM/VEX policy approval (next: source signed VEX referrers from the real vuln-management system).

- Establish schema registry with semver, compatibility tests, ownership ADRs, and deprecation windows for every event topic.

- Autopsy governance: record LLM model ID/digest/prompts/temperature; prohibit LLM-only gate decisions.

- Runner isolation (optional): GitHub-hosted runners cover the baseline. `config/runner-isolation.yaml` and `scripts/check_runner_isolation.py` exist for future self-hosted rollout (Firecracker/gVisor, Vault-issued tokens, cache provenance) if compliance demands it.

- Cost/carbon enforcement: turn telemetry into budgets that gate PRs exceeding limits.

- Disaster recovery proof: quarterly artifact recall drill using provenance/SBOM/pinned mirrors; publish diff in Evidence Bundle.

- Scheduler upgrades: pre-warm runners based on predictions, deterministic fallback when MAPE > threshold, publish fairness metrics per team.

- GitHub organization controls: Rulesets enforcing required status checks, signed commits/tags, CODEOWNERS approval on critical paths, conversation resolution, no force-push, protected releases (only builder identity signs tags).

- Admission policy trio: per-environment image digest allowlists, required provenance, required SBOM referrers; deny deploy on missing attestations.

- Base-image SLO: block builds when base image gains critical CVE without VEX “not exploitable”.

- Builder hardening: ephemeral isolated builders with OIDC identity, provenance capturing parameters, pinned source URI, reproducible toolchain versions, environment hash recorded in provenance and Evidence Bundle.

- Determinism hardening: release workflow now performs cross-arch/time manifest reruns and fails on hash drift (`tools/determinism_check.sh`); next step is 24h-spaced rebuild diffing to catch BUILD_ID/JAR drift even with stable digests.

- Language-specific reproducibility hooks: PYTHONHASHSEED=0 + pip --require-hashes; Go -trimpath + GOMODSUMDB=on; Java reproducible builds plugin; Node npm ci with lockfile v3; Rust --remap-path-prefix.

- Cache integrity: complete — manifests are signed, bundles verified pre-restore, quarantines emitted, and cache telemetry recorded.

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

Phase 2 – Shared Tool Distribution
----------------------------------
Purpose: evolve this repo from “scripts + instructions” into a consumable toolkit that any repo can download and run in its own pipelines without duplicating logic.

1. Package the analyzers and helpers.
   - Ship the Python CLIs (mutation observatory, supply-chain scanners, VEX tooling) as a versioned package on PyPI and as an OCI image that contains their runtime deps (`rekor-cli`, `jq`, etc.).
   - Provide console entrypoints and `pipx` install instructions; publish SemVer tags and changelog.

2. Publish reusable GitHub Actions/workflows.
   - Convert the current `.github/workflows/*.yml` files into `workflow_call` templates and/or composite actions.
   - Downstream repos reference them via `uses: org/ci-cd-bst-demo-github-actions/.github/workflows/mutation.yml@v1` and pass repo-specific inputs/secrets.

3. Template repo-specific configs.
   - Maintain canonical configs (mutation observatory YAML, Rekor monitor settings, VEX fixtures) in `templates/`.
   - Use Copier/Cookiecutter or a sync bot to stamp/update files in downstream repos; record overrides via metadata comments.

4. Release and promotion process.
   - For each hub release: tag git (`vX.Y.Z`), publish the PyPI/OCI artifacts, and attach a GitHub Release with upgrade notes.
   - Encourage repos to pin to specific versions and roll forward deliberately (dev → staging → prod channels).

5. Migration guidance.
   - Document “drop-in” steps: install the published package/image, invoke the reusable workflow, plug in configs, and set env/secrets.
   - Track adoption status per repo (table in README or ops board) to coordinate upgrades/rollbacks.

6. Local-first workflows + caching strategy.
   - Ship a `docker-compose`/`devcontainer` setup so engineers can run the same analyzers locally (mutation observatory, Rekor monitor, supply-chain gates) before pushing. Provide `make` targets that mirror the CI jobs.
   - Standardize cache usage in GitHub Actions: leverage `actions/cache` for dependency trees (pip, npm, cargo) and `docker/build-push-action` cache exports/imports to GHCR so parallel jobs share layers. Document the pattern (prime cache once, export to GHCR, and import in parallel jobs) and provide snippets in `/docs/caching.md` so teams can opt in per workflow.
   - Ensure local runs honor the same cache dirs (mounted volumes) so debugging uses the cached artifacts and matches CI behavior.

7. Structured parallelism playbook.
   - Define a default job matrix that splits “lint”, “unit test”, “integration test”, “mutation test”, and deployment stages into separate jobs so Actions runners execute them concurrently (matching the Jenkins-to-GH Actions speedup story).
   - Provide guidance for self-hosted runners vs GitHub-hosted (labels, concurrency caps, dependency ordering) and encode the pattern in the reusable workflows to keep PR-to-dev time low across microservices.

8. Secure lint/SAST suite.
   - Provide a reusable “security lint” job with severity gating and vulnerability DB caching; coverage, thresholds, and enforcement live in the [Security Tooling Matrix](#security-tooling-matrix).
   - Teams extend the matrix by adding rows for new stacks, and every finding is normalized to SARIF before flowing into policy gates and SBOM/VEX diffing.

Hub product specification (install once, apply everywhere):

1. Install modes
   - Reusable workflows exported via `workflow_call`, versioned (`@vX.Y`), pin sub-actions by SHA.
   - Composite actions that wrap the shared agent container for bespoke steps.
   - OCI image (`ghcr.io/org/ci-intel@sha256:...`) plus PyPI/`pipx` CLI (`ci-intel`) with signatures and attestations.

2. Single config contract
   - `.ci-intel/config.yml` validated by JSON Schema with layered overrides (hub defaults → org policy overlay → repo-specific stricter settings).
   - Keys cover project metadata, budgets (Bandit/Semgrep/Trivy/cost/CO₂e), test thresholds, performance SLOs, chaos cadence, supply-chain requirements, policy packs, runner preferences.

3. Published workflows (entrypoints)
   - `ci.yml` (lint/unit/diff mutation/SCA/SAST/IaC + NDJSON emit), `release.yml` (build/SBOM/provenance/sign/referrers/Evidence Bundle), `policy-gates.yml`, `deploy.yml`, `dr-drill.yml`, `rekor-monitor.yml`.
   - Each accepts inputs (`config_path`, `lang`, toggles) and is invoked from downstream repos with one `uses:` block and required permissions.

4. Security and supply chain
   - Keyless Cosign, SLSA v1.0 provenance, OCI 1.1 referrers for SBOM/VEX; Kyverno `verifyImages` policies; org Rulesets enforcing signed commits/tags, CODEOWNERS, no force-push; OIDC-only secrets; egress default deny.

5. SAST/SCA/IaC packs with budgets
   - Bundled tools per language (Bandit, Ruff security rules, Semgrep, pip-audit, npm audit, govulncheck, OWASP DC, CodeQL queries, GitHub dependency-review, Checkov/KICS, Trivy/Grype) with enforcement via `policy-gates.yml` comparing results to `.ci-intel` budgets; override flow requires justification and SBOM evidence. Coverage and gate posture are tracked in the [Security Tooling Matrix](#security-tooling-matrix).

6. Determinism and cache
   - Reusable determinism step ensuring SOURCE_DATE_EPOCH/TZ/LC and dual-run checksum; cache sentinel with BLAKE3 keys, signed manifests, quarantine on mismatch.

7. Analytics wiring
   - Every workflow emits `pipeline_run.v1.2` NDJSON, validated before upload; provided ingest to GCS→BigQuery/dbt marts with row-level security; dashboards auto-published.

8. Bootstrap and update automation
   - `pipx run ci-intel bootstrap --repo org/name` seeds `.ci-intel/config.yml`, caller workflow, OIDC trust, and docs.
   - Sync bot watches hub releases, opens update PRs, supports stable/canary channels, reports risk via “plan” job.

9. Compatibility and tests
   - Strict SemVer, backward-compatible minors; golden repos per language; CI matrix (lang, monorepo flag, runner OS/arch) plus schema compatibility gates.

10. Runner strategy
    - Default to GitHub-hosted for light work, self-hosted ephemeral pools for heavy jobs; enforce quotas/fairness, maintain ARM/x86 parity runs.

11. Org policy spine
    - Central `org-policy/` repo with Rego/CEL packs, Kyverno bundles, Ruleset JSON, allowlists/licensing/egress domains; signed releases consumed by `policy-gates.yml`.

12. DR and retention
    - WORM + cross-region artifact/NDJSON storage with tiered retention (30/180/400 days); weekly `dr-drill.yml` gated by ruleset, blocks promotion if stale.

13. Day-0 deliverables
    - Reusable workflows, composite wrappers, agent images (rekor-cli, jq, trivy, grype, semgrep, checkov, k6), schemas for `.ci-intel` + NDJSON, templates per service type, adoption/upgrade/policy docs.
    - Native test-report UX: integrate reporters (e.g., Playwright GitHub Actions Reporter) and add a workflow step that posts annotated PR comments linking to hosted rich reports for UI/E2E suites.

14. Minimal caller configs
    - Example `.ci-intel/config.yml` snippets for Python API and Node service demonstrating budgets/tests/supply-chain/chaos knobs.

15. Enforcement snippets
    - Canonical Bandit budget check, referrer presence probe, and similar bash fragments documented for extension.

16. Developer experience & communications
    - Ship a docs portal (e.g., GitHub Pages + MkDocs) sourced from `/docs` with quick starts, troubleshooting, FAQs, and sample dashboards.
    - Provide ChatOps commands (`/ci-intel rerun`, `/ci-intel status`) plus Slack/Teams notifications that link to the rich reports and Evidence Bundle.
    - Bundle a `ci-intel doctor` command that inspects local environments, validates `.ci-intel/config.yml`, and reproduces CI jobs locally with the same containers.

Outcome: one centrally maintained toolchain that every repo can consume by downloading a release artifact or referencing a reusable workflow, enabling consistent CI/CD enforcement without re-implementing pipelines per project.
# Current Maturity Snapshot

| Dimension | Score (0–5) | Notes |
|-----------|-------------|-------|
| Supply-chain trust (signing, SBOM/VEX, Rekor) | 4.0 | End-to-end evidence model is in place: SBOM, VEX, provenance, Rekor proof, digest/tag linkage, cache manifests, schema-validated telemetry. |
| Provenance/SLSA L3 plausibility on GH-hosted | 3.5 | SLSA attestation and verifier wired; GH-hosted limitations documented. |
| Determinism harness (dual-run, diffing) | 3.0 | Diffing present but hardening (SOURCE_DATE_EPOCH, locale, umask) not yet enforced. |
| Policy gates (Kyverno/OPA packs + tests) | 3.0 | Policies exist and are tested; enforcement still advisory. |
| Evidence lineage and auditability | 4.0 | Evidence bundle layout, signing, cache manifests, telemetry, and schema checks are advanced. |
| DR/chaos and runner isolation | 2.5 | Scenarios exist but not tied to SLOs or automated rollback gates; GH-hosted runner isolation only. |
| Reusable workflows as a hub (`workflow_call`) | 3.0 | Blueprint defined; hub workflow not yet shipped. |
| Data/analytics spine (NDJSON → dbt) | 3.0 | Ingestion pipeline + marts working; chain of custody signatures pending. |
| Documentation/runbooks and ops hygiene | 3.5 | Plan/README/runbooks detailed; enforcement posture docs still TODO. |
| Overall enterprise readiness | 3.0 | Advanced for a small team; key guardrails still beta. |
