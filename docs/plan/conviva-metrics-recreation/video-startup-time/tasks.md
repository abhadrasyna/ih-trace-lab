# Video Startup Time — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**The POC (commits `e52661a` and `e8d27d9`) is evidence, not a task. All tasks below are the formal build.**

**Execution order:** CMR-VST-1 and CMR-VST-2 can run now. CMR-VST-3 and the data part of CMR-VST-4 need `../concurrent-plays/` CMR-CP-2. CMR-VST-5 needs CMR-CP-6 and its own go-ahead.

**Open: CMR-VST-1, CMR-VST-2, CMR-VST-3, CMR-VST-4, CMR-VST-5.**

- [ ] **CMR-VST-1** — Settle the open definition points and the report content with the user | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-VST-2** — Explain the number: the two chart spikes, plays without a `CREATE`, `startup_time_ms` against the debug-event delta | Owner: Copilot CLI | Model: n/a | Review: code-reviewer |
  SHA: —
- [ ] **CMR-VST-3** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-VST-4** — Close the data gaps: Conviva's distribution ranges, heartbeat gap and pre-roll rules, device and playback type, then extend the report | Owner: Copilot CLI | Model: n/a | Review:
  code-reviewer | SHA: —
- [ ] **CMR-VST-5** — Formal recreation: graduate the POC into tested production code (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —

## Story done when

- **CMR-VST-1** — The open definition points (plays without a `CREATE`, retried or revived starts, the interval, the report sections) are written down, with Conviva's reference number if one exists.
- **CMR-VST-2** — The two spikes are explained from the sessions behind them, the 5 `session.csv` plays without a value and any play without a `CREATE` are explained, and the two startup measures are
  reconciled.
- **CMR-VST-3** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-VST-4** — Conviva's distribution ranges, the heartbeat-gap and pre-roll rules and the device and playback-type splits are in the report, or the missing source is documented as a blocker.
- **CMR-VST-5** — A tested VST script, pure module and report writer exist in `investigations/conviva-metrics/scripts/`, built on the shared `src/lib/` helpers; the report and its queries are in the
  catalog and run for any tenant and date; the scratch copy is retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
