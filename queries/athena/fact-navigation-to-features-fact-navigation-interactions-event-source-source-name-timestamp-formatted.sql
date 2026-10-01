-- Purpose: 21c. Home-screen navigation — raw row sample and exploration
-- Tables: `unified_e6auj7k7.fact_navigation_to_features`, `unified_e6auj7k7.fact_navigation_interactions`
-- Params: `event_source`, `source_name`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 21c. Home-screen navigation — raw row sample and exploration

SELECT * FROM "unified_e6auj7k7"."fact_navigation_to_features"
WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}} and source_name = {{source_name}} limit 10;

SELECT * FROM "unified_e6auj7k7"."fact_navigation_interactions"
WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}} event_source = {{event_source}} limit 100;

SELECT count(distinct user_id) FROM "unified_e6auj7k7"."fact_navigation_interactions"
WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}} and event_source = {{event_source}} limit 100;
-- gives 83
