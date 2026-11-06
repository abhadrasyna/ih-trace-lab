# Skill analysis and takeaways

Read-only evaluations of external skills, repos and documents against two needs: (A) this repo's agent workflow (AGENTS.md, `.github/skills/*`, hooks, `docs/plan/`) and (B) the unified dashboard in
`docs/analysis/2026-11-04_unified-dashboard/`. One numbered section per source below; the Verdicts table is the quick index. Evidence rule: a gap counts only if our own history shows a past failure
(A) or it blocks a named dashboard phase or gate (B). There is no frontend code in the repo yet, so for (B) the local counterpart is the dashboard plan and `docs/guides/chart-guidelines.md`.

## 1. Verdicts

| # | Source | Scope | Verdict |
|---|---|---|---|
| 1 | `nextlevelbuilder/ui-ux-pro-max-skill` (v2.15.0), evaluated 2026-11-05 | A+B | Do not install. Borrow three ideas for dashboard phase 2; skip the rest. |

## 2. nextlevelbuilder/ui-ux-pro-max-skill

### What was worth noting

The repo is mature as a project: created 2025-11-30, about 145k stars, 15k forks, 30 contributors, MIT licence, last push the day of this review, CI that runs tests, and data files carrying provenance
and verification dates. Stars are not evidence that it fits us. It is an AI skill that gives UI/UX recommendations from local CSV data (80 styles, 192 product types with colour and reasoning rules, 74
font pairings, 119 UX guidelines, 25 chart types, 22 stack rule sets) through a stdlib-only Python BM25 search script. The scripts make no network calls and run no subprocesses (checked by grep for
`urllib`, `requests`, `subprocess`, `socket`); the only file writes are the optional `--persist` output under `design-system/<slug>/`. The same plugin also ships five more skills (`ui-styling`,
`brand`, `design`, `design-system`, `slides`, `banner-design`), dozens of bundled TTF fonts and a `shadcn_add.py` wrapper around `npx shadcn@<version> add`.

The data is aimed at marketing and consumer UI. Its 192 product types are things like spas, restaurants and fintech apps, and its default output is a landing-page pattern, a style name and a palette.
Our dashboard is an internal exec and SRE tool with a decided direction (dark-first, one accent colour, 3-4 chart types, shadcn/ui, ECharts), so the style, palette and font engine has no decision left
to make for us. The README itself says the brand, logo and slide skills are a Premium tier while the repo contains them; I did not resolve that mismatch.

### Why not install wholesale

Installing the plugin loads the frontmatter of every bundled skill into always-loaded context, and the `ui-ux-pro-max` and `ui-styling` descriptions alone are several hundred characters each; I did
not measure the total. The 16.6 KB `SKILL.md` body loads whenever a UI task triggers it. Its flow says a design system is "REQUIRED for new pages/projects", which would put a generator in front of the
phase 1 and phase 2 artifacts that our dashboard plan deliberately writes by hand, each ending in a review gate. `--persist` creates `design-system/<slug>/MASTER.md` outside `docs/analysis/` and
`docs/plan/`, which our taxonomy guide does not provide for, so every run would need a new folder decision. It gives us no dashboard-specific chart or data-freshness guidance beyond a generic table.

### Covered vs gap

| Area | What we already have | What the source adds | Real gap? |
|---|---|---|---|
| Chart type choice | Chart guide "Choosing a chart type" (matplotlib, dark only, direct labels) | `charts.csv`: 25 types, "when not to use" | No; its web libraries are not our ECharts |
| Colour-only meaning | Green/red carry sign; plan has RAG status KPIs | `color-not-only`, chart "A11y fallback" (data table) | Yes: grep finds no a11y or colour-blind wording (see below) |
| Tile states | Plan: "last updated" badge; rate-limit and Athena-cache risks | `empty-data-state`, `loading-chart`, stale/error | Yes: no empty, error, stale or partial tile state |
| Design tokens | Plan phase 2 token file; `ChartTheme` in `src/lib/charts` | Master plus per-page overrides layout | Small: a file layout idea only |
| Next.js and shadcn rules | None in repo (no frontend code yet) | 60 and 68 severity-tagged rows, docs URLs | Not yet; model already knows the stack |
| Agent safety posture | AGENTS.md protocol; `no-row-level-ids-in-head-output` seen 5 times | "No private data in queries or persisted output" | No: local rule already exists |

The grep behind the colour-only row covered AGENTS.md, PYTHON_DESIGN.md, `docs/guides` and `docs/refactor` for accessibility, contrast, colour-blind and WCAG terms.

### Verdicts per candidate

1. Whole plugin / core `ui-ux-pro-max` skill [B]: **skip**. Covered: our dashboard decisions already fix style, stack and chart count. Missing: nothing it can decide for us. Evidence: none; the plan
   has no open style question. Token cost: grows always-loaded context (seven skill descriptions) and loads a 16.6 KB body on trigger. Protocol conflict: its "REQUIRED" generator and `--persist`
   folder bypass our plan-then-go-ahead and review-gate flow, and `legend-visible` contradicts our direct-labels rule. Data-safety: low, scripts are offline, but its marketing-oriented defaults could
   put a consumer palette in front of execs.
2. `ui-styling`, `brand`, `design`, `slides`, `banner-design`, bundled fonts, `shadcn_add.py` [B]: **skip**. Covered: `npx shadcn@latest add` can be run directly under approval; brand and slide work
   is out of scope. Evidence: none. Token cost: more always-loaded descriptions, plus the font files in the checkout. Not read: the `design`, `brand`, `slides` and `banner-design` bodies.
3. Chart accessibility and tile-state rules from `charts.csv` and `references/quick-reference.md` section 10 [B]: **borrow the idea only**. Covered: chart choice. Missing: a rule that status never
   relies on colour alone (RAG tiles need an icon or text label too), a visible data-table alternative per chart, and explicit empty, loading, stale, error and partial-data states per tile. Evidence:
   the plan's own RAG KPI row and its stated Lightstep rate-limit and Athena-cache risks; a stale or failed connector rendering as a healthy number is the exec-view way to misstate a metric. Cost:
   zero, it goes into `03-design-tokens.md` at phase 2, not into always-loaded files. Conflict: take the colour rule, reject `legend-visible` so direct labels still win. Data-safety: improves it.
4. `nextjs.csv` and `shadcn.csv` stack rows [B]: **skip**. Covered by model knowledge and the shadcn and Next.js docs. Evidence: no blocked gate. Revisit at the clickable-prototype step (phase 2) and
   read single rows on demand with `gh api`, no install.
5. Master plus per-page overrides pattern [A+B]: **borrow the idea only**. Use it as the layout of the phase 2 token file (global tokens, optional per-view overrides) and keep its rule to read an
   existing master before regenerating and never overwrite without approval, which our protocol already requires. No new script, no `design-system/` folder.
6. Skill-authoring habits (short `SKILL.md`, long reference loaded on demand, "retry once then say no match was found", "do not persist unverified output") [A]: **borrow the idea only**, weak. Our
   `session-close` skill is 271 lines, but `suggestions.md` records no incident traced to skill size, so no edit now.

## 3. Resume plan

1. At dashboard phase 2, when writing `03-design-tokens.md`: add (a) status colour is always paired with an icon or text label, (b) a data-table alternative per chart type, (c) a per-tile state set of
   loading, empty, stale, error and partial with the "last updated" badge, (d) global tokens plus optional per-view overrides. Gate: look-and-feel review.
2. Keep `ui-ux-pro-max-skill` uninstalled; make no edits to AGENTS.md, `.github/skills/*`, CONTEXT.md or `docs/guides/chart-guidelines.md` for this source.
3. If the phase 2 prototype stalls on Next.js or shadcn specifics, read the relevant `nextjs.csv` or `shadcn.csv` rows on demand through `gh api`; do not install.
4. Re-evaluate only if the dashboard moves to a stack the model handles poorly or a UI defect is traced to a missing guideline.

## Scope note

Read in full: the first 14 KB and the middle 16 KB of the README (the tail was not read), `plugin.json`, `marketplace.json`, `.claude/skills/ui-ux-pro-max/SKILL.md` and `stack/.claude/settings.json`.
Read partially: `references/pro-rules.md` (first 7 KB), `data/charts.csv` (all 25 rows, columns sampled), `references/quick-reference.md` (matches for chart, table and status terms only), root
`CLAUDE.md` (first 3.5 KB) and `ui-styling/SKILL.md` (first 3.5 KB). Sampled: the first rows of `nextjs.csv` and `shadcn.csv`, and the `ux-guidelines.csv` rows matching chart, table, loading and empty
terms. Checked by grep only: `search.py`, `core.py`, `design_system.py`, `reasoning_contract.py` (network, subprocess and file-write calls) and `shadcn_add.py` (subprocess use). Not read: `cli/src/*`
(what `uipro init` downloads and writes), the `design`, `brand`, `slides`, `banner-design` and `design-system` skills, `ui-reasoning.csv`, `styles.csv`, `motion.csv`, the CI workflows, tests and every
other stack CSV. Locally read: the dashboard README, `docs/analysis/README.md`, `docs/guides/chart-guidelines.md` (anchors and key sections), `suggestions.md`, hook configs and file sizes. Not read
locally: `.github/skills/*` bodies, `AUTOMATION.md` and `session_audit.jsonl` beyond line counts (AGENTS.md was only available as loaded instructions and a grep). Next to read:
`cli/src/utils/github.ts` and `init.ts`, then the `ui-reasoning.csv` rows for dashboards.
