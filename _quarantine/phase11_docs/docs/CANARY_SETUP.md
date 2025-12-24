# Canary Decision Setup Guide

This guide explains how to adapt the canary evidence pipeline to your service. It uses
Prometheus for metrics and Grafana for visualization; swap in equivalent tooling if needed.

## 1. Metrics Requirements

- Prometheus recording rules for `error_total` and latency histograms (e.g., `http_request_duration_seconds_bucket`).
- Labels: `service`, `environment` (`baseline`, `canary`), `region` (optional).
- Metrics retention ≥ 24h to allow retroactive evaluation.

## 2. PromQL / SQL Query

Update `fixtures/canary/payments_canary.sql` with the metrics your service exposes. If
you track ratios, adjust the SELECT accordingly. Example PromQL equivalent:

```promql
max_over_time(
  sum(rate(http_requests_total{service="payments-api",environment="canary"}[1m]))
)[10m:1m]
```

You can embed PromQL directly if you wrap it in a shell script:

```bash
cat <<'PROM' > fixtures/canary/payments.promql
max_over_time(
  sum(rate(http_requests_total{service="payments-api", environment="canary"}[1m]))
)[10m:1m]
PROM
```

Then update `scripts/capture_canary_decision.py` invocation to execute the PromQL via
`curl` or `promtool query`.

## 3. Grafana Dashboard Link

Create a Grafana dashboard that overlays baseline vs canary metrics. Use dashboard
variables to select the release tag and region. Example URL:

```text
https://grafana.example.com/d/payments/canary?var-release=${GITHUB_REF_NAME}&var-region=us-east-1
```

Update `.github/workflows/release.yml` to set `CANARY_METRICS_URI` to that dashboard.

## 4. Decision Thresholds

Decide on SLO boundaries before rollout. Example:

- Canary error rate ≤ baseline error rate × 1.05.
- Canary P95 latency ≤ baseline P95 + 25 ms.
- No elevated saturation (CPU, memory) vs baseline.

Capture these thresholds in `scripts/capture_canary_decision.py` by adding post-processing
logic or store them as notes.

## 5. Evidence Bundle Output

After the release completes, the evidence bundle contains:

- `artifacts/evidence/canary/decision.json`
- `artifacts/evidence/canary/decision.ndjson`
- `artifacts/pipeline_run.ndjson` (with the embedded canary block)

Link these artifacts in change-management tickets or incident reviews so auditors can see
exactly how the promote/rollback call was made.

## 6. Manual Override

If you must promote manually:

1. Run the query (Grafana explore, promtool, etc.).
2. Save the output to `artifacts/evidence/canary/manual.json`.
3. Run `python scripts/capture_canary_decision.py --decision promote --query-file artifacts/evidence/canary/manual.sql --output artifacts/evidence/canary/manual.json`.
4. Attach the JSON to the release ticket.

This keeps the evidence trail intact even for manual decisions.
