-- Purpose: 21b. Home-screen navigation — unique households per day (fact_navigation_interactions)
-- Tables: `unified_e6auj7k7.fact_navigation_interactions`
-- Params: `event_source`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 21b. Home-screen navigation — unique households per day (fact_navigation_interactions)
--   - ctap-smvod-session-report/queries/adoption.md :: 13. Guest login funnel — datewise unique HH count per event (fact_navigation_interactions)
--   - ctap-smvod-session-report/queries/adoption.md :: 6. Home-screen navigation — unique households per day (fact_navigation_interactions)

SELECT
    date(timestamp_formatted) AS session_date,
    count(distinct user_id) AS unique_hhid
FROM "unified_e6auj7k7"."fact_navigation_interactions"
WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}}
  and event_source = {{event_source}}
GROUP BY 1
ORDER BY 1;
