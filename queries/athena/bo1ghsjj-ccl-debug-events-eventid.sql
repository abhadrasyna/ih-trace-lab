-- Purpose: 23e. Staging (bo1ghsjj) — all PLAYER_ERROR rows, unfiltered by session (plus a specific session lookup)
-- Tables: `unified_bo1ghsjj.bo1ghsjj_ccl_debug_events`
-- Params: `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23e. Staging (bo1ghsjj) — all PLAYER_ERROR rows, unfiltered by session (plus a specific session lookup)

SELECT * FROM "unified_bo1ghsjj"."bo1ghsjj_ccl_debug_events" WHERE eventid = {{eventid}}
