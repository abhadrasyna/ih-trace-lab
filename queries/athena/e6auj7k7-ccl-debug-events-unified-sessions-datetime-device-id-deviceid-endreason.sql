-- Purpose: 3. Cross-check — did any hhid+deviceId combo hitting 4032 also have a successful playback?
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `datetime_end`, `datetime_start`, `endreason`, `event_type`, `eventid`
-- Status: drafted-not-yet-run
-- Source:
--   - ctap-smvod-session-report/queries/edge_4032_playback_failure.md :: 3. Cross-check — did any hhid+deviceId combo hitting 4032 also have a successful playback?

WITH impacted_sessions AS (
    SELECT DISTINCT json_extract_scalar(eventdata, '$.sessionid') AS session_id
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventid = {{eventid}}
      AND CAST(json_extract_scalar(eventdata, '$.errorcode') AS INTEGER) = 4032
      AND datetime >= {{datetime_start}}
      AND datetime <  {{datetime_end}}
),
impacted_pairs AS (
    SELECT DISTINCT us.user_id AS householdId, us.device_id AS deviceId
    FROM "unified_e6auj7k7"."unified_sessions" us
    JOIN impacted_sessions i ON us.parent_session_id = i.session_id
)
SELECT
    ip.householdId,
    ip.deviceId,
    MAX(CASE WHEN us.event_type = {{event_type}} AND us.endreason = {{endreason}}
             THEN 1 ELSE 0 END) AS had_successful_playback
FROM impacted_pairs ip
JOIN "unified_e6auj7k7"."unified_sessions" us
    ON us.user_id = ip.householdId AND us.device_id = ip.deviceId
WHERE us.timestamp_formatted = '2026-07-23'
GROUP BY ip.householdId, ip.deviceId
ORDER BY had_successful_playback DESC;
