# CIR Related Exits — ZA, 2026-10-24

## Definition

Conviva: ended plays with connection-induced rebuffering (CIR) within 5 seconds of the session end, divided by ended plays
([doc](https://docs.conviva.ai/sei/video/metric-dictionary/cir-related-exits/)).

- Stall: `BUFFERING` after the first `PLAYING`; CIR unless it starts less than 10 s after a `PLAYER_SEEK`.
- Counts when a CIR stall overlaps the last 5 s of the play.
- Ended play: played, then `DESTROY`, `STOPPED` or `PLAYER_ERROR`; UTC buckets by session end.

## Headline

**19.40%** of ended plays were CIR related exits: 258 of 1,330. Of 3,961 sessions, 2,631 are not ended plays (never played, or no end event) and 0 ended on another UTC day.

![CIR Related Exits](../../../../output/ZA/charts/2026-10-24_cir-related-exits_5min.png)

## Top 10 content of CIR related exits

Percentages are of all 258 CIR related exits.

| # | Content | Exits | % of exits | Households |
|---|---|---|---|---|
| 1 | Zuluboy's 10% | 30 | 11.6% | 18 |
| 2 | My Sister Stole My Man | 13 | 5.0% | 6 |
| 3 | The Letter Delivered | 9 | 3.5% | 1 |
| 4 | Led Steppin | 8 | 3.1% | 6 |
| 5 | Lock and Load | 7 | 2.7% | 5 |
| 6 | Crossroads of Fate | 6 | 2.3% | 6 |
| 7 | Don't Let Them In | 6 | 2.3% | 4 |
| 8 | Masterminds | 6 | 2.3% | 5 |
| 9 | The Wrong Date | 6 | 2.3% | 4 |
| 10 | Becky | 5 | 1.9% | 4 |
| | Not resolved | 2 | 0.8% | |

## Device breakdown of CIR related exits

| Device class / OS / browser | Sessions | % |
|---|---|---|
| Mobile / Android / Chrome | 244 | 94.6% |
| Mobile / iOS / Safari | 10 | 3.9% |
| Desktop / Linux / Opera | 1 | 0.4% |
| Desktop / Windows / Chrome | 1 | 0.4% |
| Unresolved | 2 | 0.8% |

| DRM device type | Sessions | % |
|---|---|---|
| BROWSER | 252 | 97.7% |
| Unresolved | 6 | 2.3% |

## Playback type of CIR related exits

| Playback type | Sessions | % |
|---|---|---|
| VOD | 258 | 100.0% |
| Unresolved | 0 | 0.0% |
