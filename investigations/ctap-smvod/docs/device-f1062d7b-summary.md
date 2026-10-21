# Device f1062d7b…e057 — playback and error summary (ZA, 2026-10-18 to 2026-10-19)

Generated from `scripts/trace_device_household.py` over `output/ZA/<date>_setupsession_with_outcome.csv` and `output/ZA/error_eventdata_flat/<date>_all.csv`.

## Identity

| Field | Value |
|---|---|
| deviceId | `f1062d7bc72d63370850d70f6407d525d319774d5f7f030ef886480e6a4de057` |
| householdId | `rD_saW-tErOcF5lAOB8WUzjoIkg7f11kmFW_ZufEMMgj3kDqciW8` (single household in all rows) |
| User agent | `Mozilla/5.0 (Linux; Android 10; K) … Chrome/155.0.0.0 Mobile Safari/537.36` |
| Window | first error 2026-10-18T15:32:30Z, last error 2026-10-19T11:33:38Z |

## Volumes

- Unique playback sessions: 44 (28 rows have span `POST`; 16 rows have a blank span name).
- Sessions with at least one error event: 33 (33 error events in total).
- Outcomes (row counts): 33 `INCOMPLETE_NO_DESTROY`, 8 `EBVS`, 3 blank. No successful playback was recorded.

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

## Caveats

- Operations/outcomes count rows; "attempts by content" counts unique sessions.
- For 3015 rows the `pipeline_status` column holds a URL instead of a pipeline status (column shift in the flattened file).
- The 16 blank-span rows and 3 blank outcomes are unexplained.
