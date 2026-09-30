# ctap-smvod investigation migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CSM-1, CSM-2, CSM-3, CSM-4, CSM-5, CSM-6, CSM-7.**

- [ ] **CSM-1** — Audit `ctap-smvod-session-report/scripts/` and produce a per-file lib-vs-script classification table | Owner: AI agent | Model: n/a | Review: human read-through | SHA: <—>
- [ ] **CSM-2** — Create `investigations/ctap-smvod/` skeleton + port business-logic scripts over `src/lib/*` | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **CSM-3** — Relocate manual Lightstep exports to `data/lightstep/`, ISO-prefixed | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **CSM-4** — Relocate Athena-pull inputs to `data/athena/` via `src/lib/athena` | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **CSM-5** — Migrate `output/` to PT-7's snapshot/range/rollup convention | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **CSM-6** — Extract the 45 query files into `query-catalog` | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **CSM-7** — Add tests + `RETENTION.md` + `CONTEXT.md` pointer | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>

## Story done when

- **CSM-1** — every file under `ctap-smvod-session-report/scripts/` is classified lib vs. script with the FCT-1 test stated per file; `scripts/lib/athena_runner.py` and `scripts/lib/aws_sso.py`
  confirmed **lib** (superseded, not re-ported), all `analyze_*`/`build_*`/`extract_*`/`merge_*`/`run_pipeline.py` confirmed **script**.
- **CSM-2** — `investigations/ctap-smvod/` exists with the PT-2 Rule B skeleton; `run_pipeline.py` and every business-logic script ported, importing `src/lib/{athena,auth,csv_io}` for every
  domain-mechanism concern.
- **CSM-3** — the 3 manually-exported Lightstep CSVs land in `data/lightstep/` with ISO-prefixed filenames; `run_pipeline.py`'s Step 1 guidance/file-not-found message points at the new path; Step 1
  itself remains a manual human action, not automated.
- **CSM-4** — Athena-pulled enrichment CSVs land in `data/athena/`, produced via `src/lib/athena` rather than `scripts/lib/athena_runner.py`.
- **CSM-5** — every output write in `output/` follows PT-7's snapshot/range/rollup filename convention; no `_DDMMYYYY`-style ad hoc suffix remains.
- **CSM-6** — all 45 query files' text lives in `query-catalog`'s catalog; zero inline SQL/query-string literals remain in `investigations/ctap-smvod/`.
- **CSM-7** — every ported business-logic script has a happy-path + edge-case test with no live Athena/Lightstep calls; `RETENTION.md` states the investigation is rolling with no close-out; the epic's
  `CONTEXT.md` pointer line is added.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story list and add one line to your backlog/session-log file. When the
whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
