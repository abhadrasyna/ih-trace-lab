-- Purpose: 22a. Which devices were impacted by specific error codes (1003, 7000)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `eventid`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22a. Which devices were impacted by specific error codes (1003, 7000)

WITH impacted_sessions AS (
    SELECT DISTINCT
        json_extract_scalar(eventdata, '$.sessionid') AS session_id
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventid = {{eventid}}
      AND CAST(json_extract_scalar(eventdata, '$.errorcode') AS INTEGER) IN (1003, 7000)
)

SELECT
    array_join(array_agg(DISTINCT us.device_id), ',') AS device_ids
FROM "unified_e6auj7k7"."unified_sessions" us
JOIN impacted_sessions i
    ON us.parent_session_id = i.session_id
WHERE us.timestamp_formatted LIKE {{timestamp_formatted_pattern}};
