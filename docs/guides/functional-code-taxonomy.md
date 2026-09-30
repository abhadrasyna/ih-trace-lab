# Functional code taxonomy

Use this guide when deciding whether logic belongs in a shared `src/lib/` module or stays inside one pipeline, investigation, tool, or experiment. It names the six shared-library targets this repo is
building toward and the specific `github_copilot` originals they replace.

## Modules

### `src/lib/auth/`

`src/lib/auth/` owns AWS SSO session refresh and related credential-bootstrap behavior that is the same no matter which pipeline or investigation needs temporary cloud access. Its first replaced
original is `github_copilot/aws-access-cli/scripts/refresh_aws_sso.py`, which currently keeps the refresh workflow private to one pipeline even though the concern is infrastructure, not business
logic. Status: not yet implemented — first real port happens when a follow-up story needs it.

### `src/lib/athena/`

`src/lib/athena/` owns the canonical Athena query start, poll, and result-download client so future callers inject one shared executor instead of each project constructing its own boto3-facing flow.
It replaces the duplicated execution pattern currently split across `github_copilot/oasis-athena-mcp/src/athena_mcp/query_tools.py`,
`github_copilot/ctap-smvod-session-report/scripts/lib/athena_runner.py`, `github_copilot/aws-access-cli/scripts/athena_runner/query_executor.py`, and
`github_copilot/mtn-zm-session-device-investigation/scripts/run_athena_query.py`. Status: not yet implemented — first real port happens when a follow-up story needs it.

### `src/lib/csv_io/`

`src/lib/csv_io/` owns shared CSV and tabular report reading and writing so projects stop carrying private `csv.DictWriter` or `DataFrame.to_csv()` blocks that differ only in column selection. It
replaces the ad hoc writers now spread across `github_copilot/aws-access-cli/scripts/run_incomplete_no_destroy_investigation.py`,
`github_copilot/aws-access-cli/scripts/run_adoption_gap_analysis_report.py`, `github_copilot/aws-access-cli/scripts/run_adoption_gap_analysis_session_report.py`,
`github_copilot/aws-access-cli/scripts/athena_runner/adoption/period_report_store.py`, `github_copilot/aws-access-cli/scripts/athena_runner/adoption/report_store.py`,
`github_copilot/applauseInvestigation/scripts/analyze_athena_playback.py`, `github_copilot/mtn-network-traffic/scripts/curl_timer/report.py`, and the matching CSV/report emitters in
`github_copilot/ctap-smvod-session-report` and `github_copilot/mtn-zm-session-device-investigation`. Status: not yet implemented — first real port happens when a follow-up story needs it.

### `src/lib/report_render/`

`src/lib/report_render/` owns rendering normalized rows into human-facing output such as markdown tables, console summaries, and report sections, while `csv_io` stays focused on file input and output.
Its first replaced originals are the per-project markdown/table builders in `github_copilot/mtn-network-traffic/scripts/curl_timer/report.py` and the various investigation- and pipeline-specific
summary loops that currently live inline beside CSV-writing code. Status: not yet implemented — first real port happens when a follow-up story needs it.

### `src/lib/har/`

`src/lib/har/` owns HAR capture entry loading and normalization so one project, or even one script inside a project, does not re-implement the same `har["log"]["entries"]` walk. It replaces the
function-body-level duplicates in `github_copilot/applauseInvestigation/scripts/analyze_har.py::iter_entries()`,
`github_copilot/vod-playback-timing-probe/scripts/extract_content_ids_from_har.py::_load_entries()`, `github_copilot/vod-playback-timing-probe/scripts/summarize_har_playbacks.py::_load_entries()`, and
`github_copilot/vod-asset-ingestion-mapping/scripts/lib/har_parser.py::load_json_entries()`. Status: not yet implemented — first real port happens when a follow-up story needs it.

### `src/lib/curl_to_python/`

`src/lib/curl_to_python/` owns curl-command parsing and curl-to-Python conversion that can be reused by any future traffic-capture or replay workflow instead of staying private to one diagnostics
tool. Its first replaced originals are `github_copilot/mtn-network-traffic/scripts/curl_timer/blocks.py`, `github_copilot/mtn-network-traffic/scripts/curl_timer/curl_timing.py`,
`github_copilot/mtn-network-traffic/scripts/time_curl_requests.py`, and `github_copilot/mtn-network-traffic/scripts/inspect_curl_auth.py`, which all parse or reinterpret captured curl commands inside
that one tool. Status: not yet implemented — first real port happens when a follow-up story needs it.

## Shared vs. specific test

Logic belongs in `src/lib/` if and only if it operates on a domain mechanism: a technical concern that stays the same regardless of which campaign, case, pipeline, or tool is asking for it. Athena
query execution, CSV and report I/O, HAR entry parsing, curl-command parsing, AWS SSO refresh, and config-driven path resolution are all domain mechanisms, so they are shared-library candidates by
definition. Logic stays local to one project's `scripts/` when it encodes campaign- or case-specific business rules: which fields matter for this ticket, what counts as an anomaly for this customer,
how this report should be titled, or which slices of a result set are meaningful for this investigation. The test is not whether another project already has similar code; that is only evidence that a
shared module is overdue. The real test is whether a second, unrelated project could plausibly need the exact same logic to answer a different business question. If yes, write or extract it in
`src/lib/` regardless of which project needs it first.
