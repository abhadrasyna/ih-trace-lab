# CIR Related Exits — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**The POC (commit `38d767c`) is evidence, not a task. All tasks below are the formal build.**

**Execution order:** CMR-CIR-1 and CMR-CIR-2 can run now. CMR-CIR-3 and the data part of CMR-CIR-4 need `../concurrent-plays/` CMR-CP-2. CMR-CIR-5 needs CMR-CP-6 and its own go-ahead.

- [ ] **CMR-CIR-1** — Settle the open definition points and the report content with the user | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-CIR-2** — Explain the number: open stalls at the end, plays with no end event, seek proximity, sample sessions | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CIR-3** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CIR-4** — Close the data gaps: backgrounding as a session end, device type and playback type, then extend the report | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-CIR-5** — Formal recreation: graduate the POC into tested production code (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —

## Story done when

- **CMR-CIR-1** — The stall end rule, seek-grace reference point, impact-period scope, chart interval and report sections are written down, with Conviva's reference number if one exists.
- **CMR-CIR-2** — The 258 exits are split by cause (stall open at the end or recovered, seek proximity) with sample sessions, and the 181 plays without an end event are explained.
- **CMR-CIR-3** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-CIR-4** — A backgrounding signal and the device and playback-type splits are in the report, or the missing source is documented as a blocker.
- **CMR-CIR-5** — A tested CIR script, pure module and report writer exist in `investigations/conviva-metrics/scripts/`, built on the shared `src/lib/` helpers; the report and its queries are in the
  catalog and run for any tenant and date; the scratch copy is retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
