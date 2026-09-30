# smarttv-mtntv migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## SMT-1 — audit + classification confirmation (audit-only, blocked on `src/lib/crypto_signing/`)

**Files to change / create:** none under `src/` yet — this task only confirms classification/blocking status. Do not begin any actual port — `src/lib/crypto_signing/` does not exist yet.

**What to implement:**

1. Re-read `/Users/abhadra/github_copilot/smarttv-mtntv/scripts/signedJson.py` and compare against root `/Users/abhadra/github_copilot/investigations/scripts/sign_jws_json.py` — confirm both implement
   the same JWS/JSON-signing mechanism (per epic `README.md`'s promotion reasoning), not just a superficial "signs JSON" naming coincidence.
2. Check `docs/plan/src-lib-migration/README.md` for whether `src/lib/crypto_signing/` has been added to that epic's module list yet; if not, state that the actual port cannot start until it is.

**Tests:** none — audit/docs-only task.

**Commit:** `docs(smarttv-mtntv-tool-migration): confirm classification and crypto_signing blocking status`
