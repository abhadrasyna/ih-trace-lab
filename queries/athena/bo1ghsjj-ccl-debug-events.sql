-- Purpose: 22l. Staging (bo1ghsjj) — raw row sample from the debug-events table (⚠️ syntax bug)
-- Tables: `unified_bo1ghsjj.bo1ghsjj_ccl_debug_events`
-- Params: —
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22l. Staging (bo1ghsjj) — raw row sample from the debug-events table (⚠️ syntax bug)

SELECT * FROM "unified_bo1ghsjj"."bo1ghsjj_ccl_debug_events" limit 10;
