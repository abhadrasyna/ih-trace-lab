# Knowledge: SRE Jira Project Reference

## Read this first when

Consult this before writing any JQL against Jira project SRE, or before running or authoring one of the `/sre*` skills.

## Project structure

The SRE Jira project was documented around two work dimensions.

### 1. Daily operational stories

These are anchored by the custom **Report Date** field.

#### Proactive Dashboard Monitoring

- Story summary contains: `Proactive Dashboard Monitoring`
- Work is split across three shifts.
- The source doc records a per-customer expected-effort table for these shifts.
- Skills:
  - `/sremonitoringeffort` — effort totals and variance against target
  - `/sremonitoringcommentanalysis` — shift-comment quality and alert / incident / handover analysis

#### Operational Daily Report & IVPA Health Verification

- Story summary contains: `Operational Daily Report & IVPA Health Verification`
- Skill: `/sredailyreporteffort`

### 2. Q2 2026 epic-driven work

Two epic families were called out:

- `Q2 2026 – Customer Change Support`
- `Q2 2026 – Incident & Problem Triaging`

The triaging side is cross-referenced with project `SDI`. The qualifying SDI filters were:

- `Request Source` = `SNOW Incident` or `SNOW ProblemTask`
- `External Assignment Group` contains one of:
  - `PS-VideoPractice-PE`
  - `VCS-SA - IVP`
  - `APAC - SA`
  - `VCS-GO`

Coverage states for the SDI cross-check are:

- `active`
- `existing-no-activity`
- `missing`

Skill: `/srecustomerschangesupportreport`

## Key Jira fields and conventions

| Field | ID / shape | Notes |
| --- | --- | --- |
| Report Date | `customfield_13204` | Anchors daily stories to a date |
| Epic Link | `customfield_10101` | Story/Bug → Epic linkage |
| Parent Link | Jira parent-link field | Epic → Initiative linkage |
| External Assignment Group | `customfield_10377` | Text field — use `~`, not `=` |
| Request Source | `customfield_10348` | SDI source classification |
| Story Points | `customfield_10106` | Days-based effort values, not Fibonacci |

The documented Story Points convention is **0.125 / 0.25 / 0.5 / 1** day-style effort, not the usual Fibonacci story-point scale.

## Initiative → Epic → Story hierarchy

```text
Initiative
└── Epic
    └── Story / Bug
```

Field mapping:

- `Parent Link` = Epic → Initiative
- `Epic Link` = Story/Bug → Epic

## Quarterly JQL templates

The quarterly prompt is parameterized rather than tied permanently to one quarter. Update the label / epic keys each quarter.

### Initiatives

```jql
project = "Site Reliability Engineering" AND issuetype = Initiative AND labels = "<quarter-label>" AND labels = "ops"
```

### Epics under those initiatives

```jql
issuetype = Epic AND "Parent Link" in (<initiative keys>)
```

### Stories / bugs under epic groups

```jql
issueType in (Story, Bug) AND "Epic Link" in (<epic keys>)
```

The source prompt's Q1-2026 examples are useful templates, but the explicit guidance there is to swap in the current quarter's label and the initiative/epic keys for the cycle being analyzed.

## Skills reference

| Skill | Trigger / use-for |
| --- | --- |
| `sreWorkLog` | Project-wide effort totals by person and issue for a date |
| `sredailyreporteffort` | Effort on Operational Daily Report stories |
| `sremonitoringeffort` | Effort on Proactive Dashboard Monitoring stories |
| `sremonitoringcommentanalysis` | Comment-quality and shift-handover analysis |
| `srecustomerschangesupportreport` | Q2 epic activity plus SDI triaging cross-check |

Shared conventions called out by the source docs:

- default to yesterday when no date is provided;
- accept natural-language dates;
- write to a reports folder by default unless `inline-only` is requested.

## Time-of-writing example gotcha

As of the 2026-06-28 analysis captured in the source doc, SDI → SRE triaging coverage was heavily skewed toward a single assignment group: `VCS-GO` had **7%** coverage in sprint AC26.2.6 and **0%**
coverage in AC26.3.1. Preserve this as an example of the gap the `/srecustomerschangesupportreport` skill is meant to surface, not as a permanent fact to assume without re-checking.

## Out of scope for this harvest

The raw sprint-by-sprint SDI comparison tables, `sre/data/*.csv`, and `sre/reports/*.md` stay in `github_copilot` as dated raw inputs or generated skill-run outputs. They are artifacts, not the stable
reference knowledge this file is meant to preserve.

## Source

Source paths: `/Users/abhadra/github_copilot/sre/docs/sre-jira-knowledge.md` and `/Users/abhadra/github_copilot/sre/docs/SRE_Quarterly_Jira_Query_Prompt.md`. These files are read-only reference, not a
shared codebase.
