-- Purpose: 12b. unified_sessions — duplicate check
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 12b. unified_sessions — duplicate check

SELECT
  parent_session_id,
  event_type,
  event_start,
  event_end,
  endreason,
  COUNT(*) AS dup_count
FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}}
GROUP BY parent_session_id, event_type, event_start, event_end, endreason
HAVING COUNT(*) > 1
ORDER BY dup_count DESC;
