-- Purpose: CTAP/SM-VOD presence check: row counts per sessionId in unified_sessions and in the debug-events table.
-- Tables: `{{database}}.unified_sessions`, `{{database}}.{{debug_events_table}}`
-- Params: `database`, `date_end`, `date_start`, `datetime_end`, `datetime_start`, `debug_events_table`, `session_ids_block`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod investigation: why do no_request / no_error sessions have no playback_outcome (outcome_missing)? Run on GH 2026-10-23.

SELECT
  'unified_sessions' AS source,
  parent_session_id AS sessionId,
  COUNT(*) AS row_count,
  array_join(array_sort(array_distinct(array_agg(event_type))), ',') AS kinds,
  CAST(MIN(timestamp_formatted) AS varchar) AS first_seen
FROM "{{database}}"."unified_sessions"
WHERE timestamp_formatted >= '{{date_start}}'
  AND timestamp_formatted <= '{{date_end}}'
  AND parent_session_id IN (
{{session_ids_block}}
  )
GROUP BY parent_session_id

UNION ALL

SELECT
  'debug_events' AS source,
  json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
  COUNT(*) AS row_count,
  array_join(array_sort(array_distinct(array_agg(eventid))), ',') AS kinds,
  MIN(datetime) AS first_seen
FROM "{{database}}"."{{debug_events_table}}"
WHERE datetime >= '{{datetime_start}}'
  AND datetime <  '{{datetime_end}}'
  AND json_extract_scalar(eventdata, '$.sessionid') IN (
{{session_ids_block}}
  )
GROUP BY json_extract_scalar(eventdata, '$.sessionid')
ORDER BY sessionId, source;
