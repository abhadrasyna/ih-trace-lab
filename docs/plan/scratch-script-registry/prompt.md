# Scratch script registry — prompt

> Give `scratch/` a searchable script registry, a manual promotion CLI, and a sub-agent-delegated duplicate-check, wired into `session-close`.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in `stories.md` (same
task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`scratch/SCRATCH.md` already documents the convergence rule (probe → promote to `scripts/dev/` or `src/` after 2–3 repeats) but has no *registry* — there is no single file listing what already exists
in `scratch/`, so a new session has no fast way to check "has someone already probed this Lightstep/Athena question?" before writing another near-duplicate scratch script. `/Users/abhadra/
github_copilot` solved the equivalent problem for its `scripts/` folders with a generator (`scripts/generate_scripts_registry.py` → root `SCRIPTS.md`), but that workspace is reference-only now —
`ih-trace-lab` is meant to replace it, not import from it, so this story builds an adapted, `ih-trace-lab`-native equivalent rather than copying that script.

Three gaps get closed together because they share one artifact (the registry) and one workflow (session-close): (1) no registry exists at all — root `SCRIPTS.md` is currently empty; (2) promotion from
`scratch/` to `scripts/dev/` is currently a purely manual `git mv` with no tooling and no registry update; (3) nothing instructs a session to delegate the "check for an existing script before writing
a new one" step to a sub-agent, so that check is easy to skip under time pressure.

## Scope guard

**In scope:** a registry generator scanning `scripts/` and `scratch/`, a manual (not automatically triggered) promotion CLI, an update to `scratch/SCRATCH.md` documenting the sub-agent-delegated
duplicate-check protocol, a one-line `AGENTS.md` pointer, and a new `session-close` step that regenerates the registry. Docs + tooling only — no runtime behaviour of any existing system changes.

**Out of scope:** `/Users/abhadra/github_copilot` (reference-only, no changes there — see `AGENTS.md`'s existing rule against touching it), automatic/scheduled promotion (promotion cadence is manual,
run at the operator's discretion), and any change to the convergence rule itself in `SCRATCH.md` (this story adds a registry + delegation section alongside it, it does not rewrite it).

## Session-start load hints

- `scratch/SCRATCH.md` — the existing convergence rule this story adds a registry and delegation section to; read in full before editing it.
- `.github/skills/session-close/SKILL.md` — the existing skill this story adds a step to; read Step 4b–4c to match its existing style (file-write procedure, idempotent re-run) before adding a new
  step.
- `scripts/dev/reflow_md.py` and `scripts/dev/hooks/check_md_line_length.py` — this project's existing precedent for an untested `scripts/dev/` tool. This story deviates from that precedent
  deliberately (adds tests) per `AGENTS.md` Step 4's hard requirement — do not use the untested precedent as a reason to skip SSR-4's tests.

## Task overview

- **SSR-1** — `scripts/dev/generate_scripts_registry.py`: scans `scripts/` and `scratch/`, writes root `SCRIPTS.md` with a "Scripts" section and a "Scratch" section (scratch rows show the
  filename-embedded date).
- **SSR-2** — `scripts/dev/promote_scratch_scripts.py`: `--list [--days N]` shows promotion candidates by age; `--script <path>` git-moves one scratch script into `scripts/dev/` and re-runs SSR-1's
  generator. Manual only — no scheduled trigger.
- **SSR-3** — `scratch/SCRATCH.md`: add a "Registry & duplicate-check" section documenting the sub-agent-delegated check-and-create workflow and the registry/promote commands.
- **SSR-4** — Tests for SSR-1 and SSR-2 (registry generation, promotion CLI).
- **SSR-5** — `AGENTS.md`: one-line pointer to the new `SCRATCH.md` section (existing "No throwaway code in production folders" paragraph).
- **SSR-6** — `.github/skills/session-close/SKILL.md`: new step regenerating `SCRIPTS.md` when scratch/scripts files changed this session.
- **SSR-7** — Run the generator once to populate root `SCRIPTS.md`, commit the populated file.

## Definition of done

- Root `SCRIPTS.md` lists every current `scripts/` and `scratch/` script, regenerable by a single command, and is populated (not empty) after this story closes.
- `scripts/dev/promote_scratch_scripts.py --list` shows age-based candidates without moving anything; `--script <path>` moves one file and leaves the registry in sync.
- `scratch/SCRATCH.md` documents, as a hard requirement, that a sub-agent checks the registry before a new scratch script is created.
- `session-close` regenerates `SCRIPTS.md` as one of its steps.
- `AGENTS.md` gained exactly one new pointer line; no registry mechanics duplicated there.
- Tests for both new scripts are green.

## Perspectives not covered

- Whether the registry should also flag *near-duplicate* scratch scripts by content similarity (not just by name/topic) — this story only gives the sub-agent a list to read against, it does not build
  any similarity/search tooling. If duplicate scratch scripts keep slipping through despite the delegated check, that is a signal for a follow-up story, not something this one solves.
