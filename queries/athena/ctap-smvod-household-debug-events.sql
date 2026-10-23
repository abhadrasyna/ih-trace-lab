-- Purpose: CTAP/SM-VOD every debug event (all eventclass/eventid, full eventdata JSON) for known household/device pairs over a date range.
-- Tables: `{{database}}.{{debug_events_table}}`
-- Params: `client_ids_block`, `database`, `datetime_end`, `datetime_start`, `debug_events_table`
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/run_athena_household_debug_events.py (clientid is '<deviceId>:<householdId>')

SELECT
  datetime,
  messageid,
  clibversion,
  clientid,
  eventclass,
  eventid,
  eventdata
FROM "{{database}}"."{{debug_events_table}}"
WHERE datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  AND clientid IN (
{{client_ids_block}}
  )
ORDER BY datetime;
