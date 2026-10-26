# Linear session coverage (ctap-smvod) — prompt

> Fix the VOD-only blind spot: the ctap-smvod Lightstep export and merge only see `sm-vod` sessions, so linear playback (ZM, GH) is mis-reported or missing.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

The `YYYY-MM-DD_smvod.csv` Lightstep export was built from a query filtered to `service == "sm-vod"`, so every report downstream (merge, error reports, DRM funnel) measures VOD sessions only. Linear
playback (`sm-linear`, session ids `abr-linear-<uuid>`) is possible in Zambia (ZM, `busUnitId` `dtunf6yo`) and Ghana (GH, `busUnitId` `apbyfj9d`), so a share of real sessions was never counted. This
was a defect in the original design, not handled when the pipeline was built.

Evidence (ZM, 2026-10-24, read-only check): 21 `sm-linear` SetupSession sessions vs 94 VOD rows. All 20 linear traces checked are already in `2026-10-24_ctap.csv`, which is exactly why ctap has 20
more traces than smvod (114 vs 94). `merge_ctap_smvod_csv.py` therefore emits them as `ctap_only (no SM-VOD session data…)` rows with blank session fields. Linear sessions also appear in the mDRM
`mdrmfe` export, but not in `smvod-ts`. Linear sessions have an empty `externalPackageId`, a channel-name `contentId` (e.g. `009_Nolly Africa`) and a `playbackURL` on `sa-live.cdn.yellotv.mtn.com`
(VOD uses the `vod-dai-ott-eu2.ssai…` SSAI host), so `content_uuid` extraction (`/vod[a-z]/<uuid>/`) returns blank for linear.

The corrected export query (per tenant, one run each for ZM and GH; project `mcs-go-prod-mtn-1-eu`, resolve with `scripts/resolve_tenant.py`):

```
spans count
| delta
| filter (service == "sm-linear" || service == "sm-vod") && session.api == "SetupSession" && span.kind == "server" && busUnitId == "<busUnitId>"
| group_by ["householdId", "deviceId", "session.clientIp", "sessionId", "contentId", "externalPackageId", "lightstep.trace_id", "playbackURL", "busUnitId"], sum
```

This story is opened as the defect record and **will be appended to as the work progresses**; tasks and open questions below are the starting point, not the final list.

## Scope guard

In bounds: `investigations/ctap-smvod/scripts/` (merge, pipeline summary, downstream reports that assume VOD), their tests, and `investigations/ctap-smvod/docs/` plus `CONTEXT.md`. Out of bounds:
other investigations, the mDRM scripts' DRM logic (already kind-aware via `session_kind`), and tenants other than ZM/GH until linear is confirmed possible there. Changes runtime behaviour of the merge
and the reports; no schema/storage change. Re-exporting Lightstep data is a manual step by the user (MCP/UI), not done by scripts here.

## Session-start load hints

- `investigations/ctap-smvod/scripts/merge_ctap_smvod_csv.py` (merge key `lightstep.trace_id`, `SMVOD_FIELDS`, `extract_content_uuid`).
- `investigations/ctap-smvod/scripts/lib/drm_funnel.py` (`session_kind`) for the existing VOD/linear split.
- `docs/guides/tenant-resolution.md` before any Lightstep call (shared project: use the resolved filter).
- `investigations/ctap-smvod/docs/lightstep-drm-exports.md` for the export conventions.

## Task overview

- **LC-1** — Update the documented Lightstep export queries (smvod and smvod-ts) to include `sm-linear`, for ZM and GH.
- **LC-2** — Merge: add `session_type` and a linear-safe content key; stop emitting linear as `ctap_only`.
- **LC-3** — Audit and fix downstream scripts and pipeline summaries that assume VOD.
- **LC-4** — Validate end to end on one day for ZM and GH; update docs and `CONTEXT.md`.

## Definition of done

A re-exported ZM and GH day runs through `run_pipeline.py` with linear sessions matched to their CTAP traces (no linear `ctap_only` rows), carrying a `session_type` column, and every downstream report
either handles linear or documents why it skips it. See `tasks.md` "Story done when".

## Open questions (append answers here)

- Does the Athena `ctap-smvod-playback-outcome` query cover linear sessions?
- Is the linear `playbackURL` host/path the right key for linear CDN correlation (`correlate_cdn_ips.py`)?
- Is linear playback possible in any other tenant (ZA)? Check before widening scope.
- Should the `_smvod.csv` file name be kept (alias) or renamed once both types are handled?

## Perspectives not covered

- Historical exports before this fix stay VOD-only; no backfill of past dates is planned here.
- End-to-end session tracing from creation to failure (the broader goal that motivated this) is a separate story that builds on this one.
