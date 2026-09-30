# mtn-network-traffic migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## MNT-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read all 13 implementation files under `/Users/abhadra/github_copilot/mtn-network-traffic/scripts/` (incl. `curl_timer/blocks.py`, `curl_timer/curl_timing.py`, `curl_timer/dns_trace.py`,
   `curl_timer/jwt_inspect.py`, `curl_timer/markdown_report.py`, `curl_timer/mtr_probe.py`, `curl_timer/report.py`, `curl_timer/tls_probe.py`, `curl_timer/traceroute.py`, `curl_timer/whois_lookup.py`,
   `generate_timing_report.py`, `inspect_curl_auth.py`, `time_curl_requests.py`).
2. Confirm or refine `spec.md` §3's classification — state the FCT-1 test result explicitly per file.
3. Confirm the network-diagnostics accept-local decision (epic `README.md`) still holds.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(mtn-network-traffic-tool-migration): audit scripts and classify lib vs. business logic`
