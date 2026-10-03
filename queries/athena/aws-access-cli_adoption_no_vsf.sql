WITH attempted AS (
    SELECT DISTINCT user_id, {{session_date_expr}} AS session_date
    FROM "{{database_identifier}}"."unified_sessions"
    WHERE date(timestamp_formatted) >= date '{{start_date}}'
      AND date(timestamp_formatted) < date '{{end_date_exclusive}}'
      AND event_type = 'REQUEST_VIEWING'
),
vsf_hh AS (
    SELECT DISTINCT user_id, {{session_date_expr}} AS session_date
    FROM "{{database_identifier}}"."unified_sessions"
    WHERE date(timestamp_formatted) >= date '{{start_date}}'
      AND date(timestamp_formatted) < date '{{end_date_exclusive}}'
      AND event_type = 'REQUEST_VIEWING'
      AND endreason LIKE 'PLAYER_ERROR'
)
SELECT
    a.session_date AS session_date,
    count(distinct a.user_id) AS metric_value
FROM attempted a
LEFT JOIN vsf_hh v
  ON v.user_id = a.user_id AND v.session_date = a.session_date
WHERE v.user_id IS NULL
GROUP BY a.session_date
ORDER BY a.session_date;
