-- Purpose: 11. EBVS — unique HH per day, zero-filled
-- Tables: `unnest`, `unified_e6auj7k7.unified_sessions`
-- Params: `playback_outcome`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/adoption.md :: 11. EBVS — unique HH per day, zero-filled

WITH days AS (
    SELECT date_add('day', seq, DATE '2026-08-01') AS session_date
    FROM UNNEST(sequence(0, 30)) AS t(seq)   -- 0..30 = all 31 days of August
),
session_outcomes AS (
    SELECT
        parent_session_id,
        user_id,
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
    GROUP BY parent_session_id, user_id, timestamp_formatted
)
SELECT
    d.session_date,
    count(distinct so.user_id) AS ebvs_unique_hh
FROM days d
LEFT JOIN session_outcomes so
    ON date(so.session_date) = d.session_date
    AND so.playback_outcome = {{playback_outcome}}
GROUP BY d.session_date
ORDER BY d.session_date;
