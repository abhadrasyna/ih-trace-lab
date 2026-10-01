-- Purpose: 23c. New table: e6auj7k7_ccl_debug_events_jun26 — monthly-suffixed debug-events variant
-- Tables: `unified_e6auj7k7.unified_sessions`, `unified_e6auj7k7.e6auj7k7_ccl_debug_events_jun26`
-- Params: `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23c. New table: e6auj7k7_ccl_debug_events_jun26 — monthly-suffixed debug-events variant

SELECT
    json_extract_scalar(e.eventdata, '$.errorcode') AS errorcode,
    COUNT(DISTINCT s.uid) AS affected_uids
FROM "unified_e6auj7k7"."unified_sessions" s
JOIN "unified_e6auj7k7"."e6auj7k7_ccl_debug_events_jun26" e
    ON s.parent_session_id = json_extract_scalar(e.eventdata, '$.sessionid')
WHERE s.timestamp_formatted LIKE {{timestamp_formatted_pattern}}
  AND s.endreason IN ('DESTROY', 'PLAYER_ERROR')
  AND s.event_type IN ('REQUEST_VIEWING')
  AND e.eventid IN ('DESTROY', 'PLAYER_ERROR')
GROUP BY json_extract_scalar(e.eventdata, '$.errorcode')
ORDER BY affected_uids DESC;
