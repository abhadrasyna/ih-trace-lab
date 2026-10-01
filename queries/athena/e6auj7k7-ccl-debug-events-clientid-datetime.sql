-- Purpose: confirm session-level PLAYER_ERROR detail (errorcode, Shaka message, playback position) for every session found in Query 1.
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `clientid`, `datetime_end`, `datetime_start`
-- Status: confirmed-run
-- Source:
--   - applauseInvestigation/investigations/queries/QUERY_CATALOG.md :: Query 2 — e6auj7k7_ccl_debug_events, full PLAYER-class dump for the household

SELECT *
FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
WHERE datetime >= {{datetime_start}}
  AND datetime <  {{datetime_end}}
  AND clientid = {{clientid}}
ORDER BY event_timestamp;
