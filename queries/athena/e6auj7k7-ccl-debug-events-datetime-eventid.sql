-- Purpose: 9. Ad-hoc: eventid distribution for the day
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 9. Ad-hoc: eventid distribution for the day

SELECT eventid, COUNT(*)
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}}
GROUP BY eventid;
