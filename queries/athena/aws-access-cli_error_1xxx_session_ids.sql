SELECT DISTINCT
  json_extract_scalar(eventdata, '$.sessionid') AS session_id
FROM "{{database_identifier}}"."{{table_identifier}}"
WHERE eventid = 'PLAYER_ERROR'
  AND json_extract_scalar(eventdata, '$.errorcode') IN ({{error_codes}})
  AND datetime >= '{{date}}T00:00:00.000Z'
  AND datetime <  '{{next_date}}T00:00:00.000Z'
ORDER BY session_id;
