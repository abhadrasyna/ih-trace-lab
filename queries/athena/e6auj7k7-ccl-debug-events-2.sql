-- Purpose: 22k. eventclass distribution across the whole debug-events table
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: —
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 2. Sample rows (both tables)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22k. eventclass distribution across the whole debug-events table

SELECT eventclass, count(*) FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events" group by 1 order by 1 limit 10
