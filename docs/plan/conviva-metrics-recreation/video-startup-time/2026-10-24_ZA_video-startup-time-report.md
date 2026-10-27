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

## Top 10 households by mean VST

Households with at least 3 plays (445 households overall, 2 plays without a household).

| # | Household | Plays | Mean (s) | Median (s) | P90 (s) | Max (s) | % over 10 s | Top device |
|---|---|---|---|---|---|---|---|---|
| 1 | 6utTNU6qJ9tsH6B7R--X7HFB_ry33HYcDLlnpcR-U1bDDPmyUiOP | 5 | 77.72 | 8.71 | 350.77 | 350.77 | 40% | Mobile / iOS / Safari |
| 2 | h5p99w6PPEgfpwV7tc9GpotOkVOGt9sVRMEpc26GuoubddJxFw2W | 3 | 18.36 | 21.48 | 27.81 | 27.81 | 67% | Mobile / Android / Chrome |
| 3 | 4KwLjKMUYKN3qfEy-9rXBDQ7deocF-xd-TriNHBiSFxTTagIv53F | 6 | 17.95 | 19.43 | 25.55 | 25.55 | 83% | Mobile / Android / Chrome |
| 4 | I-LEiL3n3_dTCI_cUTztOZ4VoMlSy_lkOFEP7Pfhu4GPBWwPpGFz | 3 | 17.65 | 12.45 | 32.25 | 32.25 | 67% | Mobile / Android / Chrome |
| 5 | KONsYK8lPUASRuM_zKagKwJEvi_hqcjJwkxb-3exL-fPDMPnuaaX | 7 | 17.22 | 15.92 | 29.46 | 29.46 | 71% | Mobile / iOS / Safari |
| 6 | _En1_ypX-c0zmy2Q7qiKexQtGpOJt18mf2mVDDGp6mdPq1Z9MNBd | 4 | 17.06 | 15.80 | 31.93 | 31.93 | 75% | Mobile / Android / Chrome |
| 7 | Vg_dvnz4T-pseoMtEbDZsS5Zj8c9hPRNdpGpDfhC5K3J4XM6YH_g | 32 | 16.14 | 10.85 | 33.11 | 47.02 | 56% | Mobile / Android / Chrome |
| 8 | L1vZC7ZrQgRNjOF07qPVptW6uhNEXZeGG0qofaFeW933vnuPqe7q | 3 | 15.22 | 9.94 | 27.70 | 27.70 | 33% | Mobile / Android / Chrome |
| 9 | EZvjcAMZ6hJdwyS_nHHIGBPAytOsz5-sDJpDXGj-694Mfk3xG5tF | 3 | 15.15 | 16.27 | 19.07 | 19.07 | 100% | Mobile / iOS / Safari |
| 10 | yK3cA9Wt3P5HKXmcO3bthy66C44HCFBwxSHPquClcvffTHeDwyl2 | 4 | 15.10 | 7.32 | 42.21 | 42.21 | 25% | Mobile / Android / Chrome |

## Top 10 households by worst single play

Any number of plays; the single slowest play of each household.

| # | Household | Plays | Mean (s) | Median (s) | P90 (s) | Max (s) | % over 10 s | Top device |
|---|---|---|---|---|---|---|---|---|
| 1 | Srwj6pCnaG6G8xbe8vaYTRHSGgzyBwdT1Uq24te4GGGxXopvhyTB | 1 | 600.00 | 600.00 | 600.00 | 600.00 | 100% | Mobile / Android / Chrome |
| 2 | 6utTNU6qJ9tsH6B7R--X7HFB_ry33HYcDLlnpcR-U1bDDPmyUiOP | 5 | 77.72 | 8.71 | 350.77 | 350.77 | 40% | Mobile / iOS / Safari |
| 3 | DUyZ3yl9ePBrjtJiEmNLGArQbd6mX2uMga2RTvPykO_AozBaNP3d | 2 | 101.84 | 101.84 | 195.19 | 195.19 | 50% | Mobile / Android / Chrome |
| 4 | s7R2iSXvNxXoLQB3gPL7KuVvj6inrViOzOOX1hQ4EFIXV9wJPWud | 1 | 87.33 | 87.33 | 87.33 | 87.33 | 100% | Mobile / Android / Chrome |
| 5 | 3qjGGgN7bvx13HFgKWSJDsZoUBpEGT5X9SFhv57sI6vRSWSYGP_H | 1 | 65.40 | 65.40 | 65.40 | 65.40 | 100% | Mobile / iOS / Safari |
| 6 | Vg_dvnz4T-pseoMtEbDZsS5Zj8c9hPRNdpGpDfhC5K3J4XM6YH_g | 32 | 16.14 | 10.85 | 33.11 | 47.02 | 56% | Mobile / Android / Chrome |
| 7 | Fq0wFVCV00U7PajYXA8HTeszVzz13k9dLfAvG1U50k-xQpmcTRN5 | 2 | 33.63 | 33.63 | 42.43 | 42.43 | 100% | Mobile / Android / Chrome |
| 8 | yK3cA9Wt3P5HKXmcO3bthy66C44HCFBwxSHPquClcvffTHeDwyl2 | 4 | 15.10 | 7.32 | 42.21 | 42.21 | 25% | Mobile / Android / Chrome |
| 9 | hu06fmJa_AsZ6vfTAZaYAJo8r05yssPbTo8MxhYZbtHNDJL8eNtU | 9 | 14.99 | 7.64 | 41.60 | 41.60 | 33% | Mobile / Android / Chrome |
| 10 | I-LEiL3n3_dTCI_cUTztOZ4VoMlSy_lkOFEP7Pfhu4GPBWwPpGFz | 3 | 17.65 | 12.45 | 32.25 | 32.25 | 67% | Mobile / Android / Chrome |

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
