{% test not_empty(model) %}
  with row_count as (
    select count(*) as cnt
    from {{ model }}
  )
  select
    {{ "cnt" if should_store_failures() else "1" }}
  from row_count
  where cnt = 0
{% endtest %}
