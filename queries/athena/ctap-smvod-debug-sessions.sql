-- Purpose: CTAP/SM-VOD distinct abr-vod sessions in the debug-events table for one UTC day with their first event time, input to compare_lightstep_athena_sessions.py --debug.
-- Tables: `{{database}}.{{debug_events_table}}`
-- Params: `database`, `datetime_end`, `datetime_start`, `debug_events_table`
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/run_athena_debug_sessions.py

SELECT
  json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
  MIN(datetime) AS first_event
FROM "{{database}}"."{{debug_events_table}}"
WHERE eventid IN ('PLAYER_SESSION_EVENT', 'PLAYER_STATE_CHANGE', 'PLAYER_ERROR')
  AND datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  AND json_extract_scalar(eventdata, '$.sessionid') LIKE 'abr-vod-%'
GROUP BY json_extract_scalar(eventdata, '$.sessionid');
