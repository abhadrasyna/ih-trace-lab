# Linear session coverage (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: LC-1, LC-2, LC-3, LC-4.**

- [ ] **LC-1** — Document the smvod and smvod-ts Lightstep queries (include `sm-linear`, add `http.status_code`) as a per-tenant template | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none
  | SHA: —
- [ ] **LC-2** — Merge adds `session_type`, a linear-safe content key and optional `http.status_code`/`setup_failed`; no linear `ctap_only` rows | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —
- [ ] **LC-3** — Audit and fix downstream scripts and pipeline summaries that assume VOD | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **LC-4** — Validate ZM and GH linear days plus a VOD-only day end to end; confirm no hardcoded tenants; update docs and CONTEXT.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none
  | SHA: —

## Story done when

- **LC-1** — The export docs give the corrected query as a template parameterised by tenant `busUnitId`, for smvod and smvod-ts, with ZM and GH as worked examples.
- **LC-2** — Merged output has a `session_type` (vod/linear) column and linear rows match their CTAP trace; `http.status_code` is carried when present and `setup_failed` marks pre-session failures;
  tests cover a linear row, a blank `externalPackageId`, a 403 row and an old export.
- **LC-3** — Each VOD-assuming script is either fixed or documented as VOD-only, and the pipeline summary reports counts per `session_type`.
- **LC-4** — Re-exported ZM and GH days run clean, a VOD-only day is unchanged, no tenant code or id is hardcoded in scripts or tests, the open questions in `prompt.md` are answered, and `CONTEXT.md`
  and `usage.md` are current.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it with `python scripts/dev/archive_completed_story.py linear-session-coverage`.
