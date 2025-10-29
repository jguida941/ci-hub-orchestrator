CREATE TABLE IF NOT EXISTS demo_metrics (
  id SERIAL PRIMARY KEY,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC NOT NULL,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO demo_metrics (metric_name, metric_value)
VALUES ('resilience_score', 0.87),
       ('flake_index', 0.02),
       ('cache_hit_ratio', 0.78);

