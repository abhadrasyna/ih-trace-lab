-- Purpose: 30b. Household overlap between E31012 and 1003 (full August)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `datetime_end`, `datetime_start`, `errorcode`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 30b. Household overlap between E31012 and 1003 (full August)

WITH e31012_hh AS (
  SELECT DISTINCT u.user_id AS householdId
  FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events" e
  JOIN "unified_e6auj7k7"."unified_sessions" u
    ON u.parent_session_id = json_extract_scalar(e.eventdata, '$.sessionid')
  WHERE e.eventid = {{eventid}}
    AND json_extract_scalar(e.eventdata, '$.errorcode') = {{errorcode}}
    AND e.datetime >= {{datetime_start}} AND e.datetime < {{datetime_end}}
),
e1003_hh AS (
  SELECT DISTINCT u.user_id AS householdId
  FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events" e
  JOIN "unified_e6auj7k7"."unified_sessions" u
    ON u.parent_session_id = json_extract_scalar(e.eventdata, '$.sessionid')
  WHERE e.eventid = {{eventid}}
    AND json_extract_scalar(e.eventdata, '$.errorcode') = {{errorcode}}
    AND e.datetime >= {{datetime_start}} AND e.datetime < {{datetime_end}}
)
SELECT householdId FROM e31012_hh INTERSECT SELECT householdId FROM e1003_hh;
