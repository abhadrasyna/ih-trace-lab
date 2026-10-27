# VSF-T error summary, option A (parallel detail tables) — ZA, 2026-10-24

Preview for choosing the layout. VSF-T sessions only (2,101; 2,085 have a flat error row), grouped by each session's first error, from the flattened raw `PLAYER_ERROR` eventdata. `is_wv` is shown for
6001 only.

## 6001 (1,887 sessions)

| Phase | % | Network | % | WebView | % |
|---|---|---|---|---|---|
| LOADING | 100.0% | 4g | 99.6% | true | 94.3% |
| | | 3g | 0.4% | false | 5.7% |

Shaka error: `DRM.REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE` for 100.0% of sessions.

## 3016 (104 sessions)

| Phase | % | Network | % | Pipeline status | % |
|---|---|---|---|---|---|
| SEEKING | 96.2% | 4g | 64.4% | `PIPELINE_ERROR_DECODE` (merged) | 99.0% |
| BUFFERING | 1.9% | 3g | 33.7% | `Media failed to decode` | 1.0% |
| STALLED | 1.0% | (blank) | 1.0% | | |
| LOADED_METADATA | 1.0% | slow-2g | 1.0% | | |

The merged `PIPELINE_ERROR_DECODE` group is 76 + 17 + 10 sessions (three spellings, one with "video decoder reinitialization failed").

## 1003 (29 sessions)

| Phase | % | Network | % | Host | % |
|---|---|---|---|---|---|
| LOADING | 62.1% | 4g | 72.4% | SSAI (`vod-dai-ott-eu2.ssai.iris.synamedia.com`) | 58.6% |
| WAITING | 17.2% | 3g | 27.6% | MTN CDN (`sa-vod.cdn.yellotv.mtn.com`) | 41.4% |
| LOADED_METADATA | 6.9% | | | | |
| BUFFERING | 6.9% | | | | |
| SEEKING | 6.9% | | | | |

## E31012 (7 sessions)

| Phase | % | Network | % |
|---|---|---|---|
| SEEKING | 57.1% | 3g | 57.1% |
| LOADING | 28.6% | 4g | 42.9% |
| BUFFERING | 14.3% | | |
