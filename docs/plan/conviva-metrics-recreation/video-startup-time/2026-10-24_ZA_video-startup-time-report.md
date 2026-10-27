# Video Startup Time — ZA, 2026-10-24

## Definition

Conviva: time from the play attempt to the first frame displayed, averaged over the plays starting in the interval; capped at 600 s per play
([doc](https://docs.conviva.ai/sei/video/metric-dictionary/video-startup-time/)).

- Attempt = `CREATE`; first frame = first `PLAYING`. Plays are bucketed by attempt time, UTC.
- No pre-roll ads or heartbeat gaps are modelled.

## Headline

**8.33 s** average VST over 1,510 plays (median 6.33 s, 90th percentile 14.11 s). Capped at the limit: 1. Of 3,961 sessions, 2,450 never played, 0 had their attempt on another UTC day and 1 had no
usable attempt time.

![Video Startup Time](../../../../output/ZA/charts/2026-10-24_video-startup-time_5min.png)

## Distribution

| VST | Plays | % of plays |
|---|---|---|
| 0-1 s | 16 | 1.1% |
| 1-2 s | 35 | 2.3% |
| 2-3 s | 178 | 11.8% |
| 3-5 s | 337 | 22.3% |
| 5-10 s | 611 | 40.5% |
| 10-30 s | 314 | 20.8% |
| 30-60 s | 14 | 0.9% |
| 60-600 s | 4 | 0.3% |
| >= 600 s | 1 | 0.1% |

## Top 10 content by plays

| Content | Plays | Avg VST (s) |
|---|---|---|
| My Sister Stole My Man | 279 | 4.07 |
| Zuluboy's 10% | 112 | 8.74 |
| The Day We Got Married | 44 | 4.21 |
| The Wrong Date | 36 | 6.55 |
| Cabin 28 | 33 | 9.72 |
| KOKO: The Box TV | 30 | 8.45 |
| Don't Let Them In | 28 | 7.53 |
| Lock and Load | 26 | 9.45 |
| Living Among Us | 25 | 7.63 |
| Masterminds | 25 | 7.71 |
| Unresolved | 5 | 17.58 |

## Device breakdown

| Device class / OS / browser | Plays | Avg VST (s) |
|---|---|---|
| Mobile / Android / Chrome | 1,319 | 8.19 |
| Mobile / iOS / Safari | 123 | 10.67 |
| Desktop / macOS / Chrome | 24 | 1.71 |
| Mobile / iOS / Chrome (iOS) | 13 | 14.15 |
| Mobile / Android / Opera | 7 | 10.24 |
| Desktop / Windows / Chrome | 5 | 9.19 |
| Desktop / Windows / Microsoft Edge | 4 | 3.11 |
| Tablet / Android / Chrome | 3 | 8.74 |
| Desktop / Linux / Opera | 2 | 5.69 |
| Tablet / Android / Firefox | 1 | 14.02 |
| Unresolved | 9 | 6.03 |

| DRM device type | Plays | Avg VST (s) |
|---|---|---|
| BROWSER | 1,479 | 8.36 |
| Unresolved | 31 | 7.13 |

## Playback type

| Playback type | Plays | Avg VST (s) |
|---|---|---|
| VOD | 1,510 | 8.33 |
| Unresolved | 0 | |
