with source as (
    select * from read_json_auto('data/warehouse/pipeline_runs.ndjson')
)

select
    run_id,
    repo,
    branch,
    status,
    environment,
    cast(tests.total as integer) as tests_total,
    cast(tests.resilience.score as double) as resilience_score,
    cast(cost.usd as double) as cost_usd,
    started_at,
    ended_at
from source
