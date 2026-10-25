# mDRM analysis and DRM session funnel (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MDRM-1, MDRM-2, MDRM-3, MDRM-4, MDRM-5, MDRM-6.**

- [ ] **MDRM-1** — pure funnel logic: unique sessions, DRM-type split, license outcome, downstream error | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-2** — funnel CLI writing CSV plus markdown summary; first run on 2026-10-23 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-3** — license-chain quality report: statuses, 403/400 failures, retries, fcId consistency, part overlap | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-4** — device and policy report: brRef vs security level, FairPlay, VOD vs linear, hot-spots, cross-date brRef | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **MDRM-5** — wire the funnel into run_pipeline.py as a daily step; SCRIPTS.md and CONTEXT.md entries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-6** — docs: extra Lightstep attributes to export and the 2026-10-23 sample findings | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **MDRM-1** — every session lands in exactly one DRM bucket (widevine, fairplay, playready, none) and one license outcome; counts are split VOD/linear and by `source` (`merge` or `drm_only`).
- **MDRM-2** — the funnel CSV and markdown summary exist for ZA, GH and ZM on 2026-10-23 and the stage counts reconcile.
- **MDRM-3** — the report lists status-code counts per export, the 29 failing requests with device and household, requests per session, `fcId` mismatches and duplicate `fcId` across parts.
- **MDRM-4** — the report states `brRef` against Widevine security level, FairPlay device and OS split, VOD against linear, and whether `brRef` is constant across the available dates.
- **MDRM-5** — `run_pipeline.py --date` runs the funnel with a skip flag, and the registries list the new scripts.
- **MDRM-6** — the guide lists each extra attribute with the reason it is wanted, and records the sample findings.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then add one line to your backlog/session-log file. When the whole story is done, archive it with `python
scripts/dev/archive_completed_story.py ctap-smvod-mdrm-analysis`.
