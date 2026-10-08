# CTAP/SM-VOD multi-tenant support — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MT-4, MT-5, MT-6, MT-7, MT-8, MT-9, MT-10.**

- [x] **MT-1** — audit tenant-specific hardcoding in ctap-smvod scripts/SQL; record findings | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: 8d871b2
- [x] **MT-2** — tenant-namespaced input/output paths in `runtime.py` + `data_paths.yaml` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: 222de48
- [x] **MT-3** — tenant context resolution + input discovery; Athena steps use registry values | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: fd19d54
- [ ] **MT-4** — `run_pipeline.py` all-tenants default, `--tenant`, continue-on-failure | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —
- [ ] **MT-5** — `busUnitId` guard for shared Lightstep projects at merge | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —
- [ ] **MT-6** — `git mv` existing SA data/output under the SA tenant folder | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **MT-7** — Zambia pilot run for one date + sanity checks vs Ghana | Owner: Copilot CLI + user | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **MT-8** — add `is_wv` column to the 1xxx/6xxx error report (CSV + xlsx); move `_is_wv` to `scripts/lib/` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —
- [ ] **MT-9** — rerun empty-`raw_user_agent` dates (e.g. 2026-10-02) per tenant; regenerate error-report CSVs/xlsx | Owner: Copilot CLI + user | Model: claude-sonnet-5.5 | Review: user | SHA: —
- [ ] **MT-10** — update `usage.md`, `CONTEXT.md`; final review | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review-checklist | SHA: —

## Story done when

- **MT-1** — every tenant-specific hardcode is listed in `stories.md` with file and line.
- **MT-2** — path helpers return `<TENANT>`-scoped paths; no script builds tenant paths by hand.
- **MT-3** — tenant context is resolved once from `config/tenants.yaml`; unknown tenant or missing input folder fails with a message naming the expected path.
- **MT-4** — no flag runs every tenant with input for the date; `--tenant` runs one; failures are collected and the exit code is non-zero if any tenant failed.
- **MT-5** — a Zambia file containing another tenant's `busUnitId` fails the merge loudly.
- **MT-6** — SA history preserved via `git mv`; SA reruns reproduce prior outputs.
- **MT-7** — Zambia produces the full output set for one date; row counts reconcile with the export.
- **MT-8** — every error-report row has `is_wv` (true/false, blank when no user agent); the xlsx carries it; `_is_wv` lives in `scripts/lib/` and `analyze_webview_devices.py` imports it.
- **MT-9** — no error-report row is left with a blank user agent because of stale outputs.
- **MT-10** — docs and `CONTEXT.md` reflect the new layout; tests green.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to your backlog/session-log file. When the whole story
is done, archive it with `scripts/dev/archive_completed_story.py ctap-smvod-multitenant`.
