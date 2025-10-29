with runs as (
    select * from {{ ref('stg_pipeline_runs') }}
)

select
    repo,
    avg(resilience_score) as avg_resilience_score,
    percentile_cont(0.95) within group (order by tests_total) as p95_tests
from runs
group by 1

