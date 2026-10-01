-- Purpose: 14. Unique HHs who did NOT report any playback failure (VSF) — single day
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `endreason_pattern`, `event_type`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/adoption.md :: 14. Unique HHs who did NOT report any playback failure (VSF) — single day

WITH attempted AS (
    SELECT DISTINCT user_id
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}}
      AND event_type = {{event_type}}
),
vsf_hh AS (
    SELECT DISTINCT user_id
    FROM "unified_e6auj7k7"."unified_sessions"
    WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}}
      AND event_type = {{event_type}}
      AND endreason LIKE {{endreason_pattern}}
)
SELECT count(distinct a.user_id) AS unique_hh_no_vsf
FROM attempted a
LEFT JOIN vsf_hh v ON v.user_id = a.user_id
WHERE v.user_id IS NULL;
