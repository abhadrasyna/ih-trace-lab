-- Purpose: 14. Total unique-session counts across both tables, and the event_type filter trap
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `event_type`, `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 14. Total unique-session counts across both tables, and the event_type filter trap

-- Sessions present in unified_sessions but missing a REQUEST_VIEWING row
WITH all_sessions AS (
    SELECT DISTINCT parent_session_id AS sessionId
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted = {{timestamp_formatted}}
),
req_viewing AS (
    SELECT DISTINCT parent_session_id AS sessionId
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted = {{timestamp_formatted}}
      AND event_type = {{event_type}}
)
SELECT a.sessionId,
       (SELECT array_agg(DISTINCT event_type)
        FROM "unified_e6auj7k7"."unified_sessions" u
        WHERE u.parent_session_id = a.sessionId
          AND u.timestamp_formatted = {{timestamp_formatted}}) AS event_types_present
FROM all_sessions a
LEFT JOIN req_viewing r ON a.sessionId = r.sessionId
WHERE r.sessionId IS NULL;
