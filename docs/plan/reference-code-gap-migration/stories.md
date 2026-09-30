# Reference code gap migration — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task.

---

## GAP-1 — decide scope shape + resolve category conflict (done)

> Closed 2026-09-30. Decisions recorded in `README.md` §"GAP-1 decisions". This spec is kept as the historical record of what was asked; do not re-run it.

**Files to change / create:**
- Either this story's own `tasks.md` (if kept flat — add per-project task ids), or a new `docs/plan/reference-code-gap-migration/README.md` + per-project sub-story folders (if promoted to an epic,
  mirroring `docs/plan/pipeline-migration/`'s exact file set: epic `prompt.md` + `README.md` router at the root, no epic-level `tasks.md`, one sub-story folder per project with its own
  `prompt.md`/`tasks.md`/`stories.md`).
- `docs/plan/project-taxonomy/structure.md` — only if the category-conflict resolution is "flag a correction", in which case update the `vod-asset-ingestion-mapping` worked example there (coordinate
  with that story owner; do not silently move it out of `experiments/` without a documented reason readable in this task's own commit).

**What to implement:**

1. Read `spec.md`'s full audit before deciding anything.
2. **Scope-shape decision.** Considerations to weigh explicitly, not just gut-call:
   - `pipeline-migration`'s epic shape (one epic, N stories, shared blocking-dependency list) fits when stories share dependencies. These 10 projects don't share as clean a dependency set — some
     (`applauseInvestigation`, `astro-events-household-report`) are near-zero-effort once `src-lib-migration` lands; others (`vod-playback-timing-probe`, `mtn-zm-session-device-investigation`) need
     net-new modules first.
   - A plausible split: land the cheap, fully-lib-absorbable projects as their own small stories first (no new module blocking them), defer the two large/novel-module projects to stories that
     explicitly block on a decision about promoting a new `src/lib/*` module.
   - Record the decision and its reasoning in whichever file ends up being this story's index (`tasks.md` if flat, `README.md` if promoted to an epic).
3. **Category-conflict resolution.** `project-taxonomy/structure.md` already worked-examples `vod-asset-ingestion-mapping` under `experiments/`. `spec.md`'s audit — and that project's own README,
   which calls it "a continuous data-gathering exercise" — reads as a recurring-campaign *investigation*, not a one-off experiment. Pick one of:
   - **Accept `structure.md` as-is**, with a one-paragraph documented reason readable by a future session (e.g. "experiment because X, despite the recurring cadence, because Y").
   - **Flag a correction**: update `structure.md`'s worked example and note the change in `project-taxonomy`'s own story files (do not silently drift the two docs apart — `structure.md`'s own
     Invariant section requires this). Do not leave this unresolved — a later per-project task cannot pick a target folder until this is settled.
4. **New-module promotion decision.** For each of `spec.md`'s "suggests a genuinely new shared module" candidates (`mpd`/DASH parser, playback-session/timing correlator, network-diagnostics,
   ADI/XML+asset-identity mapper, device/user-agent identity, crypto/JWS signing), record either "promote to `src/lib/<name>/`, blocks project X's story" or "accept as project-local duplication,
   revisit if a third project needs it" — per `functional-code-taxonomy` FCT-1's own "shared vs. specific" test, not a new ad hoc rule.
5. Write per-project task ids (one per remaining gap project) into whichever file is this story's new working list, each citing: target category + folder (from step 3's resolution or `structure.md`'s
   existing examples), which `src/lib/*` modules it consumes (existing or newly-promoted per step 4), and which files stay local business logic — mirroring `pipeline-migration`'s own per-file
   lib-vs-script citation discipline (see its README's "Cross-cutting constraints").

**Tests:** none — planning/docs-only task.

**Commit:** `docs(reference-code-gap-migration): decide scope shape and resolve category conflict`
