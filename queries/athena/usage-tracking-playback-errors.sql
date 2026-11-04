-- Purpose: usage tracking: PLAYER_ERROR rows (session id, error code, message, position) from the debug-events table for given clientid values (<deviceId>:<householdId>) over a datetime range.
-- Tables: `{{database}}.{{debug_events_table}}`
-- Params: `client_ids_block`, `database`, `datetime_end`, `datetime_start`, `debug_events_table`
-- Status: draft
-- Source:
--   - usage tracking pipeline: src/pipelines/usage_tracking/athena_source.py (debug_events_table is <tenant>_ccl_debug_events for the current month, else with a month suffix such as _oct26 or _sept26)

SELECT
  datetime,
  clientid,
  json_extract_scalar(eventdata, '$.sessionid') AS session_id,
  json_extract_scalar(eventdata, '$.errorcode') AS error_code,
  json_extract_scalar(eventdata, '$.errordescription.errordescription') AS message,
  json_extract_scalar(eventdata, '$.position') AS position
FROM "{{database}}"."{{debug_events_table}}"
WHERE eventid = 'PLAYER_ERROR'
  AND datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  AND clientid IN (
{{client_ids_block}}
  )
ORDER BY datetime;
