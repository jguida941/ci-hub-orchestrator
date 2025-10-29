with source as (
    select * from read_json_auto('data/warehouse/autopsy_findings.ndjson')
)

select
    tool,
    severity,
    file,
    line,
    message
from source
