-- Purpose: 22i. Raw debug-event lookup by sessionid substring (second example, e6auj7k7 tenant)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `eventdata_pattern`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22i. Raw debug-event lookup by sessionid substring (second example, e6auj7k7 tenant)

SELECT *
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventid = {{eventid}}
  AND eventdata like {{eventdata_pattern}};
