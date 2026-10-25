# mDRM analysis and DRM session funnel (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MDRM-2c, MDRM-2d, MDRM-2e, MDRM-3, MDRM-4, MDRM-5, MDRM-6.**

- [x] **MDRM-1** — pure funnel logic: unique sessions, DRM-type split, license outcome, downstream error | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: e7ee80c
- [x] **MDRM-2** — funnel CLI writing CSV plus markdown summary; first run on 2026-10-23 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 614c3e6
- [x] **MDRM-2a** — shared stacked-bar chart: theme series palette and render_stacked_bar in src/lib/charts, guide update | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA:
  426089a
- [x] **MDRM-2b** — funnel charts (stage funnel, DRM split, license outcome per DRM type) embedded in the markdown summary | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: 257b393
- [ ] **MDRM-2c** — split "ended in error" by error code and license outcome; 3016 finding as a table | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-2d** — 3014/3015/3016 triage sub-categories by license outcome, reusing the classifier | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-2e** — shared pie/donut chart in src/lib/charts and error-code and sub-category charts in the funnel markdown | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **MDRM-3** — license-chain quality report: statuses, 403/400 failures, retries, fcId consistency, part overlap | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-4** — device and policy report: brRef vs security level, FairPlay, VOD vs linear, hot-spots, cross-date brRef | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer |
  SHA: —
- [ ] **MDRM-5** — wire the funnel into run_pipeline.py as a daily step; SCRIPTS.md and CONTEXT.md entries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **MDRM-6** — docs: extra Lightstep attributes to export and the 2026-10-23 sample findings | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **MDRM-1** — every session lands in exactly one DRM bucket (widevine, fairplay, playready, none) and one license outcome; counts are split VOD/linear and by `source` (`merge` or `drm_only`).
- **MDRM-2** — the funnel CSV and markdown summary exist for ZA, GH and ZM on 2026-10-23 and the stage counts reconcile.
- **MDRM-2a** — `render_stacked_bar` returns themed PNG bytes (vertical or horizontal) or a `ChartError`; series colours come from the theme palette only and the guard test still passes.
- **MDRM-2b** — three PNGs per OpCo and date under `output/<OPCO>/charts/` and embedded in the funnel markdown; a chart failure is logged and the CSV and markdown are still written without the link.
- **MDRM-2c** — the markdown lists errored sessions by exact error code with the license outcome split, and a 3014/3015/3016 table by license outcome; counts reconcile to the errored total.
- **MDRM-2d** — the markdown lists 3014/3015/3016 sessions by triage sub-category and license outcome; the total equals the 3014/3015/3016 sessions in the MDRM-2c table.
- **MDRM-2e** — `render_pie` returns themed PNG bytes or a `ChartError`; two error-mix charts per OpCo and date are embedded in the funnel markdown, and a chart failure never blocks the CSV or
  markdown.
- **MDRM-3** — the report lists status-code counts per export, the 29 failing requests with device and household, requests per session, `fcId` mismatches and duplicate `fcId` across parts.
- **MDRM-4** — the report states `brRef` against Widevine security level, FairPlay device and OS split, VOD against linear, and whether `brRef` is constant across the available dates.
- **MDRM-5** — `run_pipeline.py --date` runs the funnel with a skip flag, and the registries list the new scripts.
- **MDRM-6** — the guide lists each extra attribute with the reason it is wanted, and records the sample findings.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then add one line to your backlog/session-log file. When the whole story is done, archive it with `python
scripts/dev/archive_completed_story.py ctap-smvod-mdrm-analysis`.
