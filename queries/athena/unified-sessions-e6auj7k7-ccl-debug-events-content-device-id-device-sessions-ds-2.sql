-- Purpose: 20a. Single device, all its PLAYER_ERROR sessions for the month
-- Tables: `unified_e6auj7k7.unified_sessions`, `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `device_id`, `eventid`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 20a. Single device, all its PLAYER_ERROR sessions for the month
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 20b. All devices, filtered to one specific errorcode (e.g. 6007)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 20c. All devices, all PLAYER_ERROR sessions for the month (no filter)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22g. e6auj7k7 — single-device PLAYER_ERROR history, device ba1cd944...

WITH device_sessions AS (
    SELECT DISTINCT
        parent_session_id,
        user_id,
        uid,
        device_id,
        content
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}}
      AND device_id = {{device_id}}
)

SELECT
    ds.parent_session_id,
    ds.user_id,
    ds.uid,
    ds.device_id,
    ds.content,
    CAST(json_extract_scalar(c.eventdata, '$.errorcode') AS INTEGER) AS errorcode,
    json_extract_scalar(c.eventdata, '$.errordescription') AS errordescription
FROM device_sessions ds
LEFT JOIN "unified_e6auj7k7"."e6auj7k7_ccl_debug_events" c
    ON ds.parent_session_id =
       json_extract_scalar(c.eventdata, '$.sessionid')
WHERE c.eventid = {{eventid}}
ORDER BY ds.parent_session_id;
