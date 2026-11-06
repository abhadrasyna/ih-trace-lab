-- Purpose: Shaka 6001 guest-login redirect rows (event_source guestLoginPrompt-redirect) for one UTC day, one row per distinct navigation event.
-- Tables: `{{database}}.fact_navigation_interactions`
-- Params: `database`, `date`
-- Status: draft
-- Source:
--   - shaka-6001 investigation: investigations/shaka-6001/scripts/fetch_guest_login_redirects.py
--   - extends queries/athena/fact-navigation-interactions-event-source-timestamp-formatted.sql
-- Scan note: filters on the timestamp_formatted day prefix (UTC) and the redirect event_source; the table is small compared to the debug-events table.
-- Output columns are fixed: fetch_guest_login_redirects.py writes them as <date>_guest_login_redirect.csv (header only when the day has no rows).

SELECT DISTINCT
    user_id,
    device_id,
    device_type,
    uid,
    nav_event_time,
    timestamp_formatted,
    navigation_start_time,
    navigation_end_time,
    nav_step_num,
    nav_step_total,
    nav_start_event,
    nav_end_event,
    start_reason,
    end_reason,
    event_type,
    event,
    event_code,
    event_source,
    event_source_ex,
    event_source_ex_name,
    source_name,
    event_details
FROM "{{database}}"."fact_navigation_interactions"
WHERE timestamp_formatted LIKE '{{date}}%'
  AND event_source = 'guestLoginPrompt-redirect'
ORDER BY timestamp_formatted, user_id, nav_step_num;
