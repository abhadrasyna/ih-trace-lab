# Vod asset knowledge harvest — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: VAK-1, VAK-2.**

- [ ] **VAK-1** — `knowledge/vod-asset-field-mapping.md`: harvest ID-navigation + field-mapping docs from `vod-asset-ingestion-mapping/` | Owner: AI agent (Copilot CLI) | Model: claude-sonnet-5 |
  Review: human diff review | SHA: <—>
- [ ] **VAK-2** — `knowledge/vod-asset-ingestion-pipeline.md` + `knowledge/ctap-smvod-pipeline.md`: port + correct root `knowledge/` distillations, add applauseInvestigation pointer | Owner: AI agent
  (Copilot CLI) | Model: claude-sonnet-5 | Review: human diff review | SHA: <—>

## Story done when

- **VAK-1** — `knowledge/vod-asset-field-mapping.md` exists, contains the four-ID-family navigation table (Physical Content ID / Internal Content ID / Package Asset ID / Show-Season ID) and the
  ADI→`contentInstances`→MongoDB field correspondence tables, plus a short note on the auto-generated `common-field-mapping*.md` matrix and where to find it if a fresher regeneration is ever needed
  (without porting the generator scripts themselves).
- **VAK-2** — `knowledge/vod-asset-ingestion-pipeline.md` and `knowledge/ctap-smvod-pipeline.md` both exist in `ih-trace-lab`, the MongoDB "open gap" claim in the former is corrected to reflect
  `STATUS.md`'s stage-6 closure, both cross-link to `knowledge/vod-asset-field-mapping.md` instead of repeating its tables, and `vod-asset-ingestion-pipeline.md` carries one clearly-labeled pointer to
  `applauseInvestigation/knowledge/lightstep-span-attributes-by-service.md` marked as not-yet-harvested / deferred to a future `applauseInvestigation`-scoped story.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it per your project's own convention — do not leave a done story half-archived.
