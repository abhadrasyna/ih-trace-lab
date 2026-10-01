-- Purpose: 27d. All events for one specific sessionId
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `sessionid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 17a. Every event, any eventclass, for a single sessionId (13 Jul 2026)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 27d. All events for one specific sessionId

SELECT
    datetime,
    eventclass,
    eventid,
    clientid,
    eventdata
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE json_extract_scalar(eventdata, '$.sessionid') = {{sessionid}}
ORDER BY datetime;
