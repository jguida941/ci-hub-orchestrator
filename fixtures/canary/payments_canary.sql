-- Canary metrics comparison for payments API.
WITH windowed AS (
  SELECT
    time_bucket('1 minute', ts) AS window,
    service,
    SUM(rate(error_total[1m])) AS error_rate,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS latency_p95
  FROM metrics.prometheus_series
  WHERE service = 'payments-api'
    AND environment IN ('canary', 'baseline')
    AND ts BETWEEN $1 AND $2
  GROUP BY 1, service
)
SELECT
  MAX(window) - INTERVAL '10 minutes' AS window_start,
  MAX(window) AS window_end,
  MAX(CASE WHEN service = 'canary' THEN error_rate END) AS canary_error_rate,
  MAX(CASE WHEN service = 'baseline' THEN error_rate END) AS baseline_error_rate,
  MAX(CASE WHEN service = 'canary' THEN latency_p95 END) AS canary_latency_p95_ms,
  MAX(CASE WHEN service = 'baseline' THEN latency_p95 END) AS baseline_latency_p95_ms
FROM windowed;
