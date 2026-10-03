SELECT
  errorcode,
  COUNT(DISTINCT counted_id) AS metric_value
FROM (
  SELECT
    json_extract_scalar(eventdata, '$.errorcode') AS errorcode,
    {{distinct_expression}} AS counted_id
  FROM "{{database_identifier}}"."{{table_identifier}}"
  WHERE eventid = 'PLAYER_ERROR'
    AND {{time_predicate}}
    AND json_extract_scalar(eventdata, '$.errorcode') IS NOT NULL
)
GROUP BY errorcode
ORDER BY errorcode;
