-- Purpose: 10. VSF — unique HH per day, zero-filled
-- Tables: `unnest`, `unified_e6auj7k7.unified_sessions`
-- Params: `endreason_pattern`, `event_type`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/adoption.md :: 10. VSF — unique HH per day, zero-filled

WITH days AS (
    SELECT date_add('day', seq, DATE '2026-08-01') AS session_date
    FROM UNNEST(sequence(0, 30)) AS t(seq)   -- 0..30 = all 31 days of July
)
SELECT
    d.session_date,
    count(distinct s.user_id) AS unique_hh_attempted_vod
FROM days d
LEFT JOIN "unified_e6auj7k7"."unified_sessions" s
    ON date(s.timestamp_formatted) = d.session_date
    AND s.event_type = {{event_type}}
    AND s.endreason LIKE {{endreason_pattern}}
GROUP BY d.session_date
ORDER BY d.session_date;
