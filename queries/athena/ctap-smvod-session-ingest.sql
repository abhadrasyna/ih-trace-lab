-- Purpose: CTAP/SM-VOD one row per session with its earliest event_start and earliest ingest_timestamp (when the row landed in Athena), input to chart_playback_attempts.py --time-field ingest.
-- Tables: `{{database}}.unified_sessions`
-- Params: `database`, `date`, `date_start` (the partition is by event date, so the day before `date` is included to catch sessions ingested on `date`)
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/run_athena_session_ingest.py

SELECT
  parent_session_id AS sessionId,
  MIN(event_start) AS event_start,
  MIN(ingest_timestamp) AS ingest_timestamp
FROM "{{database}}"."unified_sessions"
WHERE timestamp_formatted BETWEEN '{{date_start}}' AND '{{date}}'
GROUP BY parent_session_id;
