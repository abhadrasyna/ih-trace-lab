# Video Start Failures Technical — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**The POCs (commits `005e774`, `fcb5b71`, `09346c7`, `09aa839`, `c15c2fc`, `a5d8043`, `10a590a`) are evidence, not tasks. Every task below builds a formal, tested piece (CMR-VSFT-1 is the only
discussion task).**

**Execution order:** CMR-VSFT-1 can run now. CMR-VSFT-2, CMR-VSFT-3 and CMR-VSFT-4 are pure modules and a runner that need no other story. CMR-VSFT-5 builds on 2 to 4. CMR-VSFT-6 needs
`../concurrent-plays/` CMR-CP-6 (shared loader, chart, breakdown and report helpers). CMR-VSFT-7 needs CMR-CP-2 (raw export for any tenant and date).

**Open: CMR-VSFT-1, CMR-VSFT-2, CMR-VSFT-3, CMR-VSFT-4, CMR-VSFT-5, CMR-VSFT-6, CMR-VSFT-7.**

- [ ] **CMR-VSFT-1** — Settle the open definition points and the report content with the user | Owner: Copilot CLI | Model: n/a | Review: none | SHA: —
- [ ] **CMR-VSFT-2** — Build the VSF-T core: start-failure detection, VSF-T/VSF-B classification and bucketing, as a pure, tested module | Owner: Copilot CLI | Model: n/a | Review: code-reviewer |
  SHA: —
- [ ] **CMR-VSFT-3** — Build the error-codes table: shares, impacted households, sessions per household and first/last seen, as a pure, tested module | Owner: Copilot CLI | Model: n/a | Review:
  code-reviewer | SHA: —
- [ ] **CMR-VSFT-4** — Build the flat error eventdata export: catalogued query, runner with a saved export, offline tests | Owner: Copilot CLI | Model: n/a | Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-5** — Build the per-code detail tables: first-error grouping, bandwidth bands, percentiles and the spacer-column table, as pure, tested code | Owner: Copilot CLI | Model: n/a |
  Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-6** — Build the report and the script: option A report writer, chart, on-demand and daily run, device and playback type; retire the scratch POCs | Owner: Copilot CLI | Model: n/a |
  Review: code-reviewer | SHA: —
- [ ] **CMR-VSFT-7** — Prove it generalises: run for another tenant and another date, fix hardcoded assumptions, document per-tenant mappings | Owner: Copilot CLI | Model: n/a | Review: code-reviewer
  | SHA: —

## Story done when

- **CMR-VSFT-1** — The open definition points (business-error list owner, multi-code rule, late errors, bandwidth bands, chart sharing, the report sections) are written down, with Conviva's reference
  number if one exists.
- **CMR-VSFT-2** — A tested pure module detects start failures, classifies VSF-T and VSF-B by a configurable list and buckets by interval, and reproduces the POC's 2,101 VSF-T on the ZA day.
- **CMR-VSFT-3** — A tested pure module returns the error-codes table rows and reproduces the approved table on the ZA day.
- **CMR-VSFT-4** — A catalogued query, a tested runner and a saved flat error export exist for ZA, 2026-10-24, with `--date`, `--tenant`, `--dry-run` and `--force`.
- **CMR-VSFT-5** — Tested pure code returns the detail tables for 6001, 3016, 1003 and E31012 and reproduces the approved option A numbers.
- **CMR-VSFT-6** — A tested script and report writer produce the option A report from the saved exports for any tenant and date, in an on-demand and a daily run, on the shared `src/lib/` helpers; the
  three scratch copies are retired.
- **CMR-VSFT-7** — The script runs for a second tenant and a second date with only arguments changed; any per-tenant mapping is documented.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's row in the epic `README.md` status column and add one line to the backlog/session-log file. When the whole
story is done, archive it per the project convention.
