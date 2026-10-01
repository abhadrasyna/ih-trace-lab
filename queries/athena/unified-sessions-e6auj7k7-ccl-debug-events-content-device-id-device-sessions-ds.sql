-- Purpose: 22h. Same device, richer output — attempted nested error-detail extraction (⚠️ likely bad JSON path)
-- Tables: `unified_e6auj7k7.unified_sessions`, `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `device_id`, `eventid`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22h. Same device, richer output — attempted nested error-detail extraction (⚠️ likely bad JSON path)

WITH device_sessions AS (
    SELECT DISTINCT
        parent_session_id,
        timestamp_formatted,
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
    json_extract_scalar(c.eventdata, '$.errorcode') AS errorcode,
    json_extract_scalar(c.eventdata, '$.errordescription.errordescription') AS error_description,
    json_extract_scalar(c.eventdata, '$.errordescription.user_agent') AS user_agent,
    c.eventdata
FROM device_sessions ds
LEFT JOIN "unified_e6auj7k7"."e6auj7k7_ccl_debug_events" c
    ON ds.parent_session_id =
       json_extract_scalar(c.eventdata, '$.sessionid')
WHERE c.eventid = {{eventid}}
ORDER BY ds.parent_session_id;
