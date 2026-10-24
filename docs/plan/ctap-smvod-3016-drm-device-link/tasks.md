# 3016 DRM device link (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: DRM-3, DRM-4.**

- [x] **DRM-1** — readers for the saved mdrmfe, Widevine, PlayReady, FairPlay and LRM CSVs | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: 84a9dfa
- [x] **DRM-2** — join builder: sessionId to fcid to CDM, with explicit missing-row outcomes | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: fd35f82
- [ ] **DRM-3** — add DRM columns to the events CSV and write a per-device-model summary | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **DRM-4** — first real ZA run, usage doc, SCRIPTS.md and CONTEXT.md entries | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **DRM-1** — each reader returns typed rows, tolerates the UI export's BOM, and fails loudly on a missing expected column; FairPlay `FP_SPC_contents` is parsed to device type, OS and security level.
- **DRM-2** — every event gets exactly one outcome: joined, no license request, or no CDM row; empty `sessionId`, `fcid` or `fcId` never join.
- **DRM-3** — the events CSV carries the new columns and its row count is unchanged; the device-model summary counts events and households and says whether the license was issued.
- **DRM-4** — the run on ZA 2026-10-22 reconciles, and the usage doc, `SCRIPTS.md` and `CONTEXT.md` list the new scripts.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then add one line to your backlog/session-log file. When the whole story is done, archive it with `python
scripts/dev/archive_completed_story.py ctap-smvod-3016-drm-device-link`.
