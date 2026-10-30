# Incident summaries

Case-scoped summaries of incident investigations done in team chat/meetings (Microsoft Teams Copilot), kept here so a new incident can be compared against past ones. One file per incident:
`YYYY-MM-DD_<ticket>_<slug>.md` (date = day the summary was written). Use `_TEMPLATE.md` for the headings. Fill gaps from the ticket; never infer — leave "Not stated".

## Prompt for Teams Copilot

Replace the bracketed fields, then paste:

```
Summarise the investigation in this chat thread/meeting about [incident title / ticket ID], raised on [date].
Use only what is stated in the thread or transcripts. If something isn't stated, write "Not stated" instead of inferring. Output as Markdown with these headings:

1. Incident: ID, raised date, reporter, affected tenant/OpCo, platform/device/app version, severity, current status.
2. Symptom & impact: what users saw, error codes or messages (exact text), start/end time (with timezone), scope (how many users/devices/sessions).
3. Timeline: chronological bullets as "YYYY-MM-DD HH:MM TZ - who - what was done or found".
4. Hypotheses: each as hypothesis, evidence for, evidence against, final status (confirmed / rejected / open).
5. Evidence & queries: every tool or data source used (Lightstep, Athena, Conviva, logs, etc.), with exact query text, filters, time windows, and the result of each.
Quote IDs (sessionId, householdId, deviceId, trace IDs) verbatim.
6. Root cause: confirmed cause, or "Not confirmed" with the best current theory and confidence.
7. Fix / workaround: what was changed, by whom, when, and whether it was verified.
8. Open questions & next steps: owner and due date for each item.
9. Links: tickets, PRs, dashboards, docs, and files shared in the thread.
10. Lessons for future incidents: signals that would let us recognise this faster, and checks to run first.

Keep it factual and under 600 words, excluding the queries section.
Do not include chit-chat.
```

## Index

| Date | Ticket | Summary | Root cause |
|------|--------|---------|------------|
| 2026-10-30 | INC0256822 | [VOD series not searchable in MTN-1 Ghana/Zambia](2026-10-30_INC0256822_search-vod-not-found.md) | Not confirmed (incremental Search update never started) |
