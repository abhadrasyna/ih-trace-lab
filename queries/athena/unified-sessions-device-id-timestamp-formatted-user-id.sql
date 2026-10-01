-- Purpose: confirm session-level outcome (endreason) across the full day for the ticket's device, not just the two reported repro times, since the Lightstep pass found the failure signature recurring all day.
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `device_id`, `timestamp_formatted`, `user_id`
-- Status: confirmed-run
-- Source:
--   - applauseInvestigation/investigations/queries/QUERY_CATALOG.md :: Query 1 — unified_sessions, full row dump for this device
--   - applauseInvestigation/investigations/queries/QUERY_CATALOG.md :: Query 1 — unified_sessions, full row dump for this device

SELECT *
FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}}
  AND user_id = {{user_id}}
  AND device_id = {{device_id}}
ORDER BY event_start;
