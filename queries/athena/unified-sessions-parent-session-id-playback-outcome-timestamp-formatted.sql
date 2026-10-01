-- Purpose: 5. Exit Before Video Starts (EBVS) Sessions
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `playback_outcome`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/adoption.md :: 5. Exit Before Video Starts (EBVS) Sessions

SELECT
    date(session_date) AS session_date,
    count(distinct parent_session_id) AS ebvs_sessions
FROM (
    SELECT
        parent_session_id,
        timestamp_formatted AS session_date,
        COALESCE(
            MAX(CASE WHEN event_type = 'PLAY' THEN endreason END),
            CASE WHEN MAX(CASE WHEN endreason = 'DESTROY' THEN 1 ELSE 0 END) = 1
                 THEN 'EBVS'
                 ELSE 'INCOMPLETE_NO_DESTROY'
            END
        ) AS playback_outcome
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}}
    GROUP BY parent_session_id, timestamp_formatted
)
WHERE playback_outcome = {{playback_outcome}}
GROUP BY 1
ORDER BY 1;
