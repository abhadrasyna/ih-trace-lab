# Shared libs `mpd` and `crypto_signing` — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SLM-1, SLM-2, SLM-3, SLM-4.**

- [ ] **SLM-1** — audit the four originals and record the shared API for `mpd` and `crypto_signing` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **SLM-2** — build `src/lib/mpd/` (DASH MPD parser, `MpdError` boundary) with offline tests | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —
- [ ] **SLM-3** — build `src/lib/crypto_signing/` (JWS JSON signing, `SigningError` boundary) with offline tests | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA:
  —
- [ ] **SLM-4** — update taxonomy guide, code registry and `CONTEXT.md`; unblock dependent stories | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **SLM-1** — `docs/plan/shared-lib-mpd-crypto-signing/api.md` lists the public functions, inputs, outputs and errors for both modules, agreed with the user.
- **SLM-2** — `src/lib/mpd/` parses fixture MPDs into typed results and raises only `MpdError`; tests are green.
- **SLM-3** — `src/lib/crypto_signing/` signs and verifies JSON via JWS and raises only `SigningError`; tests are green with no real keys.
- **SLM-4** — the guide, registry and `CONTEXT.md` list both modules and the three dependent stories no longer treat them as missing.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `reference-code-gap-migration/README.md` where it is summarised and add one line to your
backlog/session-log file. When the whole story is done, archive it with `python scripts/dev/archive_completed_story.py shared-lib-mpd-crypto-signing`.
