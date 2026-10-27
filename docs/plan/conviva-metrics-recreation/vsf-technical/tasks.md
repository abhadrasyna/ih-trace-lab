# Video Start Failures Technical — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**The POCs (commits `005e774`, `fcb5b71`, `09346c7`, `09aa839`, `c15c2fc`, `a5d8043`, `10a590a`) are evidence, not tasks. All tasks below are the formal build.**

**Execution order:** CMR-VSFT-1 and CMR-VSFT-2 can run now. CMR-VSFT-3 and the data part of CMR-VSFT-4 need `../concurrent-plays/` CMR-CP-2. CMR-VSFT-5 needs CMR-CP-6 and its own go-ahead.

**Open: CMR-VSFT-1, CMR-VSFT-2, CMR-VSFT-3, CMR-VSFT-4, CMR-VSFT-5.**

- [ ] **CMR-VSFT-1** — Settle the open definition points and the report content with the user | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-VSFT-2** — Explain the number: attempts 3,954 against 3,901, the 10 extra sessions, the 16 sessions with no flat error row, multi-code sessions, the 6001 repeat households | Owner: Copilot
  CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-3** — Prove the POC generalises: run it for another tenant and another date | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-4** — Close the data gaps: business-error list, saved flat error export per tenant and date, bandwidth for 6001, device and playback type, then extend the report | Owner: Copilot CLI
  | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-5** — Formal recreation: graduate the POCs into tested production code and the option A report (separate go-ahead) | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —

## Story done when

- **CMR-VSFT-1** — The open definition points (business-error list owner, multi-code rule, late errors, bandwidth bands, chart sharing, the report sections) are written down, with Conviva's reference
  number if one exists.
- **CMR-VSFT-2** — The attempts mismatch, the 10 extra sessions, the 16 sessions with no flat error row and the multi-code counting each have a stated cause backed by sample sessions, and the 6001
  repeat households are described.
- **CMR-VSFT-3** — The POC runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.
- **CMR-VSFT-4** — The business-error list is supplied or recorded as a blocker, a saved flat error export exists for any tenant and date, and the bandwidth, device and playback-type gaps are closed
  or documented as blockers.
- **CMR-VSFT-5** — A tested VSF-T script, pure module and report writer exist in `investigations/conviva-metrics/scripts/`, built on the shared `src/lib/` helpers; the report matches the approved
  option A layout and runs for any tenant and date; its queries are in the catalog; the three scratch copies are retired.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
