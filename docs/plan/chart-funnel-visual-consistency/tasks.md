# DRM funnel chart visual consistency — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: MV-2, MV-3, MV-4, MV-5, MV-6.**

- [x] **MV-1** — decision record: resolve mockup-vs-guide conflicts and settle theme/token additions | Owner: Copilot CLI + user | Model: claude-sonnet-5.5 | Review: user | SHA: 413cfcf
- [ ] **MV-2** — shared DRM-type order, display labels and colour mapping used by every funnel chart | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —
- [ ] **MV-3** — `drm_split`: muted `none` bar, no single-series legend, tiny bars stay visible | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —
- [ ] **MV-4** — `license_outcome`: share-of-DRM-type mode, three semantic series, legend outside the plot | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —
- [ ] **MV-5** — `stages`: funnel prototype in `scratch/`, no clipped labels, colour by meaning, step conversion, error-rate header | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review:
  code-review | SHA: —
- [ ] **MV-6** — align `error_codes` and `3016_subcategory`, regenerate ZA/GH/ZM, update the guide | Owner: Copilot CLI + user | Model: claude-sonnet-5.5 | Review: user | SHA: —

## Story done when

- **MV-1** — the guide records which mockup traits are adopted, adapted or rejected, with the reason for each.
- **MV-2** — one function owns DRM-type order, labels and colours; no funnel chart orders or names types on its own.
- **MV-3** — `none` is muted, no legend appears for one series, and the playready bar is visible or labelled.
- **MV-4** — each DRM type's bar sums to 100% with absolute counts shown; series are success, failed, no_request in green, red, muted.
- **MV-5** — no label is clipped at any figure width; stages are coloured by meaning; step conversion and error rate appear on the chart.
- **MV-6** — all five funnel charts for three opcos share one look and the user has reviewed the rendered PNGs.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `docs/plan/TODOS.md` and add one line to your backlog/session-log file. When the whole story is
done, archive it with `scripts/dev/archive_completed_story.py`.
