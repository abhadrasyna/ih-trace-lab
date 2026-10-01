-- Purpose: 22j. Direct unified_sessions filter — device + endreason = 'PLAYER_ERROR'
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `device_id_pattern`, `endreason_pattern`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 22j. Direct unified_sessions filter — device + endreason = 'PLAYER_ERROR'

SELECT * FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted like {{timestamp_formatted_pattern}}
  AND endreason like {{endreason_pattern}}
  and device_id like {{device_id_pattern}}
limit 10
