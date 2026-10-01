-- Purpose: 27c. One row per session_id, with error detail (latest occurrence)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `errorcode`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 11b. Adding APP_KEEPALIVE — recovering position signal missed by the eventclass = 'PLAYER' filter (13 Jul 2026)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 27a. All PLAYER_ERROR rows for one errorcode on one day
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 27b. Unique session_id list only
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 27c. One row per session_id, with error detail (latest occurrence)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 28b. Raw full-column pull for one errorcode across a date range
--   - ctap-smvod-session-report/queries/edge_4032_playback_failure.md :: 2. Unique household count facing errorcode 4032

SELECT
    json_extract_scalar(eventdata, '$.sessionid')        AS session_id,
    json_extract_scalar(eventdata, '$.errorcode')        AS error_code,
    json_extract_scalar(eventdata, '$.errordescription') AS error_description,
    MAX(datetime) AS datetime
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE eventid = {{eventid}}
  AND json_extract_scalar(eventdata, '$.errorcode') = {{errorcode}}
  AND datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}}
GROUP BY
    json_extract_scalar(eventdata, '$.sessionid'),
    json_extract_scalar(eventdata, '$.errorcode'),
    json_extract_scalar(eventdata, '$.errordescription')
;
