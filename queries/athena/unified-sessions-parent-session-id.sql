-- Purpose: 18. Full unified_sessions pull for a single sessionId (13 Jul 2026)
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `parent_session_id`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 13. Root-cause investigation: "missing (no unified_sessions row)" sessions
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 18. Full unified_sessions pull for a single sessionId (13 Jul 2026)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 3. Single-session deep dive: unified_sessions

SELECT
  parent_session_id,
  event_type,
  event_start,
  event_end,
  endreason,
  device_id,
  user_id,
  content_id,
  ip_address,
  country,
  timestamp_formatted
FROM "unified_e6auj7k7"."unified_sessions"
WHERE parent_session_id = {{parent_session_id}}
ORDER BY event_start;
