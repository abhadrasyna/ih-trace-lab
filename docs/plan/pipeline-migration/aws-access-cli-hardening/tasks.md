# aws-access-cli hardening — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: AAH-1, AAH-2, AAH-3, AAH-4, AAH-5, AAH-6, AAH-7, AAH-8, AAH-9, AAH-10.**

- [ ] **AAH-1** — Add run summary record and non-zero-exit alerting to the schedule | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: <—>
- [ ] **AAH-2** — Isolate preflight failure and add mid-run SSO re-check | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: <—>
- [ ] **AAH-3** — Add per-unit timeout and per-metric isolation | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: <—>
- [ ] **AAH-4** — Add empty-day sentinel for header-only CSVs | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: <—>
- [ ] **AAH-5** — Fix `--force` scope across catch-up dates and document it | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **AAH-6** — Add output and log retention script | Owner: AI agent | Model: n/a | Review: tests green + dry-run read by human | SHA: <—>
- [ ] **AAH-7** — Add `ReportSpec` registry and one `run_report` | Owner: AI agent | Model: n/a | Review: tests green + CSV parity diff + code-reviewer | SHA: <—>
- [ ] **AAH-8** — Deduplicate date, batch and error-code helpers | Owner: AI agent | Model: n/a | Review: tests green | SHA: <—>
- [ ] **AAH-9** — Merge shaka queries and combine `unified_sessions` metrics | Owner: AI agent | Model: n/a | Review: tests green + CSV parity diff on a sample day | SHA: <—>
- [ ] **AAH-10** — Parallelise tenants with a bounded pool | Owner: AI agent | Model: n/a | Review: tests green + code-reviewer | SHA: <—>

## Story done when

- **AAH-1** — every run writes `logs/aws_access_cli_status.json` listing each tenant/report/period unit with status and duration, and exits non-zero when any unit failed.
- **AAH-2** — a preflight failure is logged and returns exit 1 without a traceback abort, and an auth error mid-run triggers one re-check before the unit is marked failed.
- **AAH-3** — one hung or failing metric or unit cannot stall the run past its timeout; the failed date is not written partially.
- **AAH-4** — a date with genuinely no events is recorded once and not re-queried by later runs, while a failed run still retries.
- **AAH-5** — `--force` re-runs every date in the catch-up window, or the help text states the last-date-only rule, with a test for the chosen behaviour.
- **AAH-6** — a retention script prunes old position CSVs, `.out` files and `app.log` by configured age, defaults to dry-run, and is listed in `SCRIPTS.md`.
- **AAH-7** — daily, weekly and monthly wrappers share one `REPORTS` registry and one `run_report`; CSV output is byte-identical to the pre-refactor baseline for the sampled days.
- **AAH-8** — each of `_iso_date`, next-day, `_batched` and the 1001–1010 error-code list is defined once, and unused `build_error_1xxx_session_ids` is removed or used.
- **AAH-9** — shaka-hhid and shaka-session come from one query per tenant-day and the `unified_sessions` metrics from fewer queries, with identical CSV content; the new per-run query count is
  recorded.
- **AAH-10** — tenants run concurrently with a configurable cap and no interleaved CSV writes, with throttling backoff still honoured.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story list and add one line to your backlog/session-log file. When the
whole story is done, archive it per your project's own convention — do not leave a done story half-archived.
