# Chart guide and code alignment — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: CA-1, CA-2, CA-3, CA-4.**

- [ ] **CA-1** — shared `draw_title` helper at the guide's 16/10 pt scale, used by bar, signed_line, stacked_bar, pie | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —
- [ ] **CA-2** — apply `format_count` to the value axis of `render_bar` and `render_stacked_bar` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —
- [ ] **CA-3** — align `chart-guidelines.md` and `CONTEXT.md` with the code; drop stale statements | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: —
- [ ] **CA-4** — theme: `amber` status colour, `Tone.WARNING`, five-colour `series`, pie `max_slices` default 5 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: —

## Story done when

- **CA-1** — no chart module contains its own title or subtitle `fig.text` call; titles render at 16 pt bold and subtitles at 10 pt, from one helper.
- **CA-2** — bar and stacked-bar value axes show `2k`, not `2000`; horizontal and vertical orientations both covered.
- **CA-3** — the guide's type scale, module table and `CONTEXT.md` describe what the code does, including the new helper.
- **CA-4** — `amber` exists in `ChartTheme` with a test; no status colour appears in `series`; `Tone.WARNING` renders amber; the pie default and its validation match the five-colour palette.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `docs/plan/TODOS.md` and add one line to your backlog/session-log file. When the whole story is
done, archive it with `scripts/dev/archive_completed_story.py`.
