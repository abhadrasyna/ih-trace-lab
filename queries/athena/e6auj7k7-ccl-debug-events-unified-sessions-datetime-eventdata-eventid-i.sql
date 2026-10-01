-- Purpose: 2. Unique household count facing errorcode 4032
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `datetime_end`, `datetime_start`, `eventid`, `timestamp_formatted`
-- Status: drafted-not-yet-run
-- Source:
--   - ctap-smvod-session-report/queries/edge_4032_playback_failure.md :: 2. Unique household count facing errorcode 4032

WITH impacted_sessions AS (
    SELECT DISTINCT
        json_extract_scalar(eventdata, '$.sessionid') AS session_id
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventid = {{eventid}}
      AND CAST(json_extract_scalar(eventdata, '$.errorcode') AS INTEGER) = 4032
      AND datetime >= {{datetime_start}}
      AND datetime <  {{datetime_end}}
)

SELECT
    COUNT(DISTINCT us.user_id) AS unique_hhid
FROM "unified_e6auj7k7"."unified_sessions" us
JOIN impacted_sessions i
    ON us.parent_session_id = i.session_id
WHERE us.timestamp_formatted = {{timestamp_formatted}};
