# Metrics Dictionary

| Metric           | Definition | Unit | Notes |

|------------------|------------|------|-------|

| Resilience       | `killed / max(1, mutants_total - equivalent)` | Ratio (0-1) | Control limits recorded per service. |

| Flake Index      | `flaky_runs / total_runs` (excluding quarantined tests) | Ratio | 30-day rolling window per suite. |

| MTTR             | Median time from failure detection to successful rerun/deploy | Minutes | Calculated per environment. |

| Cost / Run       | Total `usd` per pipeline run | USD | Aggregated by repo/pipeline. |

| Carbon / Run     | `carbon_g_co2e` | Grams CO₂e | Weekly aggregation and per-release summary. |

| Burn Rate        | `actual_error_minutes / allowed_minutes` | Ratio | Evaluated over 1h/6h/24h windows for error budgets. |

| Queue SLO        | Median queue time per runner class | Seconds | Backpressure gate when breached. |

| Cache Savings    | `(cache_hits * avg_rebuild_time)` | Minutes saved | Derived from cache events. |
