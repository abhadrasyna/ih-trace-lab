-- Purpose: 26. Empty/null contentid investigation on e6auj7k7_ccl_debug_events (30 Jul 2026)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 10. Broad eventclass='PLAYER' sample (6 sessions) — confirms §6/§7 scope is sufficient
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 26. Empty/null contentid investigation on e6auj7k7_ccl_debug_events (30 Jul 2026)

SELECT
  json_extract_scalar(eventdata, '$.sessionid')        AS sessionId,
  split_part(clientid, ':', 2)                          AS householdId,
  eventclass,
  eventid,
  json_extract_scalar(eventdata, '$.eventtype')        AS eventType,
  json_extract_scalar(eventdata, '$.state')            AS state,
  json_extract_scalar(eventdata, '$.errorcode')        AS errorcode,
  json_extract_scalar(eventdata, '$.errordescription') AS errordescription,
  datetime
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventclass = {{eventclass}}
  AND datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}}
  AND (
    COALESCE(
      json_extract_scalar(eventdata, '$.contentid'),
      json_extract_scalar(eventdata, '$.contentmetadata.contentid')
    ) IS NULL
    OR
    COALESCE(
      json_extract_scalar(eventdata, '$.contentid'),
      json_extract_scalar(eventdata, '$.contentmetadata.contentid')
    ) = ''
  )
ORDER BY sessionId, datetime;
