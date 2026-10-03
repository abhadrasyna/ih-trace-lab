SELECT
    datetime,
    eventclass,
    eventid,
    clientid,
    json_extract_scalar(eventdata, '$.sessionid') AS session_id,
    eventdata
FROM "{{database_identifier}}"."{{table_identifier}}"
WHERE json_extract_scalar(eventdata, '$.sessionid') IN ({{id_list}})
  AND datetime >= '{{start_date}}T00:00:00.000Z'
  AND datetime <  '{{end_date_exclusive}}T00:00:00.000Z'
ORDER BY session_id, datetime;
