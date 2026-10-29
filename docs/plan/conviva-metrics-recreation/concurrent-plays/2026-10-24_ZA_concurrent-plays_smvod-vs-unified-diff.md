# Concurrent Plays, SM-vod vs unified session — ZA, 2026-10-24

![overlay](../../../../output/ZA/charts/2026-10-24_concurrent-plays_smvod-vs-unified_15min.png)

## Summary

- Peak: SM-vod **16** at 07:53 UTC vs unified **18** at 07:53 UTC (difference -2).
- Mean absolute per-minute difference 1.15; the unified series is higher overall (sum of per-minute difference -1,528).
- Sessions: 1,511 played in SM-vod, 1,495 in unified (complete start and end); 1,493 in both, 18 only SM-vod, 2 only unified. 2,302 unified rows dropped (no sessionId, event_start or event_end, or end
  before start).
- SM-vod counts time from PLAYING to the next closing event; unified counts event_start to event_end, so it includes startup/buffering/paused time and drops sessions without an end.

## Largest per-minute gaps (SM-vod minus unified)

| UTC minute | SM-vod | Unified | Difference |
|---|---|---|---|
| 07:30 | 11 | 16 | -5 |
| 07:59 | 11 | 16 | -5 |
| 16:58 | 3 | 8 | -5 |
| 17:13 | 7 | 12 | -5 |
| 17:14 | 6 | 12 | -6 |
| 17:15 | 5 | 12 | -7 |
| 17:16 | 4 | 9 | -5 |
| 17:17 | 3 | 11 | -8 |
| 17:18 | 2 | 10 | -8 |
| 17:19 | 4 | 10 | -6 |
