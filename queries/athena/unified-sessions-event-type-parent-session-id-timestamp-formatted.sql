-- Purpose: 12b. unified_sessions — duplicate check
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `event_type`, `parent_session_id`, `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 12b. unified_sessions — duplicate check

SELECT *
FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}}
  AND parent_session_id = {{parent_session_id}}
  AND event_type = {{event_type}}
ORDER BY event_start;
