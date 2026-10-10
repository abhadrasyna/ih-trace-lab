# Monthly error code pipeline — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec. Every deliverable is generated for all four OpCos (ZA, NG, ZM, GH) for the month being analysed (September 2026 first).

**Open: MEC-0, MEC-1, MEC-2, MEC-3, MEC-4, MEC-5, MEC-6, MEC-7.**

- [ ] **MEC-0** — September adoption-session-report CSV for all OpCos, via a month orchestrator over the existing aws_access_cli runner | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-1** — September adoption-report (household counts) CSV for all OpCos, via the same orchestrator | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-2** — September adoption-gap-analysis-session CSV for all OpCos, with the attempts_sum_check column | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA: —
- [ ] **MEC-3** — define error-code source and count grain; add the monthly error-code catalog query (pending dedup decision) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer
  hook | SHA: —
- [ ] **MEC-4** — finalize runbook, usage.md, SCRIPTS.md | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **MEC-5** — verify one playback outcome per session (raw-data check before the adoption CSVs are trusted; run before MEC-2 sign-off) | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-reviewer hook | SHA: —
- [ ] **MEC-6** — join the session and household adoption CSVs into per-day concentration ratios (sessions per household, share of households affected) | Owner: Copilot CLI | Model: claude-sonnet-5.5
  | Review: code-reviewer hook | SHA: —
- [ ] **MEC-7** — top-N households by VSF/EBVS sessions for the month, to name any small group driving the failures | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-reviewer hook | SHA:
  —

## Story done when

- **MEC-0** — `output/<OPCO>/daily/2026-09_adoption-session-report.csv` exists in this investigation for all four OpCos, one row per day 2026-09-01..30 with the four session columns.
- **MEC-1** — `output/<OPCO>/daily/2026-09_adoption-report.csv` exists for all four OpCos, one row per day with the six household columns.
- **MEC-2** — a September `adoption-gap-analysis-session` CSV exists under `output/<OPCO>/daily/` for all four OpCos, with the three gap columns, `attempts_sum_check` and
  `attempts_sum_check_adjusted`.
- **MEC-3** — the table, error field and count grain are documented, and a catalog query renders for any OpCo and month.
- **MEC-4** — `usage.md` documents every script and the run order, and `SCRIPTS.md` registers them.
- **MEC-5** — `output/<OPCO>/daily/2026-09_playback-outcome-uniqueness-check.csv` exists for all four OpCos with one row per day; the script exits non-zero if any day has a session in more than one
  playback outcome or the outcome buckets do not sum to attempts.
- **MEC-6** — `output/<OPCO>/daily/2026-09_household-concentration.csv` exists for all four OpCos with one row per day and the ratio columns for attempts, success, VSF and EBVS.
- **MEC-7** — `output/<OPCO>/daily/2026-09_top-vsf-households.csv` exists for all four OpCos with the top-N households and their share of the month's VSF and EBVS sessions.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status wherever it is summarised and add one line to the backlog/session-log file. When the whole story is
done, archive it per the repo convention — do not leave a done story half-archived.
