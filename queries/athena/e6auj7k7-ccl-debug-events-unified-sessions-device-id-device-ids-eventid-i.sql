-- Purpose: 22b/22c. Same query, no error-code filter — every device with any PLAYER_ERROR this month
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `eventid`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22b/22c. Same query, no error-code filter — every device with any PLAYER_ERROR this month

WITH impacted_sessions AS (
    SELECT DISTINCT
        json_extract_scalar(eventdata, '$.sessionid') AS session_id
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventid = {{eventid}}
)

SELECT
    array_join(array_agg(DISTINCT us.device_id), ',') AS device_ids
FROM "unified_e6auj7k7"."unified_sessions" us
JOIN impacted_sessions i
    ON us.parent_session_id = i.session_id
WHERE us.timestamp_formatted LIKE {{timestamp_formatted_pattern}};
