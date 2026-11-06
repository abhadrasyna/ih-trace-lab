-- Purpose: Shaka 6001 every debug-table event of the guests that were redirected to a browser to log in (guestLoginPrompt-redirect) on one UTC day.
-- Tables: `{{database}}.fact_navigation_interactions`, `{{database}}.{{debug_events_table}}`
-- Params: `database`, `date`, `debug_events_table`
-- Status: draft
-- Source:
--   - shaka-6001 investigation: investigations/shaka-6001/scripts/fetch_guest_login_redirects.py
-- Scan note: about 650 MB per UTC day for the debug-events table (ZA, 2026-11); the datetime range [date, date+1) is mandatory and bounds the scan.
--   The navigation side is filtered by the timestamp_formatted day prefix and event_source, so only that day's redirected guests are kept.
-- Join key: debug clientid is '<device_id>:<user_id>' where user_id is 'GUEST.<uuid>' (the debug table has no separate user column).
-- Output columns are fixed: datetime, clientid, eventclass, eventid, eventdata (header only when the day has no rows).

WITH guests AS (
    SELECT DISTINCT device_id || ':' || user_id AS clientid
    FROM "{{database}}"."fact_navigation_interactions"
    WHERE timestamp_formatted LIKE '{{date}}%'
      AND event_source = 'guestLoginPrompt-redirect'
)
SELECT
    d.datetime,
    d.clientid,
    d.eventclass,
    d.eventid,
    d.eventdata
FROM "{{database}}"."{{debug_events_table}}" d
JOIN guests g ON d.clientid = g.clientid
WHERE d.datetime >= '{{date}}T00:00:00.000Z'
  AND d.datetime <  date_format(date_add('day', 1, date '{{date}}'), '%Y-%m-%dT00:00:00.000Z')
ORDER BY d.clientid, d.datetime;
