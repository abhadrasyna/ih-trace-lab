-- Purpose: CTAP/SM-VOD Step 4 debug-event enrichment with lifecycle, error, and position rows for a known session set.
-- Tables: `{{database}}.e6auj7k7_ccl_debug_events`
-- Params: `database`, `datetime_end`, `datetime_start`, `session_ids_block`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod investigation migration CSM-6: extracted from investigations/ctap-smvod/scripts/run_athena_debug_events.py

SELECT DISTINCT
  json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
  eventid,
  COALESCE(
    json_extract_scalar(eventdata, '$.eventtype'),
    json_extract_scalar(eventdata, '$.state')
  ) AS state,
  json_extract_scalar(eventdata, '$.position')          AS position,
  json_extract_scalar(eventdata, '$.errorcode')         AS errorcode,
  json_extract_scalar(eventdata, '$.errordescription')  AS errordescription,
  datetime
FROM "{{database}}"."e6auj7k7_ccl_debug_events"
WHERE eventid IN ('PLAYER_SESSION_EVENT', 'PLAYER_STATE_CHANGE', 'PLAYER_ERROR', 'PLAYER_POSITION', 'APP_KEEPALIVE')
  AND datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  AND json_extract_scalar(eventdata, '$.sessionid') IN (
{{session_ids_block}}
  )
ORDER BY sessionId, datetime;
