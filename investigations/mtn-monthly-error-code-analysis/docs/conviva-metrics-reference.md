# Conviva QoE metrics reference

Source: the Conviva SEI Video Metric Dictionary (`https://docs.conviva.ai/sei/video/metrics/` and `.../metric-dictionary/<metric>/`), fetched 2026-10-11. Page "Updated" dates are 2026-09-02 or
2026-09-23. Scope agreed with the user: quality-of-experience metrics (starts, failures, startup, rebuffering, bitrate, plays, engagement, SPI). Ad metrics, dimensions and dashboards are out of scope.
Definitions paraphrase the Conviva pages; text in quotes is verbatim. Each metric ends with a **Computable** line: whether we can compute it from `unified_<id>.unified_sessions`, our only source for
the funnel. That line is an assessment unless marked "verified", which means it was measured on ZA September 2026 (Athena, 2026-10-11).

## 1. How to read Conviva metrics

### 1.1 Metric types (decides which interval a session is counted in)

| Type | Counted in the interval where | Examples |
| --- | --- | --- |
| Started | the play started | Attempts, Plays, VST, Unique Devices with Attempts |
| Ended | the play ended | Ended Plays, VPF, Bitrate Switches, Paused Ratio |
| Interval | the activity happened | Concurrent Plays, Rebuffering Ratio, EBVS, VRT |
| Lifetime | the whole session, for distributions | Play Duration vs Rebuffering Ratio |

Consequence for us: a daily Conviva VPF counts plays that **ended** that day, a daily VST counts plays that **started** that day. Our per-day Athena columns key on the day of `timestamp_formatted`,
which can differ for sessions that cross midnight.

### 1.2 Session rules that change every count

- A session expires after more than 120 seconds without a heartbeat; Conviva then treats it as ended.
- A session that resumes after expiry is a **revived session**: same session id, separate session, separate metrics.
- Revived sessions never contribute to VST.
- Revived sessions that fail to play contribute to nothing (not VSF, not EBVS).
- Revived sessions that play successfully contribute to Attempts, Plays and Ended Plays.
- Playing states under 200 ms of continuous playing are false playing states and are not counted as plays.
- Continuous rebuffering over 90 seconds is removed from rebuffering metrics; Conviva treats that session as expired.
- Continuous pause over 90 seconds is excluded from Paused Time.
- Conviva lists all errors the player reports within 90 seconds of a failure, in the order reported (VSF and VPF).
- Real-time points aggregate the previous 60 seconds and refresh every 20 seconds.
- Historical intervals are 2-hour (any 30-day window within 13 months), 1-day and 1-month (periods over 30 days within 13 months).

## 2. The funnel (starts and failures)

Conviva states that unsuccessful play attempts count as VSF or EBVS, so **Attempts = Plays + VSF + EBVS** (before revived-session exclusions). Verified on ZA September 2026: the identity closes on 29
of 30 days; 09-18 is off by one session.

### Attempts

- Definition: the number of times viewers attempted to start playback. Whether auto-play counts depends on the player integration.
- Type: Started. Denominator: none.
- Computable: yes. Distinct `REQUEST_VIEWING` sessions (verified, 5,029).

### Plays

- Definition: counted when the viewer sees the first frame of video. Unsuccessful attempts are not plays.
- Type: Started. Shown as "Plays % of Attempts".
- Adjustment: under 200 ms of continuous playing is not a play.
- Computable: close. `REQUEST_VIEWING` with end reason `PLAYING` (verified, 3,967 = 78.9%). The 200 ms rule cannot be applied.

### Video Start Failures (VSF)

- Definition: sessions that failed to start because of a connection or streaming error reported by the player.
- A session that errored but then kept receiving heartbeats and played does not count.
- If the video terminates before starting without an error, it is EBVS, not VSF.
- Type: counted when the failure occurs. Shown as a percentage of Attempts.
- One VSF can carry several error codes, so per-code counts must not be summed into sessions.
- Audio streams call it Stream Start Failure (SSF).
- Alerts: manual yes, AI yes (fires once per video view).
- Computable: yes. `REQUEST_VIEWING` with end reason `PLAYER_ERROR` (verified, 765 = 15.2%).

### Exits Before Video Start (EBVS)

- Definition: attempts that ended before video start without a reported fatal error.
- If a fatal error is reported at exit, it is VSF instead.
- With client-side ad insertion (CSAI) exits during pre-roll count; with server-side ad insertion (SSAI) they do not.
- Type: Interval. Shown as a percentage of Attempts. Audio streams call it Exit Before Stream Starts (EBSS).
- Alerts: manual yes, AI yes.
- Computable: close. `REQUEST_VIEWING` with end reason `DESTROY` (verified, 296 = 5.9%).
- Our earlier "broad" EBVS rule (no `PLAY` row and a `DESTROY` on any row) is not Conviva's definition.

### Failed Attempts

- Ad metric only: Ad Start Failures + Exits Before Ad Start. Not a content metric; out of scope.

### 2.1 Business vs technical split

- **VSF-B** (Video Start Failures Business): VSF whose error matches a configured business error, for example user or concurrency limits. Configured under Settings, Business Error Configuration.
  Alerts: manual yes, AI no.
- **VSF-T** (Video Start Failures Technical): VSF that does not match a configured business error. Alerts: manual yes, AI yes.
- Rule: VSF = VSF-B + VSF-T; a business-matching error is never counted in the technical metric.
- With traffic rules, Conviva applies the business-error configuration of the account the player sent traffic to, not the account that received it.
- Computable: not yet. It needs the user's business-error list (task MEC-19).

## 3. Playback failure (after the first frame)

### Ended Plays

- Definition: a play that ended in the interval and showed at least one frame.
- A session ends gracefully (with or without completion), through failure (VPF), or by timeout since the last heartbeat.
- Type: Ended. It is the denominator of VPF.
- Computable: approximately. `PLAY` end reasons `DESTROY` + `PLAYER_ERROR` + `TIMEOUT` (verified: 3,649 end-reason rows for 3,648 distinct sessions; one session on 09-18 has two).

### Video Playback Failures (VPF)

- Definition: a play that terminated because of a fatal playback error such as corruption, insufficient streaming resources or a sudden interruption.
- Shown as a sum or as a percentage: Ended Plays with VPF divided by Ended Plays in the period.
- Alerts: manual yes, AI no. Audio streams call it Stream Playback Failure (SPF).
- Counting conditions, all required:
  1. A fatal error arrives from the Conviva device library **after playback started** (after the first i-frame is rendered).
  2. The session ends, and the playing time from the error to the session end is **not more than the last reported buffer length**.
  3. If the device reports no buffer length, 150 seconds (2.5 minutes) is used.
- Distribution (Custom dashboard only): plays that ended with VPF per play-duration bucket.
- Computable: proxy only. `PLAY` with end reason `PLAYER_ERROR` over ended plays. It cannot check the i-frame or the error-to-end gap, so call it "VPF-proxy". Verified: 161 of 3,649 = 4.4%. Dividing
  by attempts would give 3.2%, which is the wrong denominator. `PLAY`/`TIMEOUT` (102) are ended plays and part of the denominator; they are not failures in Conviva terms.

### VPF-B and VPF-T

- **VPF-B**: a VPF whose error matches a configured business error. Needs the same three conditions plus the business match. Percentage of Ended Plays.
- **VPF-T**: a VPF that does not match a business error. VPFs matching a business error are counted in VPF-B only.
- Computable: not yet (MEC-19).

## 4. Startup time

### Video Startup Time (VST)

- Definition: time from the play attempt to the first frame displayed (playStart minus attempt timestamp).
- Pre-roll ad time is not counted; content pre-fetched in the background during an ad is not counted.
- Type: Started. Summary is the average over plays that started in the interval; also a distribution by preset bucket.
- Adjustments: capped at 600 seconds per play; plays with a heartbeat gap or loss during startup are excluded; the UI shows -3 when unavailable.
- Alerts: manual yes, AI yes.
- Computable: approximately. `REQUEST_VIEWING` duration for plays (verified: mean 6.4 s, median 5.1 s, 90th percentile 11.6 s). Whether that duration equals attempt-to-first-frame is unverified.

### High Startup Time (HST)

- Definition: percent of plays whose startup took too long against the SPI threshold (10 seconds for SPI Good, 8 seconds for SPI Best).
- Thresholds are customer settings.
- Computable: approximately. Plays above 10 seconds (verified: 13.6% of plays).

### Video Restart Time (VRT)

- Definition: wait after user-initiated seeks. In the page's example VRT = (R1 + R3) / 2, and an incomplete seek (R2) is not included.
- Type: Interval. Summary is the average over plays re-starting in the interval.
- Adjustments: capped at 600 seconds; seeks before join are ignored; mid-roll not-monitored time and unknown states are removed.
- Alerts: manual yes (may fire several times per view), AI no.
- Computable: no. It needs seek events.

### Wait Time Before Exit

- Definition: how long viewers waited before exiting during EBVS. Distribution over 4 predefined buckets, for example 0-20 s and 20-40 s.
- CSAI pre-roll counts as wait; SSAI pre-roll does not.
- Computable: approximately. `REQUEST_VIEWING` duration for `DESTROY` (verified: mean 27.2 s).

### Abandonment

- Definition: EBVS where the wait exceeded the SPI threshold (10 seconds Good, 8 seconds Best).
- Computable: approximately. EBVS over 10 seconds (verified: 39.5% of EBVS).

## 5. Rebuffering

Time components:

- `playTime` is time the reported player state is "playing" (P1, P2, ...).
- `rebufferingTime` is time in "buffering" after the first frame, excluding pause. It is seek rebuffering (R1) plus non-seek rebuffering (R2).
- Buffering before the first frame is startup, not rebuffering.

### Rebuffering Ratio (RR)

- Definition: `rebufferingTime / (playTime + rebufferingTime)`, including seek and non-seek rebuffering. Summary is total rebuffering divided by total viewing time.
- Alerts: manual yes (may fire several times per view), AI yes.
- Computable: approximately at best. `BUFFERING/PLAYING` rows give buffering time (task MEC-21, optional); player-state precision is unverified.

### Connection Induced Rebuffering Ratio (CIRR) and Time (CIRT)

- CIRR uses only non-seek rebuffering (R2) in the same ratio. CIRT is the total R2 time in the interval and feeds SPI High Rebuffering.
- Rebuffering that starts 10 seconds or more after a seek ends counts as connection induced; otherwise it is seek-induced (R1).
- A session in continuous non-seek rebuffering for 90 seconds is treated as expired; its CIRT is reported as zero and it counts as an interrupted play.
- Micro rebuffering (under 200 ms) is not excluded.
- Computable: no. It needs seek events to separate R1 from R2.

### Related ended-play rebuffering metrics

- **Zero CIRR Ended Plays %**: percent of ended plays with zero connection-induced rebuffering.
- **Connection Induced Interrupted Plays**: ended plays with at least one connection-induced interruption, shown as a percentage of ended plays.
- **CIR Related Exits**: ended plays that ended within 5 seconds of connection-induced rebuffering, divided by ended plays. The impact period counts back from session end until 30 seconds of non-CIR
  time or the play start.
- **High Rebuffering**: percent of ended plays with high CIRR or CIRT against the SPI threshold.
- Computable: no.

## 6. Bitrate and picture quality

None of these are computable from `unified_sessions`; player-side bitrate and frame-rate fields are not in our tables. All have distributions against ended plays and play duration.

- **Avg. Peak Bitrate**: time-weighted peak bitrate (manifest `BANDWIDTH`), total bits played over total playing time. Excludes buffering and pause. Formerly "Average Bitrate" (still that name in SSD
  and APIs). Interval type. Low Bitrate is the percent of ended plays under per-screen-size thresholds (TV, desktop/tablet, mobile); it can be an AI alert (beta).
- **Avg. Average Bitrate**: same method using the manifest average bandwidth attribute. Reported as 0 when the manifest or player does not send it.
- **Starting Bitrate**: bitrate at the join point, summed over ended plays and divided by ended plays. Ended type. Many DASH devices do not report it and it shows as 0. It is based on average bitrate
  today; a move to peak bitrate is on Conviva's backlog.
- **Ending Peak Bitrate** (beta): time-weighted peak bitrate in the final one-minute interval before the session ended. It exposes quality drops hidden by the session average: a 26 Mbps average with
  200 kbps in the last minute before a VPF. Filtered by a VPF error it shows which rungs of the bitrate ladder precede failures.
- **Bitrate Switches**: number of bitrate changes per session; aggregate is switches over ended plays divided by ended plays. Ended type.
- **Average Frame Rate**: total decoded frames over play time; valid when frame rate is above 0 fps while playing. Interval type. It needs minimum SDK versions (for example Android SDK 2.125 or iOS
  2.116 and later).

## 7. Engagement and volume

- **Concurrent Plays**: maximum simultaneously active sessions across 60-second buckets in the interval (10-second buckets in real time). It counts sessions that started playing and are not
  rebuffering, paused or in trick modes, and excludes failed attempts. Minute, hourly and daily values can differ by 1-2%. Computable: approximately, from overlapping `PLAY` intervals; not checked.
- **Playing Time (Ended)**: total play minutes of plays that **ended** in the interval; includes SSAI ad playing time; not supported for CDN dimensions. Computable: approximately, as the sum of `PLAY`
  durations.
- **Playing Time (Interval)**: playing time inside the selected interval only; excludes pause, CSAI ads and rebuffering. Computable: approximately; needs interval clipping.
- **Viewer Hours**: total hours of actual playing time in the interval, excluding rebuffering. Computable: approximately, as Playing Time.
- **Minutes / Ended Play**: playing minutes divided by ended plays. Computable: approximately.
- **Average % Complete**: total play time over `contentLength`; VOD only; sessions with EBVS or VSF are excluded; -1.0% when content length is missing. Computable: unverified; needs content length.
- **Paused Time**: sum of session pause time over ended sessions; includes pauses before join and during SSAI ads; pauses over 90 seconds excluded. Computable: no.
- **Paused Ratio**: pause time over (pause + playing + rebuffering) time for ended sessions. Computable: no.
- **Last Playhead Time**: playhead position at session end; shown as -3 when unavailable. Computable: no.

## 8. Devices and viewers

- **Unique Devices with Attempts**: distinct Conviva client ids with an attempt in the interval (Started type). A device is not a person. An approximation algorithm is used, so values can differ
  slightly between summary and dimension tables. Computable: approximately, from distinct household or device ids where present; not verified for ZA.
- **Unique Devices with Ended Plays**: distinct devices with at least one ended play (Ended type); hourly, daily and monthly only. The total across a dimension is smaller than the sum of its parts
  because a device is counted once.
- **Ended Plays per Unique Device** and **Minutes per Unique Device**: ended plays or minutes divided by unique devices with ended plays.
- **Unique Viewers with Attempts** (beta): distinct viewers with an attempt, including VSF and EBVS; up to 24-hour intervals within 30 days.
- **Unique Viewers with Ended Plays** (beta): distinct viewers with an ended play; excludes viewers who only had VSF or EBVS. Both viewer metrics can undercount because the viewer id may be missing
  for consent reasons. Computable: no.

## 9. Streaming Performance Index (SPI)

SPI is Conviva's single score: the percentage of streams with a good or best viewing experience. A stream is good only if it has all of the following:

- no VSF-T or VPF-T errors;
- no or very low rebuffering (using CIRR);
- acceptable picture quality (average bitrate for the screen size);
- acceptable startup time;
- no EBVS where the viewer waited a long time before exiting.

Related metrics:

- **SPI Streams**: all monitored sessions that contributed to the SPI. Excluded are exits before video start where the viewer did not wait a significant time, and sessions hit by business-logic
  errors.
- **Impacted Streams**: streams that failed one or more KPI settings (Good, Best or custom). Improvement-opportunity percentages can add up to more than the impacted percentage because one stream can
  be hit by several, for example high rebuffering leading to VPF-T.
- **Impacted vs non-impacted streaming time**: average playing minutes of each group, shown only when good sessions exceed bad sessions by 10%; otherwise "Engagement difference low".

We can compute SPI inputs only in part: VSF, VPF-proxy, startup and abandonment yes; rebuffering, bitrate and the business/technical split no. Do not publish an "SPI" number built from partial inputs.

## 10. What this means for our pipeline

- **Attempts**: matches Conviva Attempts; revived sessions are not identifiable in our data.
- **Success / Plays-Sessions**: matches Plays except that the 200 ms rule cannot be applied.
- **VSF**: matches all-VSF (business plus technical) until MEC-19 supplies the business-error list.
- **EBVS**: Conviva's rule is end reason `DESTROY` at the request stage; our "broad" rule differs.
- **Errors per 100 attempts (VPF)**: Conviva's VPF denominator is **ended plays**, not attempts, and it has the i-frame and buffer-length conditions.
- **Shaka error sessions**: a player-side count with no Conviva equivalent; compare with unified `PLAYER_ERROR` as the trust chart.
- **Startup chart**: VST and High Startup Time are approximations until the meaning of `REQUEST_VIEWING` duration is confirmed.

Cross-references: MEC-8 (funnel), MEC-16 (comparison table), MEC-17 (VST, abandonment), MEC-19 (business vs technical), MEC-21 (rebuffering approximation).
