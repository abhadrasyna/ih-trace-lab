# Shared libs `mpd` and `crypto_signing` — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`. After each task: set `SHA:` on the task line + tick the box,
> update the story status summary, add one line to your backlog/session-log file.

---

## SLM-1 — Audit and API design

**Files to change / create:**
- `docs/plan/shared-lib-mpd-crypto-signing/api.md` — public API for both modules (an extra `.md` with no task checkboxes).

**What to implement:**

1. Read the four originals named in `prompt.md`; list what each consumer actually calls.
2. For `mpd`: define the typed result (periods, adaptation sets, representations, segment info), the entry functions and `MpdError`.
3. For `crypto_signing`: define sign/verify functions over JSON payloads, how a key is passed in (never read from disk or env inside the lib), and `SigningError`.
4. Note any secrets or hardcoded keys found in the originals; they must not be copied.

**Tests:** none (docs only).

**Commit:** `docs(plan): record mpd and crypto_signing API`

---

## SLM-2 — Build `src/lib/mpd/`

**Files to change / create:**
- `src/lib/mpd/__init__.py`, `errors.py`, `parser.py` (plus `models.py` if the API calls for it) — one-way dependencies, no I/O in the parser.
- `tests/lib/mpd/__init__.py`, `test_parser.py` and small fixture MPDs under `tests/lib/mpd/fixtures/`.

**What to implement:**

1. Port the parsing logic from `playback_probe/mpd_parser.py` behind the SLM-1 API, taking MPD text and returning typed results.
2. Wrap XML and parsing exceptions as `MpdError`; type hints on all public functions.

**Tests (no network):**
- `test_parse_static_mpd` — a fixture MPD yields the expected periods and representations.
- `test_parse_invalid_xml_raises_mpd_error` — malformed input raises `MpdError`, nothing else.

**Commit:** `feat(mpd): add shared DASH MPD parser`

---

## SLM-3 — Build `src/lib/crypto_signing/`

**Files to change / create:**
- `src/lib/crypto_signing/__init__.py`, `errors.py`, `jws.py` — key passed in by the caller.
- `tests/lib/crypto_signing/__init__.py`, `test_jws.py`.

**What to implement:**

1. Port the signing logic from `signedJson.py` and `sign_jws_json.py` behind the SLM-1 API.
2. Wrap library exceptions as `SigningError`; no key or secret is ever logged.

**Tests (no network, generated throwaway keys only):**
- `test_sign_then_verify_round_trip` — a signed payload verifies and decodes to the original JSON.
- `test_verify_tampered_payload_raises_signing_error` — a modified token raises `SigningError`.

**Commit:** `feat(crypto_signing): add shared JWS signing`

---

## SLM-4 — Docs and unblock

**Files to change / create:**
- `docs/guides/functional-code-taxonomy.md` — add the two modules and their status.
- Code registry (regenerate with the existing generator), `CONTEXT.md` "What Exists".
- `docs/plan/reference-code-gap-migration/README.md` — mark the two Tier 3 stories unblocked.

**What to implement:**

1. Add both modules to the taxonomy guide and regenerate the registry.
2. Update the epic's story table and blocking notes.

**Tests:** none (docs only); run the docs-plan pre-commit hooks.

**Commit:** `docs(lib): register mpd and crypto_signing modules`
