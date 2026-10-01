-- Purpose: 16. Debug-table completeness check for §15 sessions — CREATE->PLAYING->DESTROY
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 16. Debug-table completeness check for §15 sessions — CREATE->PLAYING->DESTROY

WITH session_states AS (
    SELECT DISTINCT
        json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
        COALESCE(
            json_extract_scalar(eventdata, '$.eventtype'),  -- CREATE/DESTROY
            json_extract_scalar(eventdata, '$.state')       -- BUFFERING/PLAYING/PAUSED/STOPPED
        ) AS state,
        datetime
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventclass = {{eventclass}}
      AND eventid IN ('PLAYER_SESSION_EVENT', 'PLAYER_STATE_CHANGE', 'PLAYER_ERROR')
      AND datetime >= {{datetime_start}}   -- e.g. '2026-07-07T00:00:00.000Z'
      AND datetime <  {{datetime_end}}     -- e.g. '2026-07-08T00:00:00.000Z'
      AND json_extract_scalar(eventdata, '$.sessionid') IN (
          -- paste the §15 parent_session_id list here
      )
)
SELECT
    sessionId,
    array_agg(state ORDER BY datetime) AS state_sequence
FROM session_states
GROUP BY sessionId
HAVING SUM(CASE WHEN state = 'CREATE'   THEN 1 ELSE 0 END) > 0
   AND SUM(CASE WHEN state = 'PLAYING'  THEN 1 ELSE 0 END) > 0
   AND SUM(CASE WHEN state = 'DESTROY'  THEN 1 ELSE 0 END) > 0
ORDER BY sessionId;
