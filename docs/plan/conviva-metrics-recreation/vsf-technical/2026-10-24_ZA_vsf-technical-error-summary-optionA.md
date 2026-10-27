# VSF-T error summary, option A (long form) — ZA, 2026-10-24

Preview for choosing the layout. VSF-T sessions only (2,101; 2,085 have a flat error row), grouped by each session's first error, from the flattened raw `PLAYER_ERROR` eventdata. `is_wv` is shown for
6001 only.

## 6001 (1,887 sessions)

| Field | Value | Sessions | % |
|---|---|---|---|
| shaka_error_name | `DRM.REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE` | 1,887 | 100.0% |
| is_wv | true | 1,780 | 94.3% |
| is_wv | false | 107 | 5.7% |
| player_phase | LOADING | 1,887 | 100.0% |
| net_effectivetype | 4g | 1,879 | 99.6% |
| net_effectivetype | 3g | 8 | 0.4% |

## 3016 (104 sessions)

| Field | Value | Sessions | % |
|---|---|---|---|
| pipeline_status | `PipelineStatus::PIPELINE_ERROR_DECODE` | 76 | 73.1% |
| pipeline_status | `PIPELINE_ERROR_DECODE` | 17 | 16.3% |
| pipeline_status | `PIPELINE_ERROR_DECODE: video decoder reinitialization failed` | 10 | 9.6% |
| pipeline_status | `Media failed to decode` | 1 | 1.0% |
| player_phase | SEEKING | 100 | 96.2% |
| player_phase | BUFFERING | 2 | 1.9% |
| player_phase | STALLED | 1 | 1.0% |
| player_phase | LOADED_METADATA | 1 | 1.0% |
| net_effectivetype | 4g | 67 | 64.4% |
| net_effectivetype | 3g | 35 | 33.7% |
| net_effectivetype | (blank) | 1 | 1.0% |
| net_effectivetype | slow-2g | 1 | 1.0% |

## 1003 (29 sessions)

| Field | Value | Sessions | % |
|---|---|---|---|
| shaka_url_host | `vod-dai-ott-eu2.ssai.iris.synamedia.com` | 17 | 58.6% |
| shaka_url_host | `sa-vod.cdn.yellotv.mtn.com` | 12 | 41.4% |
| player_phase | LOADING | 18 | 62.1% |
| player_phase | WAITING | 5 | 17.2% |
| player_phase | LOADED_METADATA | 2 | 6.9% |
| player_phase | BUFFERING | 2 | 6.9% |
| player_phase | SEEKING | 2 | 6.9% |
| net_effectivetype | 4g | 21 | 72.4% |
| net_effectivetype | 3g | 8 | 27.6% |

## E31012 (7 sessions)

| Field | Value | Sessions | % |
|---|---|---|---|
| player_phase | SEEKING | 4 | 57.1% |
| player_phase | LOADING | 2 | 28.6% |
| player_phase | BUFFERING | 1 | 14.3% |
| net_effectivetype | 3g | 4 | 57.1% |
| net_effectivetype | 4g | 3 | 42.9% |
