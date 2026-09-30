---
name: investigation-doc-sync
description: Sync case-scoped findings from prior Copilot sessions into investigation docs with a cursor, dated sections, and a regenerated provenance table.
---

# Investigation doc sync

> Use this skill only for a specific case or campaign. It is the case-doc counterpart to `session-close`: instead of auditing one bounded session, it gathers case-specific evidence across many
> sessions and appends it into the real investigation deliverables under `investigations/`.

## Trigger phrases

- `investigation checkpoint <case-id>`
- `investigation checkpoint <campaign-slug>`
- `investigation summary <case-id>`

The checkpoint form appends dated findings into the detailed case doc. The summary form rewrites or refreshes the separate executive summary after the detailed doc already contains multiple dated
sections.

## Ground rules

1. This skill is case-scoped or campaign-scoped, never whole-session-scoped.
2. The cursor lives in the deliverable, not the transcript.
3. Extraction is content-filtered: include only rows that reference the case ID, campaign slug, or resolved investigation/data paths.
4. The detailed doc and executive summary are separate outputs.
5. The session-provenance table is regenerated on every sync; it is never maintained by hand.

## Target files and cursor

The detailed deliverable is the case doc named by `docs/plan/project-taxonomy/structure.md`'s `investigations/` block, for example `investigations/<campaign-slug>/docs/<case-id>-<topic>.md` or
`investigations/<case-id>/docs/<case-id>-<topic>.md`.

The cursor is a marker comment at the top of that detailed doc:

```md
<!-- last-synced: 2026-09-14T10:22:00Z -->
```

Read the timestamp before querying history. After a successful checkpoint sync, rewrite it to the newest synced timestamp. Never store the cursor in the transcript or in a sidecar state file.

## Step 1 — Resolve the target paths

1. Read `config/data_paths.yaml` and resolve the real investigation paths using the templates defined by PT-7. This skill populates those paths; it does not redefine them.
2. Confirm the doc shape from `docs/plan/project-taxonomy/structure.md`'s `investigations/` block.
3. Preserve PT-7's mandatory **Inputs used** block in the detailed doc. Update it only when the matched evidence changes what was used or what was saved.

## Step 2 — Extract only new, case-scoped evidence

Query `session_store_sql` for rows newer than the cursor whose text or paths mention the case or campaign. Prefer local history first, because the point is to assemble work already done in this repo.
Use case-id/path matching, not whole-session classification.

Illustrative extraction pattern:

```sql
WITH matched_turns AS (
  SELECT session_id, timestamp AS event_time, 'turn' AS source, user_message AS detail, assistant_response AS evidence
  FROM turns
  WHERE timestamp > :cursor
    AND (
      COALESCE(user_message, '') LIKE '%' || :case_id || '%'
      OR COALESCE(assistant_response, '') LIKE '%' || :case_id || '%'
      OR COALESCE(user_message, '') LIKE '%' || :campaign_slug || '%'
      OR COALESCE(assistant_response, '') LIKE '%' || :campaign_slug || '%'
    )
),
matched_files AS (
  SELECT session_id, first_seen_at AS event_time, 'file' AS source, file_path AS detail, file_path AS evidence
  FROM session_files
  WHERE first_seen_at > :cursor
    AND (
      file_path LIKE '%' || :case_id || '%'
      OR file_path LIKE '%' || :campaign_slug || '%'
      OR file_path LIKE '%' || :investigation_path || '%'
      OR file_path LIKE '%' || :data_path || '%'
    )
)
SELECT session_id, event_time, source, detail, evidence
FROM matched_turns
UNION ALL
SELECT session_id, event_time, source, detail, evidence
FROM matched_files
ORDER BY event_time;
```

If the available store also exposes case-matching tool execution or request rows, include them as corroborating evidence, but never widen the query to unrelated sessions just because they share the
same day. A session with zero matching rows is ignored silently.

## Step 3 — Fresh subagent writes the detailed doc

Launch a fresh subagent with only the matched rows plus the current detailed doc. Its job is to append, never overwrite, one dated section per distinct finding:

```md
## <finding title> (<YYYY-MM-DD>)

### Evidence
| Source | Detail | Why it matters |
|---|---|---|
| ... | ... | ... |

**Conclusion:** <one bolded sentence>
```

Match the style already established by `applauseInvestigation/investigations/docs/7231763-android-resume-watching-latency.md`: findings stay evidence-first, conclusions stay explicit, and every sync
appends only what is new since the cursor.

## Step 4 — Regenerate the session-provenance table

The detailed doc also carries a regenerated provenance table with both `cwd` and a derived `Case/Campaign` column. `cwd` is retained because it becomes more useful once sessions start from nested case
or campaign folders, but today the authoritative column is the derived one from `session_files` path matches.

Worked example shape:

| Date | Session ID | cwd | Case/Campaign |
|---|---|---|---|
| 2026-08-14 | `abe1165e` | `applauseInvestigation` | *(scaffold — no case yet)* |
| 2026-08-14 | `47617f46` | `applauseInvestigation` | `7231547` |
| 2026-08-14 | `80a4af33` | `applauseInvestigation` | `7231763` |
| 2026-08-25 | `a987b3ed` | `applauseInvestigation` | `7231763` |
| 2026-08-20 | `a2e0d27a` | `applauseInvestigation` | *(no files edited — Q&A only)* |

This replaces the decayed manual logging pattern seen in `applauseInvestigation/session-info.md`, where only 8 of 18 real sessions were ever appended by hand.

## Step 5 — Executive summary is a separate pass

`investigation summary <case-id>` does not read raw transcripts. It reads the already-clean detailed doc, condenses its dated sections, and writes
`investigations/.../docs/<case-id>-executive-summary.md` with a headline finding, ruled-out points, and a recommendation.

The summary exists to combine rounds, not replace them. Case `7231763` is the model: one session on 2026-08-14 and another on 2026-08-25 must remain as two dated sections in the detailed doc, while
the executive summary condenses both rounds into one short decision-ready narrative.

## Guarantees

- Multiple sessions on the same case append into the same detailed doc; they never overwrite each other.
- The detailed doc stays the source of truth; the executive summary is derived from it, not from raw history.
- `cwd` alone is never treated as the case identifier; `Case/Campaign` comes from matched file paths and content.
- The skill follows `structure.md` and PT-7's **Inputs used** rule; it does not invent a new doc shape.
