-- Purpose: 28a. Day-wise unique-session count for one errorcode (pivoted by day)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`
-- Params: `datetime_end`, `datetime_start`, `errorcode`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 19. Error-code-by-day pivot — daily count per errorcode for a month (13 Jul 2026)
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 28a. Day-wise unique-session count for one errorcode (pivoted by day)
--   - ctap-smvod-session-report/queries/adoption.md :: 8. Error-code-by-day pivot — daily count per errorcode for a month
--   - ctap-smvod-session-report/queries/adoption.md :: 9. Unique HH — errorcode-by-day pivot (unique household counts)

SELECT
  errorcode,
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-01' THEN sessionid END) AS "08-01",
  -- ... one COUNT(DISTINCT CASE WHEN day = DATE '2026-08-DD' THEN sessionid END) AS "08-DD" per day ...
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-31' THEN sessionid END) AS "08-31"
FROM (
  SELECT
    json_extract_scalar(eventdata, '$.errorcode') AS errorcode,
    json_extract_scalar(eventdata, '$.sessionid') AS sessionid,
    date(from_iso8601_timestamp(datetime)) AS day
  FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
  WHERE eventid = {{eventid}}
    AND datetime >= {{datetime_start}}
    AND datetime <  {{datetime_end}}
    AND json_extract_scalar(eventdata, '$.errorcode') = {{errorcode}}
)
GROUP BY errorcode
ORDER BY errorcode;
