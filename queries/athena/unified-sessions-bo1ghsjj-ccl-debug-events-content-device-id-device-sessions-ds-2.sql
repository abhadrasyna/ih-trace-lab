-- Purpose: 22f. New tenant unified_bo1ghsjj — single-device PLAYER_ERROR history (§20a pattern, bo1ghsjj tenant)
-- Tables: `unified_bo1ghsjj.unified_sessions`, `unified_bo1ghsjj.bo1ghsjj_ccl_debug_events`
-- Params: `device_id`, `eventid`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22f. New tenant unified_bo1ghsjj — single-device PLAYER_ERROR history (§20a pattern, bo1ghsjj tenant)

WITH device_sessions AS (
    SELECT DISTINCT
        parent_session_id,
        user_id,
        uid,
        device_id,
        content
    FROM "unified_bo1ghsjj"."unified_sessions"
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
LEFT JOIN "unified_bo1ghsjj"."bo1ghsjj_ccl_debug_events" c
    ON ds.parent_session_id =
       json_extract_scalar(c.eventdata, '$.sessionid')
WHERE c.eventid = {{eventid}}
ORDER BY ds.parent_session_id;
