# Concurrent Plays — ZA, 2026-10-24


## Definition

Conviva: per 60-second bucket, sessions with at least one video frame; the metric is the maximum over the interval ([doc](https://docs.conviva.ai/sei/video/metric-dictionary/concurrent-plays/)). Here
a session plays from `PLAYING` until the next `BUFFERING`, `PAUSED`, `STOPPED`, `DESTROY`, `PLAYER_SEEK`, `PLAYER_EOF` or `PLAYER_ERROR`; UTC minute buckets.

## Headline

**16** concurrent plays at 07:53 UTC (day maximum, equal to the maximum of the series points). Of 3,961 sessions, 1,511 played and 2,450 never played (excluded); 142 played sessions have no closing
event and end at their last event.

![Concurrent Plays](../../../../output/ZA/charts/2026-10-24_concurrent-plays_15min.png)

## Top 10 content by played sessions

Source: Athena session data. Percentages are of all 1,511 sessions that played during the day.

| # | Content | Played sessions | % of played | Households |
|---|---|---|---|---|
| 1 | My Sister Stole My Man | 279 | 18.5% | 29 |
| 2 | Zuluboy's 10% | 113 | 7.5% | 67 |
| 3 | The Day We Got Married | 44 | 2.9% | 10 |
| 4 | The Wrong Date | 36 | 2.4% | 22 |
| 5 | Cabin 28 | 33 | 2.2% | 29 |
| 6 | KOKO: The Box TV | 30 | 2.0% | 22 |
| 7 | Don't Let Them In | 28 | 1.9% | 20 |
| 8 | Lock and Load | 26 | 1.7% | 20 |
| 9 | Living Among Us | 25 | 1.7% | 21 |
| 10 | Masterminds | 25 | 1.7% | 17 |
| | Not resolved | 5 | 0.3% | |

## Device breakdown at the peak minute

| Device class / OS / browser | Sessions | % |
|---|---|---|
| Mobile / Android / Chrome | 15 | 93.8% |
| Mobile / Android / Opera | 1 | 6.2% |
| Unresolved | 0 | 0.0% |

| DRM device type | Sessions | % |
|---|---|---|
| BROWSER | 16 | 100.0% |
| Unresolved | 0 | 0.0% |

## Playback type at the peak minute

| Playback type | Sessions | % |
|---|---|---|
| VOD | 16 | 100.0% |
| Unresolved | 0 | 0.0% |
