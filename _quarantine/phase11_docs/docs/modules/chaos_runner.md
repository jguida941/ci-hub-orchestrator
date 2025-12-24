# Chaos Runner

## Purpose

Simulate chaos experiments defined in a JSON config and emit deterministic JSON plus NDJSON evidence for downstream analytics.

## Usage

```bash
python tools/run_chaos.py \
  --config chaos/config.json \
  --output artifacts/chaos/report.json \
  --ndjson artifacts/chaos/events.ndjson
```

## Configuration

Minimal example (`chaos/config.json`):

```json
{
  "run_id": "chaos-dev-001",
  "experiments": [
    { "fault": "kill_pod", "target": "worker", "rate": 0.07 },
    { "fault": "latency_inject", "target": "api", "rate": 0.02 }
  ]
}
```

- `fault`, `target`, `rate`, and optional `seed` control each simulated injection.
- `run_id` is propagated to the JSON summary for traceability.

## Outputs

- JSON summary: `schema=chaos_report.v1`, includes all experiments.
- NDJSON stream: each `ChaosEvent` serialized per line for BigQuery ingestion.

## Dependencies

- Python 3.12+
- Standard library only.

## Workflows

`.github/workflows/chaos.yml` runs the simulator nightly and publishes artifacts.

## License

See [LICENSE](../../LICENSE).

**Back to:** [Overview](../OVERVIEW.md)
