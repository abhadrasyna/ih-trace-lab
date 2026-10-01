-- Purpose: 5. Finalized single-session outcome query (superseded — see §8 for the final aggregated version)
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `event_type`, `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 5. Finalized single-session outcome query (superseded — see §8 for the final aggregated version)
--   - ctap-smvod-session-report/queries/adoption.md :: 1. Unique HHs who attempted VOD Playback
--   - ctap-smvod-session-report/queries/adoption.md :: 2. VOD Playback Attempts (Sessions)

SELECT
  parent_session_id  AS sessionId,
  user_id             AS householdId,
  device_id           AS deviceId,
  endreason           AS playback_outcome,
  event_start,
  event_end
FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}}   -- e.g. '2026-07-08'
  AND event_type = {{event_type}};
