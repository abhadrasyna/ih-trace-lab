-- Purpose: CTAP/SM-VOD raw PLAYER_ERROR debug events (full eventdata JSON, messageid, clientid) for one day, input to flatten_error_eventdata.py.
-- Tables: `{{database}}.{{debug_events_table}}`
-- Params: `database`, `datetime_end`, `datetime_start`, `debug_events_table`, `error_code_filter`
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/run_athena_error_eventdata.py (`error_code_filter` is empty or an `AND ... IN (...)` clause)

SELECT
  datetime,
  messageid,
  clibversion,
  clientid,
  eventclass,
  eventid,
  eventdata
FROM "{{database}}"."{{debug_events_table}}"
WHERE eventid = 'PLAYER_ERROR'
  AND datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  {{error_code_filter}}
ORDER BY datetime;
