SELECT
    {{session_date_expr}} AS session_date,
    count(distinct {{distinct_expression}}) AS metric_value
FROM "{{database_identifier}}"."{{table}}"
WHERE date(timestamp_formatted) >= date '{{start_date}}'
  AND date(timestamp_formatted) < date '{{end_date_exclusive}}'
  {{extra_where}}
GROUP BY 1
ORDER BY 1;
