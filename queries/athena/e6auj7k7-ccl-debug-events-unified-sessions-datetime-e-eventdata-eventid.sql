-- Purpose: 30a. Day-wise unique-session count per household, full August (pivoted by day)
-- Tables: `unified_e6auj7k7.e6auj7k7_ccl_debug_events`, `unified_e6auj7k7.unified_sessions`
-- Params: `datetime_end`, `datetime_start`, `errorcode`, `eventid`
-- Status: confirmed-run
-- Source:
--   - ctap-smvod-session-report/queries/QUERY_CATALOG.md :: 30a. Day-wise unique-session count per household, full August (pivoted by day)

SELECT
  user_id AS householdId,
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-01' THEN sessionid END) AS "08-01",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-02' THEN sessionid END) AS "08-02",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-03' THEN sessionid END) AS "08-03",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-04' THEN sessionid END) AS "08-04",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-05' THEN sessionid END) AS "08-05",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-06' THEN sessionid END) AS "08-06",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-07' THEN sessionid END) AS "08-07",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-08' THEN sessionid END) AS "08-08",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-09' THEN sessionid END) AS "08-09",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-10' THEN sessionid END) AS "08-10",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-11' THEN sessionid END) AS "08-11",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-12' THEN sessionid END) AS "08-12",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-13' THEN sessionid END) AS "08-13",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-14' THEN sessionid END) AS "08-14",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-15' THEN sessionid END) AS "08-15",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-16' THEN sessionid END) AS "08-16",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-17' THEN sessionid END) AS "08-17",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-18' THEN sessionid END) AS "08-18",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-19' THEN sessionid END) AS "08-19",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-20' THEN sessionid END) AS "08-20",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-21' THEN sessionid END) AS "08-21",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-22' THEN sessionid END) AS "08-22",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-23' THEN sessionid END) AS "08-23",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-24' THEN sessionid END) AS "08-24",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-25' THEN sessionid END) AS "08-25",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-26' THEN sessionid END) AS "08-26",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-27' THEN sessionid END) AS "08-27",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-28' THEN sessionid END) AS "08-28",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-29' THEN sessionid END) AS "08-29",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-30' THEN sessionid END) AS "08-30",
  COUNT(DISTINCT CASE WHEN day = DATE '2026-08-31' THEN sessionid END) AS "08-31",
  COUNT(DISTINCT sessionid)  AS total_sessions,
  COUNT(DISTINCT day)        AS distinct_days_affected
FROM (
  SELECT
    e.sessionid,
    u.user_id,
    date(from_iso8601_timestamp(e.datetime)) AS day
  FROM (
    SELECT
      json_extract_scalar(eventdata, '$.sessionid') AS sessionid,
      datetime
    FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
    WHERE eventid = {{eventid}}
      AND json_extract_scalar(eventdata, '$.errorcode') = {{errorcode}}
      AND datetime >= {{datetime_start}}
      AND datetime <  {{datetime_end}}
  ) e
  JOIN "unified_e6auj7k7"."unified_sessions" u
    ON u.parent_session_id = e.sessionid
)
GROUP BY user_id
ORDER BY distinct_days_affected DESC, total_sessions DESC;
