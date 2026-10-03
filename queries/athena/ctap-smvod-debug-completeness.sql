-- Purpose: Follow-up completeness check for sessions stuck in PLAYING with no PLAY row, verifying CREATE->PLAYING->DESTROY lifecycle in debug events.
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `eventclass`, `session_ids_block`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod investigation migration CSM-6: extracted from investigations/ctap-smvod/scripts/build_debug_completeness_query.py

WITH session_states AS (
    SELECT DISTINCT
        json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
        COALESCE(
            json_extract_scalar(eventdata, '$.eventtype'),
            json_extract_scalar(eventdata, '$.state')
        ) AS state,
        datetime
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventclass = '{{eventclass}}'
      AND eventid IN ('PLAYER_SESSION_EVENT', 'PLAYER_STATE_CHANGE', 'PLAYER_ERROR')
      AND datetime >= '{{datetime_start}}'
      AND datetime <  '{{datetime_end}}'
      AND json_extract_scalar(eventdata, '$.sessionid') IN (
{{session_ids_block}}
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
