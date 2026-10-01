-- Purpose: 12a. e6auj7k7_ccl_debug_events — full-row duplicate check (eventclass='PLAYER') — **canonical duplicate-count query**
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`, `eventdata`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 11. Combined lifecycle + error query — state_sequence enrichment
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 12a. e6auj7k7_ccl_debug_events — full-row duplicate check (eventclass='PLAYER') — **canonical duplicate-count query**
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 7. Filtering by all known sessionIds (IN (...))
--   - ctap-smvod-session-report/queries/edge_4032_playback_failure.md :: 1. Daily count of errorcode 4032

SELECT
  datetime, messageid, clibversion, clientid, eventclass, eventid, eventdata
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventclass = {{eventclass}}
  AND eventid = {{eventid}}
  AND eventdata = {{eventdata}}
  AND datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}}
ORDER BY datetime, messageid;
