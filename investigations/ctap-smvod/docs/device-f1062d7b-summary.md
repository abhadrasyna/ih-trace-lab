# Device f1062d7b…e057 — playback and error summary (ZA, 2026-10-18 to 2026-10-19)

Generated from `scripts/trace_device_household.py` over `output/ZA/<date>_setupsession_with_outcome.csv` and `output/ZA/error_eventdata_flat/<date>_all.csv`.

## Identity

| Field | Value |
|---|---|
| deviceId | `f1062d7bc72d63370850d70f6407d525d319774d5f7f030ef886480e6a4de057` |
| householdId | `rD_saW-tErOcF5lAOB8WUzjoIkg7f11kmFW_ZufEMMgj3kDqciW8` (single household in all rows) |
| User agent | `Mozilla/5.0 (Linux; Android 10; K) … Chrome/155.0.0.0 Mobile Safari/537.36` |
| Window | first error 2026-10-18T15:32:30Z, last error 2026-10-19T11:33:38Z |

## Session split (44 unique sessions)

VSF here means a `REQUEST_VIEWING` event was seen (`startup_time_ms` is derived from it) but the session never reached a `PLAYING` state.

| Class | With error code | No error code | Total |
|---|---|---|---|
| VSF | 33 | 8 (all `EBVS`) | 41 |
| Played (`PLAYING` seen) | 0 | 0 | 0 |
| No `REQUEST_VIEWING` / no startup time | 0 | 3 | 3 |
| Total | 33 | 11 | 44 |

- Sessions without `REQUEST_VIEWING` have no startup time; two of them have no outcome row at all (no `unified_sessions` match).
- Of the 33 error sessions, 28 carry 3016 and 5 carry 3015.
- Operations: 28 rows have span `POST`; 16 rows have a blank span name.
- Outcomes (row counts): 33 `INCOMPLETE_NO_DESTROY`, 8 `EBVS`, 3 blank. No successful playback was recorded.
- Caveat: `REQUEST_VIEWING` is not in the local CSVs, so its presence is inferred from `startup_time_ms` being set.

## Failures

| Code | Events | Shaka error | Detail |
|---|---|---|---|
| 3016 | 28 | `MEDIA.VIDEO_ERROR` (category 3) | `PIPELINE_ERROR_DECODE`; "This content cannot be played on your current device." |
| 3015 | 5 | `MEDIA.MEDIA_SOURCE_OPERATION_THREW` | each tied to an audio segment (`Audio1-*.m4f`) on `sa-vod.cdn.yellotv.mtn.com` |

## Errors by content

| Content | Errors | Codes |
|---|---|---|
| Cabin 28 | 6 | 3016 ×6 |
| Sudwala | 6 | 3016 ×6 |
| Pelgrimsrus | 3 | 3016 ×3 |
| Pumbaa | 3 | 3016 ×2, 3015 ×1 |
| Twisted Fates | 3 | 3016 ×2, 3015 ×1 |
| 12 other titles | 1 each | 3016 ×9, 3015 ×3 (Old MacDonald, Apples And Bananas, Johny Johny Yes Papa) |

## Findings

- No single title fails: 3016 spans about 17 titles across horror and kids' content, so the cause points at the device or its decoder, not the content.
- Only Pumbaa and Twisted Fates hit both 3016 and 3015; the overlap is too small to read as a content pattern.
- Not WebView: `is_wv` is `false` on all 33 error events, the user agent has no `; wv)` token, and the device has no rows in the `webview_device_report` CSVs. The "K" model and Android 10 are frozen
  Chrome UA values, so the real device may differ.

## CDN correlation (MTN_INC0256613, matched by content UUID)

Source: `data/cdnReport/MTN_INC0256613_Client_query.txt` (18 blocks, IPs 41.13.78.209 and 102.66.159.55) against `output/ZA/2026-10-01_2026-10-19_error_report_3xxx_rD_saW-t.csv` (33 error sessions, 19
content UUIDs, 15 with blank `start_time`). Sessions were matched on the `vode/<uuid>/` path segment, not on time, so blank-`start_time` sessions are covered. Content names come from `content_uuid` /
`content` in `output/ZA/2026-10-*_setupsession_with_outcome.csv`. Overlapping blocks repeat rows, so the 1,013 raw rows were deduplicated on timestamp, URL, bytes, cache result and `ttms` to 278 rows;
all counts below use the deduplicated rows. All 33 sessions have CDN rows.

- **No CDN failure:** no 4xx/5xx status and no row with `ttms` above 2000 ms.
- **Most content is served from cache** (`ttfb` median 0), so the 3015/3016 errors do not look CDN-originated: 15 of the 19 content UUIDs show no origin-bound pattern (`ttfb` 0, no aborts) and still
  failed the same way.
- **Origin-bound titles** (`ttfb` 261-404 ms) have refresh-misses and, for some, mid-transfer client aborts (`bytes > 0`), consistent with the device-side failure above rather than a CDN fault.

| Content | Sessions | Codes | CDN pattern (deduplicated) |
|---|---|---|---|
| Cabin 28 (`1a1b510a`) | 6 | 3016 ×6 | all cache hits, `ttfb` 0 |
| Sudwala (`0eef7654`) | 6 | 3016 ×6 | cache hits, 2 refresh-misses, `ttfb` 0 |
| Pumbaa (`133b65f5`) | 3 | 3016 ×2, 3015 ×1 | origin-bound, `ttfb` 262 ms, 3 mid-transfer aborts |
| Pelgrimsrus (`869e5633`) | 3 | 3016 ×3 | origin-bound, `ttfb` 262 ms, 2 mid-transfer aborts |
| Twisted Fates (3 UUIDs) | 3 | 3016 ×2, 3015 ×1 | cache hits, `ttfb` 0 |
| Elephant Whispers (`14f13bc4`) | 1 | 3016 | origin-bound, `ttfb` 404 ms, no aborts |
| The Bear Went Over the Mountain (`2df37724`) | 1 | 3016 | origin-bound, `ttfb` 328 ms, 11 refresh-misses, 1 abort |
| 10 other titles | 1 each | 3016 ×7, 3015 ×3 | cache hits, `ttfb` 0 |

- Two CDN UUIDs have no session in this report: "Deck the Halls - Fantasy Animals" and "The Hiccup Song". Matching ignores time, so a row may belong to a neighbouring session of the same content.
- UUID `17d99e7b…` maps to two titles in the session files ("A Promise of Escape" ×85, "The Wedding That Never Was" ×1); it is not in this device's data.

## Caveats

- Operations/outcomes count rows; "attempts by content" counts unique sessions.
- For 3015 rows the `pipeline_status` column holds a URL instead of a pipeline status (column shift in the flattened file).
- The 16 blank-span rows and 3 blank outcomes are unexplained.
