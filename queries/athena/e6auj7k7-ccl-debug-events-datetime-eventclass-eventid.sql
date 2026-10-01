-- Purpose: 6. Error-detail extraction with json_extract_scalar (as first-class columns, not Python JSON parsing)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 6. Error-detail extraction with json_extract_scalar (as first-class columns, not Python JSON parsing)

SELECT DISTINCT
  json_extract_scalar(eventdata, '$.sessionid')        AS sessionId,
  json_extract_scalar(eventdata, '$.errorcode')        AS errorcode,
  json_extract_scalar(eventdata, '$.errordescription') AS errordescription,
  datetime
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventclass = {{eventclass}}
  AND eventid = {{eventid}}
  AND datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}};
