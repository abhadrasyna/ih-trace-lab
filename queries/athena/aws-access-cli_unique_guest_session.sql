SELECT
    {{session_date_expr}} AS session_date,
    count(distinct clientid) AS metric_value
FROM "{{database_identifier}}"."{{table_identifier}}"
WHERE datetime >= '{{start_date}}T00:00:00.000Z'
  AND datetime < '{{end_date_exclusive}}T00:00:00.000Z'
  AND split_part(clientid, ':', 2) LIKE 'GUEST.%'
GROUP BY 1
ORDER BY 1;
