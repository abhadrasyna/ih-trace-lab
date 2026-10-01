# Pre-implementation design review — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none — story complete.**

- [x] **PIR-1** — Deep review of 6 src-lib-migration + 2 pipeline-migration stories; write `spec.md`; apply autofixes | Owner: AI agent | Model: claude-sonnet-5 | Review: none | SHA: 0fccfe9
- [x] **PIR-2** — Process-parity check of 10 reference-code-gap-migration sub-stories; append to `spec.md`; apply the one autofix | Owner: AI agent | Model: claude-sonnet-5 | Review: none | SHA:
  <pending>
- [x] **PIR-3** — Consolidate flagged section; update `CONTEXT.md` | Owner: AI agent | Model: claude-sonnet-5 | Review: none | SHA: 0fccfe9

## Story done when

- **PIR-1** — `spec.md`'s src-lib-migration/pipeline-migration section is complete; the one blocking finding (ALI method-name mismatch) is fixed in `athena-lib-integration/stories.md`, not just
  reported.
- **PIR-2** — `spec.md`'s gap-migration section is complete; the design-time-diagram parity constraint is added to `reference-code-gap-migration/README.md`.
- **PIR-3** — `spec.md`'s "Flagged for human decision" section lists every judgment-call finding with enough context to act on without re-reading this session; `CONTEXT.md` is updated.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update `CONTEXT.md`'s "What Exists" with one line for this story and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's own convention — do not leave a done story half-archived.
