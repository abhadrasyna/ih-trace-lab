-- Purpose: 14. Total unique-session counts across both tables, and the event_type filter trap
-- Tables: `unified_e6auj7k7.unified_sessions`, `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`, `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 14. Total unique-session counts across both tables, and the event_type filter trap

-- Total unique sessions seen in EITHER table for a given day
WITH unified AS (
    SELECT DISTINCT parent_session_id AS sessionId
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted = {{timestamp_formatted}}
),
debug AS (
    SELECT DISTINCT json_extract_scalar(eventdata, '$.sessionid') AS sessionId
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventclass = {{eventclass}}
      AND datetime >= {{datetime_start}}
      AND datetime <  {{datetime_end}}
)
SELECT COUNT(*) AS total_unique_sessions
FROM (SELECT sessionId FROM unified UNION SELECT sessionId FROM debug) combined;
