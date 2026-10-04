# Logging framework rollout — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none.**

- [x] **LFR-1** — Build the `init_logging()` bootstrap (setup + FCID bind + formatter wiring + redaction) | Owner: AI agent | Model: n/a | Review: tests green | SHA: 6529c9c
- [x] **LFR-2** — Define the minimum logging contract; apply it to the Athena adapter + `aws_access_cli` business logic | Owner: AI agent | Model: n/a | Review: tests green | SHA: 2038167
- [x] **LFR-3** — Wire the bootstrap into every `aws_access_cli` entry point; separate preview output from the log stream | Owner: AI agent | Model: n/a | Review: tests green + `py-code-review` | SHA:
  473621c
- [x] **LFR-4** — Add a binding "Logging" section to `code-review-checklist.md`; update `CONTEXT.md` | Owner: AI agent | Model: n/a | Review: none | SHA: 591c4b2
- [x] **LFR-5** — Dated coordination notes in unretrofitted consumers (`investigations/ctap-smvod`, remaining dev scripts) | Owner: AI agent | Model: n/a | Review: none | SHA: 7d21bcf

## Story done when

- **LFR-1** — `src/lib/logging/bootstrap.py`'s `init_logging(entry_point_slug, level="INFO") -> str` exists, returns the bound FCID, and is covered by a happy-path test (FCID bound + visible in a
  captured log record) and an edge-case test (calling it twice in one process does not duplicate handlers, matching `setup_logging()`'s own `force=True` contract). `redact_params()` matches FCID-1's
  original spec (allow-listed keys only, everything else masked).
- **LFR-2** — `docs/refactor/logging-and-correlation-id.md` states the minimum contract (run start/end, external-call start/success/failure, row counts, durations — each at a named level) in one new
  section; `src/lib/athena/adapter.py` and `src/pipelines/aws_access_cli/{adoption,shaka_errors,position_report}.py` each emit it, verified by a `caplog`-based test per module.
- **LFR-3** — every `src/pipelines/aws_access_cli/scripts/run_*.py` calls `init_logging()` before any other logic; `scripts/common.py`'s `print(render_summary(...))` calls are gated so a cron
  invocation no longer interleaves report-preview tables into the operational log file.
- **LFR-4** — `code-review-checklist.md` has a new numbered "Logging" section (same one-box-per-trigger shape as its existing FCID section); `CONTEXT.md`'s `src/lib/logging/context.py` bullet no
  longer says "not yet owned by any `docs/plan/` task."
- **LFR-5** — `investigations/ctap-smvod/` and any other unretrofitted entry point's own planning/README doc carries one dated line: "this story does not implement the logging bootstrap here; see
  `docs/plan/logging-framework/` — coordination record only."

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `CONTEXT.md`'s "What Exists" and add one line to your backlog/session-log file. When the whole
story is done, archive it per `docs/plan/README.md`'s convention (`python scripts/dev/archive_completed_story.py logging-framework`) — do not leave a done story half-archived.
