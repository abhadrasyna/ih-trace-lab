-- Purpose: 22e. New tenant unified_bo1ghsjj — direct debug-event lookup by sessionid substring
-- Tables: `unified_bo1ghsjj.bo1ghsjj_ccl_debug_events`
-- Params: `eventdata_pattern`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22e. New tenant unified_bo1ghsjj — direct debug-event lookup by sessionid substring
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23e. Staging (bo1ghsjj) — all PLAYER_ERROR rows, unfiltered by session (plus a specific session lookup)

SELECT *
FROM "unified_bo1ghsjj"."bo1ghsjj_ccl_debug_events"
WHERE eventid = {{eventid}}
  AND eventdata like {{eventdata_pattern}};
