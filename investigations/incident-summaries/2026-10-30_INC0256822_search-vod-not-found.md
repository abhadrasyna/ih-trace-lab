# INC0256822 Investigation Summary

> Source scope: Only the two attached Teams meeting transcripts were used. Where information was not stated, it is marked **Not stated**.

## 1. Incident

- **ID:** INC0256822
- **Raised date:** Not stated
- **Reporter:** Not stated
- **Affected tenant/OpCo:** MTN-1, Ghana and Zambia. South Africa/IYE was unaffected and used for comparison.
- **Platform/device/app version:** App/Web UI; device and exact versions **Not stated**. The Ghana and South Africa app versions were confirmed different.
- **Severity:** P1 initially; reduction to P2 was proposed, but final change **Not stated**.
- **Current status:** Content recovered and became searchable after the scheduled full Search ingest. Incident remained open for root-cause confirmation.

## 2. Symptom & impact

The promoted series **“100 Reasons to Stay Single in Lagos”** and its episodes were visible in the hero/swimlane after being added using the package asset ID, but could not be found by title in the
Ghana/Zambia app, Web UI or OpsHub. Search displayed **“no result”**. South Africa returned the same content. This was not a general Search outage; other content remained searchable.

- **Affected users/devices/sessions:** Not stated
- **Start/end times:** Not stated

## 3. Timeline

- **2026-10-29, time Not stated** - Real Media/publishing flow ingested the promoted VOD content.
- **2026-10-29, time Not stated** - Stan Pendyk used the package asset ID to place the asset in the swimlane.
- **2026-10-30 01:19 UTC** - P1 investigation call began; issue reproduced in Ghana/Zambia and compared with working South Africa.
- **2026-10-30, time Not stated** - Episode title was changed to the series title and republished; suggestions appeared, but content Search still returned nothing.
- **2026-10-30 approximately 02:00 (timezone not confirmed in transcript; verify against ingest logs)** - Latest full Search build ran and recovered Search.
- **2026-10-30 07:35 UTC** - Follow-up investigation reviewed ingest logs and confirmed the incremental update’s second stage never started.
- **2026-10-30, time Not stated** - Search Ingest was restarted as a precaution.

## 4. Hypotheses

### Adult/18+ filtering

- **Evidence for:** Ghana/Zambia requests contained `isAdult=false`/`isErotic=false`.
- **Evidence against:** Rating 18 was not mapped as adult; flags were off in all three OpCos.
- **Final status:** Rejected

### Incorrect episode/main-title mapping

- **Evidence for:** The VOD asset had the episode title populated as the main title. The expected structure is the series title as the main title, with the episode name stored separately. This
  mattered because Search is expected to search against the main title, not the separate episode-title field.
- **Evidence against:** Stan Pendyk corrected the Ghana asset so the main title matched the series title, "100 Reasons to Stay Single in Lagos", and the content was re-ingested. The corrected asset
  was present afterwards, but Search still returned no results.
- **Final status:** Confirmed metadata issue, rejected as root cause.
- **One-line summary:** The episode title had been used as the main title instead of the series title, but correcting and re-ingesting the metadata did not restore Search, so this mismatch was not the
  underlying cause of INC0256822.

### Wrong catalogue/filter tags

- **Evidence for:** Not stated
- **Evidence against:** Catalogue ID 1 matched MTN Ghana Live; unfiltered VOD query also failed.
- **Final status:** Rejected

### Wrong VOD Content DB

- **Evidence for:** Multiple VOD Content DBs were considered during investigation.
- **Evidence against:** Asset existed in VOD Content DB with valid language/type/update fields; the update-stage start log was absent before any DB lookup.
- **Final status:** Rejected

### Incremental Search update hung or reached a limit

- **Evidence for:** SQS was handled and a 10-minute timer announced, but `Starting content update on contentId` never appeared in MTN-1; it appeared in South Africa.
- **Evidence against:** No direct proof of the exact hung job or limiter condition was captured.
- **Final status:** Open, leading theory

## 5. Evidence & queries

### Search endpoint

```text
<!-- lint-ignore-length -->
/search/1.0.0/content?count=20&sort=-dateTimeAdded&pset=As_StandardC&searchCriterion=cast%2Ckeyword%2Ctitle~100%20reasons%20to%20stay%20single%20in%20lagos&collapse=true&historyOptIn=true&catalogueId=1&region=40000&lang=eng&filter=adult~false&filter=erotic~false&filter=source~vod&excludeRestrictedProviders=true
```

- **Issue present:** Response size `23`
- **Recovered:** Response size `8528`
- During failure, Search Aggregator did not call:

```text
/vodContentGet/content?lang=eng&contentIdList=MTN0_47_0000300000&catalogueId=1
```

### Suggest query

```text
<!-- lint-ignore-length -->
/search/1.0.0/suggest?count=20&searchField=cast%2Ckeyword%2Ctitle&queryKey=100%20&historyOptIn=true&catalogueId=Test_GH_Catalog&region=8085&lang=eng&filter=adult~false&filter=erotic~false&filter=source~vod&filter=source~ltv&filter=source~catchup&excludeRestrictedProviders=true
```

Suggestions eventually appeared, but selecting one returned no content.

### Elasticsearch

```bash
curl "http://search1523-elasticsearch:9200/search_vod/_search?q=title:lagos" | jq '.'
```

**Result:** Four assets were returned in the VOD index.

### Search health check

```bash
kubectl exec -it search1523-search-aggregator-6574f4d46-bl45n -- curl -s http://localhost:80/search/1.0.0/health | jq -S '.indexer.ingest'
```

**Result:** The latest full build was reported at approximately `02:00`; whether this was the start or completion time was not established.

### Logs and identifiers

- **Expected log:** `Starting content update on contentId`
- **Observed logs:**
  - `Should look for the contentId~instanceId after 600000ms`
  - `Successfully handled sqs message`
- **Identifiers:**
  - `daa13dc7-2a78-5087-b7c0-7f17539d734c`
  - `ab73c2d0-0dfb-55b4-9ce9-1b2210ebdc6e`
  - `f77cef7b-001d-5c2d-9890-ccc755b64254`
  - `MTN0_MTN02100000000301001`
  - `MTN00000000000301001`
  - `FCID=b6f807d4081f433c97817e05f9d92612`
  - `FCID=2394b77e75d646bea51ba80fd6098f57`

## 6. Root cause

**Not confirmed.**

Best current theory: MTN-1’s incremental Search update jobs reached a hung or limiter state. SQS notifications were accepted, but the deferred update task never started.

- **Confidence:** Medium-High (theory, unconfirmed)
- **Basis:** Missing second-stage start log and recovery through the separate full-ingest path

## 7. Fix / workaround

- The scheduled full Search ingest recovered the content.
- Search Ingest, not Search Aggregator, was restarted to reset resources.
- Restarting alone does not publish previously missed content. Recovery requires republishing the VOD asset or running a full ingest.
- The package asset ID was used as a temporary workaround to add the content to the hero/swimlane.
- Verification after restart and republish: **Not stated**.

## 8. Open questions & next steps

- **Confirm why incremental jobs hung**
  - **Owner:** Search Engineering / Itai Elran
  - **Due date:** Not stated
- **Add detection and logging for limiter saturation or ignored updates**
  - **Owner:** Search Engineering
  - **Due date:** Not stated
- **After publishing, wait 15 minutes and check for `Starting content update on contentId`**
  - **Owner:** Operations
  - **Due date:** On recurrence
- **If the log is absent, restart Search Ingest, republish by toggling the VOD published key, and verify after 15 minutes**
  - **Owner:** Operations/Publishing
  - **Due date:** On recurrence
- **Assess the performance implications of the full-ingest API before operational use**
  - **Owner:** Search Engineering
  - **Due date:** Not stated

## 9. Links

- **Ticket:** INC0256822
- **Teams incident chat/meeting:** Shared in the thread; exact URL not stated in the transcript
- **Lightstep traces:** Two traces were shared; exact URLs not stated in the transcript
- **Search health endpoint:** Included in the Evidence & queries section
- **Elasticsearch endpoint:** Included in the Evidence & queries section
- **PR:** Not stated
- **RCA document:** Not stated
- **Dashboard:** Not stated

## 10. Lessons for future incidents

- Check Search Ingest logs before investigating application filters.
- Successful SQS handling does not prove indexing completed.
- Confirm that `Starting content update on contentId` appears within 15 minutes of publication.
- Compare the second-stage log with a healthy OpCo such as South Africa.
- Verify the asset in VOD Content DB and Elasticsearch.
- Distinguish an incremental update failure from recovery through the separate full-ingest path.
- Escalate when the expected second-stage log is absent 15 minutes after publication.
