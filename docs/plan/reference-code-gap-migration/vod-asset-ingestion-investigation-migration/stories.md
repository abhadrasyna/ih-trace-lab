# vod-asset-ingestion-mapping migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## VAI-1 — audit + per-file classification

**Files to change / create:** none under `src/` yet — this task only produces/confirms a classification table.

**What to implement:**

1. Re-read all 14 source files under `/Users/abhadra/github_copilot/vod-asset-ingestion-mapping/scripts/` (incl. `lib/adi_parser.py`, `lib/har_parser.py`, `lib/id_components.py`,
   `lib/json_response.py`, `lib/lightstep_trace.py`, `lib/opshub_csv.py`, `lib/value_index.py`).
2. Confirm or refine `spec.md` §4's classification — state the FCT-1 test result explicitly per file.
3. Confirm the ADI/XML+asset-identity-mapper accept-local decision (epic `README.md`) still holds — no second real ADI-ingestion project consumer has appeared since the 2026-09-30 audit.
4. Confirm target folder is `investigations/vod-asset-ingestion/` per the GAP-1 category correction, not `experiments/`.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(vod-asset-ingestion-investigation-migration): audit scripts and classify lib vs. business logic`
