-- Purpose: 23a. Single-day unique-user counts, individual outcome categories
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `endreason_pattern`, `event_type`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 21a. Daily successful (DESTROY) session count trend for the month
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 21d. Content lookup — distinct content/content_id for June, PLAYER_ERROR or DESTROY sessions
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23a. Single-day unique-user counts, individual outcome categories
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23d. Device list impacted on a single day, REQUEST_VIEWING outcome only
--   - ctap-smvod-session-report/queries/adoption.md :: 12. Successful VOD Playback — unique HH per day
--   - ctap-smvod-session-report/queries/adoption.md :: 3. Successful VOD Playback Sessions
--   - ctap-smvod-session-report/queries/adoption.md :: 4. VOD Playback Error Reported (VSF) Sessions

SELECT count(distinct uid) FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted like {{timestamp_formatted_pattern}} AND event_type = {{event_type}} AND endreason like {{endreason_pattern}};

SELECT count(distinct uid) FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted like {{timestamp_formatted_pattern}} AND event_type = {{event_type}} AND endreason like {{endreason_pattern}};

SELECT count(distinct uid) FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted like {{timestamp_formatted_pattern}} AND event_type = {{event_type}} AND endreason like {{endreason_pattern}};
