# Analysis and storytelling framework (reference)

Reference notes for turning the September adoption CSVs (session, household, gap-analysis session) and later the error-code counts into one decision-oriented story. This is analysis guidance only; no
script depends on it. Sources are marked as read in full, or taken from a search summary only (verify before quoting).

## Source learnings

### Effective Data Storytelling, "Five excellent data storytelling examples" (read in full)

Business data stories differ from data journalism: they must drive a decision, target specific stakeholders, use everyday tools, guide the audience to one main takeaway, usually run as a live
presentation, and end with a clear recommendation and path forward. Techniques across the five examples (Rosling, Halloran, Vox on South Korean height, Vox on COVID vaccine attitudes, The Pudding on
pockets):

- Say the story in one sentence first.
- Define the unit of measure before showing any numbers (Halloran).
- Change the lens so the outlier appears: Vox switched from absolute height to growth, and South Korea became the visible outlier. State plainly when a first view shows no pattern.
- Reveal a key number progressively and give it one memorable moment (the Soviet bar that keeps rising; the phone-over-the-chart reveal).
- Annotate the figure that carries the stakes (the missed "15x" annotation in the Vox vaccine story) and never leave axes or labels mislabeled, because small errors erode trust.
- Reframe the same data through different groupings, then contextualise against other cases.
- Anticipate the obvious counterargument and control for it (The Pudding fixed waist size at 32 inches); put methodology at the end for those who want to verify.
- Put important context early, not at the end, and keep any interactivity anchored to the narrative.
- Hierarchy matters: distinguish primary labels from secondary ones.

### Duarte, "The Duarte Guide to Data Storytelling" (read about the first half)

- A data story identifies a trend, reveals an opportunity or risk, and recommends an action, in three acts: beginning (stakes), middle (problem or opportunity), end (course of action).
- Big Idea = Point of View + Stakes, written as one complete sentence containing a verb. A DataPOV frames the data from one audience's perspective.
- Examples use a "But/And" hinge in act two, e.g. "2x the traffic, but 74% abandoned their carts, so changing the cart experience could raise sales by 40%".
- Ask about the audience first: motivations, relationship to the data, biases, what is at risk, what they gain by acting.
- Visual rules: choose the chart type for the point (bars for comparison, lines for trend); emphasise the key bar with a contrasting colour and grey the rest; make the slide title the data
  observation; the audience should get the takeaway at a glance (the "glance test").

### Storytelling with Data, "The structures of story" (read in full)

You rarely need to tell the full story with every peak. Know all the peaks, then choose and weave the combination that suits the audience (an executive wants the high-level arc or pyramid; other
partners care about other peaks).

### From search summaries only (not read in full; the issue-tree page returned 403)

- Narrative arc: exposition, inciting incident, rising action, climax, falling action, resolution.
- Minto pyramid / SCQA: answer first, then supporting arguments, then data; Situation, Complication, Question, Answer.
- Funnel views (step funnel, segmented funnel, annotated drop-off points); time-series views (annotated line, heatmap, control chart); small multiples for side-by-side comparison.
- Analysis methods: issue trees (MECE branches), hypothesis-driven analysis, segmentation, Simpson's paradox checks, Pareto 80/20.

## Applying it to the September CSVs

All comparisons are within a single day. Units: a session is a `parent_session_id`; a household is a `user_id`; an attempt is a session with `REQUEST_VIEWING`. Define these once, first.

- **Big Idea (Duarte: POV + stakes):** one sentence per story, e.g. "N of every 100 playback attempts succeed; the rest fail in identifiable ways, broadly or in a few households, and each needs a
  different fix."
- **Funnel (normalise, as the Vox growth lens):** express every outcome per 100 attempts per OpCo: success, VSF, EBVS, incomplete, play-stage error, timeout. Counts hide the outlier because OpCos
  differ in size.
- **Trend and outlier days (small multiples, annotation):** one identical daily success-rate chart per OpCo; grey for normal days, one colour for anomalies; annotate the worst days and show attempt
  volume so thin days are not over-read.
- **Broad or concentrated (issue tree, Pareto):** per day, affected-household share against sessions per affected household. High share with a ratio near 1 is broad; low share with a high ratio is a
  few households.
- **Trust (anticipate the counterargument):** this is the central chart, because the gap CSV exists to explain the unknown drop-off (attempts not equal to success + VSF + EBVS). Show attempts against
  the stacked buckets per OpCo, put `incomplete_no_destroy` in a different colour from the failure buckets and label it "playback started, no end event reported", and show the leftover
  (`attempts_sum_check`) explicitly.
- **Close (Minto, three acts):** beginning is the funnel and stakes; middle ("But") is the bad days and whether they are broad or concentrated; end is a recommendation per pattern, handing off to the
  error-code breakdown.

Definition notes carried from the analysis of the existing reports:
- `unique-hh-no-vsf` always equals attempting households minus VSF households, so use the subtraction.
- The VSF household set is a subset of the attempting household set; the household CSV is a cross-check of the session CSV, not an independent funnel.
- A manual check (ZA, 2026-09-15, 309 attempts) found one playback outcome per session and buckets summing to attempts; MEC-5 repeats that check for all OpCos.
- Do not sum the daily household columns to quote a single September household figure.
- `incomplete_no_destroy_sessions` means playback started but no `DESTROY` was reported (for example a viewer killing the app on mobile), not "no `PLAY`". Treat it as a reporting gap or silent exit,
  not as a failure, and use `Successful-VOD-Playback-Sessions` plus this bucket only as an upper bound of sessions that actually played (a hypothesis until confirmed on data).
- Open question: VSF may overlap `incomplete_no_destroy`, in which case the six-column sum can exceed attempts; confirm against the reference gap CSV's `attempts_sum_check`.
