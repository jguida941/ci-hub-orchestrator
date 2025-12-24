with pipeline_runs as (
    select
        json_extract_string(json, '$.run_id') as run_id,
        json_extract(json, '$.autopsy.root_causes') as root_causes
    from read_json_objects('data/warehouse/pipeline_runs.ndjson')
),
flattened as (
    select
        run_id,
        json_extract_string(finding, '$.tool') as tool,
        json_extract_string(finding, '$.severity') as severity,
        json_extract_string(finding, '$.file') as file,
        cast(json_extract(finding, '$.line') as integer) as line,
        json_extract_string(finding, '$.message') as message,
        json_extract_string(finding, '$.pattern') as pattern,
        json_extract_string(finding, '$.suggestion') as suggestion,
        json_extract_string(finding, '$.docs_uri') as docs_uri
    from pipeline_runs
    cross join lateral json_each(coalesce(root_causes, '[]'::json)) as findings(idx, finding)
)

select
    run_id,
    tool,
    severity,
    file,
    line,
    message,
    pattern,
    suggestion,
    docs_uri
from flattened
