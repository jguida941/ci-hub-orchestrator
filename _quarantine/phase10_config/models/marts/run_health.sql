with runs as (
    select * from {{ ref('stg_pipeline_runs') }}
)

select
    repo,
    environment,
    count(*) as total_runs,
    avg(resilience_score) as avg_resilience,
    avg(cost_usd) as avg_cost_usd
from runs
group by 1,2

