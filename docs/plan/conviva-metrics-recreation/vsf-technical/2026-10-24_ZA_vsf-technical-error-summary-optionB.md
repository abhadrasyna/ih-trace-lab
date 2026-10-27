# VSF-T error summary, option B (one table) — ZA, 2026-10-24

Preview for choosing the layout. VSF-T sessions only (2,101; 2,085 have a flat error row), grouped by each session's first error, from the flattened raw `PLAYER_ERROR` eventdata. WebView is shown for
6001 only. The three 3016 `pipeline_status` spellings are merged into one `PIPELINE_ERROR_DECODE` group. Percentiles use the sessions that carry the stat, so n is smaller for 1003 and E31012.

| Code | Sessions | Meaning | Main cause | Phase | Network | Bandwidth Mbps | Buffering s | Extra |
|---|---|---|---|---|---|---|---|---|
| 6001 | 1,887 | Unable to create a streaming session | `DRM.REQUESTED_KEY_SYSTEM_CONFIG_UNAVAILABLE` 100% | LOADING 100% | 4g 99.6%, 3g 0.4% | n/a | n/a | WebView 94.3%, not 5.7% |
| 3016 | 104 | Not playable on this device | `PIPELINE_ERROR_DECODE` 99%, other 1% | SEEKING 96.2% | 4g 64.4%, 3g 33.7% | p50 0.5 / p90 3.8 (n=103) | p50 1.3 / p90 3.3 | |
| 1003 | 29 | Not playable on this network | `NETWORK.TIMEOUT` 100% | LOADING 62.1% | 4g 72.4%, 3g 27.6% | p50 0.6 / p90 5.2 (n=11) | p50 27.5 / p90 32.6 | Host: SSAI 58.6%, MTN CDN 41.4% |
| E31012 | 7 | Video is taking longer than usual to start | App timeout, no Shaka error | SEEKING 57.1%, LOADING 28.6% | 3g 57.1%, 4g 42.9% | p50 0.5 / p90 2.2 (n=5) | p50 0.9 / p90 45.6 (n=5) | |
