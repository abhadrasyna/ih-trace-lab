-- Purpose: 17. Full raw PLAYER event pull for a single session
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `eventclass`, `sessionid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 13. Root-cause investigation: "missing (no unified_sessions row)" sessions
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 17. Full raw PLAYER event pull for a single session
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 4. Single-session deep dive: e6auj7k7_ccl_debug_events

SELECT
  eventid,
  COALESCE(
    json_extract_scalar(eventdata, '$.eventtype'),  -- CREATE/DESTROY
    json_extract_scalar(eventdata, '$.state')       -- BUFFERING/PLAYING/PAUSED/STOPPED
  ) AS state,
  json_extract_scalar(eventdata, '$.errorcode')        AS errorcode,
  json_extract_scalar(eventdata, '$.errordescription') AS errordescription,
  datetime,
  eventdata
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventclass = {{eventclass}}
  AND json_extract_scalar(eventdata, '$.sessionid') = {{sessionid}}
ORDER BY datetime;
