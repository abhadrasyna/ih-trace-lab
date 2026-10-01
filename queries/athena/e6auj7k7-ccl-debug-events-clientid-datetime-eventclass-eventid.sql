-- Purpose: 29c. Debug-table errorcode lookup by hhid (query only, not yet run)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `clientid_pattern`, `datetime_end`, `datetime_start`, `eventclass`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 29c. Debug-table errorcode lookup by hhid (query only, not yet run)

-- All PLAYER_ERROR rows for a specific hhid
SELECT
  json_extract_scalar(eventdata, '$.sessionid')        AS sessionId,
  clientid,
  eventclass,
  eventid,
  json_extract_scalar(eventdata, '$.eventtype')        AS eventType,
  json_extract_scalar(eventdata, '$.state')            AS state,
  json_extract_scalar(eventdata, '$.errorcode')        AS errorcode,
  json_extract_scalar(eventdata, '$.errordescription') AS errordescription,
  datetime
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventclass = {{eventclass}}
  AND eventid = {{eventid}}
  AND clientid LIKE {{clientid_pattern}}
  AND datetime >= {{datetime_start}}   -- placeholder range, adjust
  AND datetime <  {{datetime_end}}
ORDER BY datetime;
