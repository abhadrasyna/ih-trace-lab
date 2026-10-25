# Chart guide and code alignment — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation
spec.

**Open: none — all four tasks done (2026-10-25).**

- [x] **CA-1** — shared `draw_title` helper at 16/10 pt, used by every chart module | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: b0bada7
- [x] **CA-2** — apply `format_count` to the value axis of `render_bar` and `render_stacked_bar` | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: de913aa
- [x] **CA-3** — align `chart-guidelines.md` and `CONTEXT.md` with the code; drop stale statements | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: none | SHA: d4d060f
- [x] **CA-4** — theme: `amber` status colour, `Tone.WARNING`, five-colour `series`, pie `max_slices` default 5 | Owner: Copilot CLI | Model: claude-sonnet-5.5 | Review: code-review | SHA: 2c890f5

## Story done when

- **CA-1** — no chart module contains its own title or subtitle `fig.text` call; titles render at 16 pt bold and subtitles at 10 pt, from one helper.
- **CA-2** — bar and stacked-bar value axes show `2k`, not `2000`; horizontal and vertical orientations both covered.
- **CA-3** — the guide's type scale, module table and `CONTEXT.md` describe what the code does, including the new helper.
- **CA-4** — `amber` exists in `ChartTheme` with a test; no status colour appears in `series`; `Tone.WARNING` renders amber; the pie default and its validation match the five-colour palette.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in `docs/plan/TODOS.md` and add one line to your backlog/session-log file. When the whole story is
done, archive it with `scripts/dev/archive_completed_story.py`.
