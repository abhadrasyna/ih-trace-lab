# smarttv-mtntv migration — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: SMT-1.**

- [ ] **SMT-1** — Audit `smarttv-mtntv/scripts/signedJson.py` and confirm classification/blocking status (audit-only, blocked on `src/lib/crypto_signing/` for any actual port) | Owner: AI agent |
  Model: n/a | Review: human read-through | SHA: <—>

## Story done when

- **SMT-1** — `signedJson.py`'s classification is confirmed against `spec.md` §10 and its shared-mechanism relationship with `sign_jws_json.py` (root `investigations/`) is documented; blocking status
  on `src/lib/crypto_signing/` is stated explicitly.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story table and add one line to your backlog/session-log file. When the
whole story is done, archive it per this project's convention — do not leave a done story half-archived.
