-- Purpose: 23b. Combined VSF/EBVS/error single-query breakdown (one day, all three categories via CASE)
-- Tables: `unified_e6auj7k7.unified_sessions`
-- Params: `timestamp_formatted`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 23b. Combined VSF/EBVS/error single-query breakdown (one day, all three categories via CASE)

SELECT
    COUNT(DISTINCT CASE
        WHEN event_type = 'PLAY'
         AND endreason = 'PLAYER_ERROR'
        THEN uid
    END) AS error_users,

    COUNT(DISTINCT CASE
        WHEN event_type = 'REQUEST_VIEWING'
         AND endreason = 'PLAYER_ERROR'
        THEN uid
    END) AS vsf_users,

    COUNT(DISTINCT CASE
        WHEN event_type = 'REQUEST_VIEWING'
         AND endreason = 'DESTROY'
        THEN uid
    END) AS ebvs_users

FROM "unified_e6auj7k7"."unified_sessions"
WHERE timestamp_formatted = {{timestamp_formatted}};
