-- Purpose: CTAP/SM-VOD one row per sessionid for one day with its bandwidth signals (Shaka estimate and navigator.connection on PLAYER_ERROR, ABR bitrate on PLAYER_TRACK_CHANGE) and buffering signals (PLAYER_BUFFER_LEVEL, PLAYER_STATE_CHANGE), input to analyze_bandwidth_vs_failure.py.
-- Tables: `{{database}}.{{debug_events_table}}`
-- Params: `database`, `datetime_end`, `datetime_start`, `debug_events_table`
-- Status: draft
-- Source:
--   - ctap-smvod investigation: investigations/ctap-smvod/scripts/run_athena_session_bandwidth.py (estimatedbandwidthmbps is only logged on PLAYER_ERROR, so healthy sessions have no Shaka estimate; healthy sessions only have the ABR bitrate from PLAYER_TRACK_CHANGE)

WITH ev AS (
  SELECT eventid, datetime, json_extract_scalar(eventdata, '$.sessionid') AS sid, eventdata
  FROM "{{database}}"."{{debug_events_table}}"
  WHERE datetime >= '{{datetime_start}}'
    AND datetime <  '{{datetime_end}}'
    AND eventid IN ('PLAYER_ERROR', 'PLAYER_BUFFER_LEVEL', 'PLAYER_STATE_CHANGE', 'PLAYER_TRACK_CHANGE')
), span AS (
  SELECT sid, min(datetime) AS first_event FROM ev GROUP BY sid
), err AS (
  SELECT sid,
    min_by(json_extract_scalar(eventdata, '$.errorcode'), datetime) AS first_errorcode,
    min(datetime) AS first_error,
    count(*) AS error_events,
    min(try_cast(json_extract_scalar(eventdata, '$.errordescription.networkdetails.shakastats.estimatedbandwidthmbps') AS double)) AS est_bw_mbps_min,
    max(try_cast(json_extract_scalar(eventdata, '$.errordescription.networkdetails.shakastats.estimatedbandwidthmbps') AS double)) AS est_bw_mbps_max,
    max(try_cast(json_extract_scalar(eventdata, '$.errordescription.networkdetails.shakastats.streambandwidthmbps') AS double)) AS stream_bw_mbps,
    max(json_extract_scalar(eventdata, '$.errordescription.networkdetails.navigatorconnection.effectivetype')) AS nav_effectivetype,
    max(try_cast(json_extract_scalar(eventdata, '$.errordescription.networkdetails.navigatorconnection.downlink') AS double)) AS nav_downlink_mbps,
    max(try_cast(json_extract_scalar(eventdata, '$.errordescription.networkdetails.navigatorconnection.rtt') AS double)) AS nav_rtt_ms
  FROM ev WHERE eventid = 'PLAYER_ERROR' GROUP BY sid
), buf AS (
  SELECT sid,
    count(*) AS buffer_samples,
    min(try_cast(json_extract_scalar(eventdata, '$.level.cur') AS double)) AS buf_cur_min,
    avg(try_cast(json_extract_scalar(eventdata, '$.level.cur') AS double)) AS buf_cur_avg,
    max_by(try_cast(json_extract_scalar(eventdata, '$.level.cur') AS double), datetime) AS buf_cur_last
  FROM ev WHERE eventid = 'PLAYER_BUFFER_LEVEL' GROUP BY sid
), st AS (
  SELECT sid,
    count(*) AS state_events,
    count_if(json_extract_scalar(eventdata, '$.state') = 'BUFFERING') AS buffering_events
  FROM ev WHERE eventid = 'PLAYER_STATE_CHANGE' GROUP BY sid
), tc AS (
  SELECT sid,
    count(*) AS track_changes,
    min(try_cast(json_extract_scalar(eventdata, '$.bitrate') AS double)) / 1000000 AS abr_bitrate_mbps_min,
    max(try_cast(json_extract_scalar(eventdata, '$.bitrate') AS double)) / 1000000 AS abr_bitrate_mbps_max,
    avg(try_cast(json_extract_scalar(eventdata, '$.bitrate') AS double)) / 1000000 AS abr_bitrate_mbps_avg
  FROM ev WHERE eventid = 'PLAYER_TRACK_CHANGE' GROUP BY sid
)
SELECT
  span.sid AS sessionid,
  err.sid IS NOT NULL AS has_error,
  err.first_errorcode,
  err.error_events,
  date_diff('second', from_iso8601_timestamp(span.first_event), from_iso8601_timestamp(err.first_error)) AS secs_to_first_error,
  err.est_bw_mbps_min,
  err.est_bw_mbps_max,
  err.stream_bw_mbps,
  err.nav_effectivetype,
  err.nav_downlink_mbps,
  err.nav_rtt_ms,
  buf.buffer_samples,
  buf.buf_cur_min,
  round(buf.buf_cur_avg, 2) AS buf_cur_avg,
  buf.buf_cur_last,
  st.state_events,
  coalesce(st.buffering_events, 0) AS buffering_events,
  tc.track_changes,
  tc.abr_bitrate_mbps_min,
  tc.abr_bitrate_mbps_max,
  round(tc.abr_bitrate_mbps_avg, 3) AS abr_bitrate_mbps_avg
FROM span
LEFT JOIN err ON span.sid = err.sid
LEFT JOIN buf ON span.sid = buf.sid
LEFT JOIN st  ON span.sid = st.sid
LEFT JOIN tc  ON span.sid = tc.sid
WHERE span.sid IS NOT NULL
ORDER BY span.first_event;
