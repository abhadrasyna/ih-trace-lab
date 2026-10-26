# Session lifecycle report (ctap-smvod) — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6.** Depends on `session-error-model/` (EM-2, EM-4) and `session-presence-funnel/` (PF-4, PF-8) before SL-2; LC-2 before GH/ZM validation in SL-6.

- [ ] **SL-1** — Export completeness check per tenant, date and kind (rows, parts, windows, caps, consistency) with a status and an export checklist | Owner: Copilot CLI | Model: claude-sonnet-5.5 |
  Review: code-reviewer | SHA: —
- [ ] **SL-2** — Lifecycle model on the PF-8 matrix: furthest hop, path, hop timestamps and latencies, cohort columns, VOD/linear split | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer | SHA: —
- [ ] **SL-3** — Daily per-tenant summary markdown with charts and explanations generated from the CSVs | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SL-4** — `run_pipeline.py` step for every tenant and the lifecycle trend upsert | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer | SHA: —
- [ ] **SL-5** — Exploratory sankey and per-session timeline prototypes in `scratch/` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **SL-6** — Validate ZA, then GH and ZM after LC-2; NG onboarding note; docs and `CONTEXT.md` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —

## Story done when

- **SL-1** — For any tenant and date, one command writes the completeness CSV with a status and reason per kind, and reproduces the ZA 2026-10-21 and 2026-10-24 and GH 2026-10-24 baselines in
  `stories.md`.
- **SL-2** — The lifecycle CSVs reproduce the ZA 2026-10-24 furthest-hop and timing figures in `prompt.md` within the late-ingest tolerance; linear sessions without a setup export are
  `linear_not_covered`.
- **SL-3** — The summary markdown for ZA 2026-10-24 renders every section with its chart, every number traces to a CSV, small-n rates are suppressed, and the error-codes chart is not linked.
- **SL-4** — The daily pipeline writes the report and upserts one trend row per tenant and date, with no per-tenant code.
- **SL-5** — The two prototypes exist in `scratch/` and are registered; any promotion is a separate approved task.
- **SL-6** — ZA, GH and ZM validation notes and the NG onboarding checklist exist, no tenant is hardcoded, and `CONTEXT.md` is updated.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` and add one line to your backlog/session-log file. When the whole story is
done, archive per `docs/plan/README.md`.
