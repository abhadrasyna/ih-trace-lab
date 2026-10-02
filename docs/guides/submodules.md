# Git submodules

This project vendors in already-independent sibling deliverables as pinned git submodules rather than re-porting their logic a second time. See
`docs/plan/src-lib-migration/athena-lib-integration/prompt.md` for the rationale behind each one.

## `vendor/athena-mcp-server`

- **What it provides:** `/Users/abhadra/myWork/myOffice/athena-mcp-server`'s `src/athena_runner/*` — the shared Athena start/poll/download execution stack (`config`, `aws_clients`, `query_executor`,
  `result_downloader`, `sso_auth`, `sso_profiles`, `tenants`, `logging_setup`, `date_utils`, `exceptions`). `src/lib/athena/adapter.py` (this project) delegates to it rather than reimplementing it.
- **Pinned commit:** see `.gitmodules` / `git -C vendor/athena-mcp-server rev-parse HEAD` — pinned explicitly, never tracking a floating branch.
- **Known open item inherited from that repo:** `src/athena_mcp/tool_config.py::_load_mtn_registry` mounts `aws-access-cli`'s `queries/` directory as a sibling-checkout namespace-package merge
  (`../aws-access-cli/scripts/athena_runner/queries`). This is fragile but **not this project's problem to fix** — `src/lib/athena/adapter.py` only depends on the generic `athena_runner` package,
  never on `tool_config.py`, precisely to avoid inheriting that fragility.

### Setup

```sh
git submodule update --init --recursive
```

(or clone this repo with `git clone --recurse-submodules`).

### Updating the pin

```sh
cd vendor/athena-mcp-server
git fetch origin
git checkout <new-commit-sha>
cd ../..
git add vendor/athena-mcp-server
git commit -m "chore(athena): bump athena-mcp-server submodule pin to <new-commit-sha>"
```

Out of scope for any `ih-trace-lab` story: making changes *inside* the submodule itself. It is a separate repo with its own `AGENTS.md`/test suite/commit history — treat it as externally owned.
