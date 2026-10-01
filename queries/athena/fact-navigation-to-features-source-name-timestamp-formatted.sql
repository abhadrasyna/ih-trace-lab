-- Purpose: 7. Home-screen navigation — raw row sample (fact_navigation_to_features)
-- Tables: `unified_e6auj7k7.fact_navigation_to_features`
-- Params: `source_name`, `timestamp_formatted_pattern`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/adoption.md :: 7. Home-screen navigation — raw row sample (fact_navigation_to_features)

SELECT * FROM "unified_e6auj7k7"."fact_navigation_to_features"
WHERE timestamp_formatted LIKE {{timestamp_formatted_pattern}} AND source_name = {{source_name}} LIMIT 10;
