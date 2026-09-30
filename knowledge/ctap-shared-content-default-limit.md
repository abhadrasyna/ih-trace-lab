# Knowledge: CTAP `shared/content` / `agg/content` default `limit` is hardcoded to 10

> Distilled from `investigations/docs/20260805-mtn-sa-inc0254814-season-truncation.md` (INC0254814, MTN SA, 2026-08-05). Read the full case doc for the HAR/Lightstep/ CSV/Jira evidence chain; this
> file only captures the reusable fact.

**Related:** `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` covers the tenant-specific MTN SA versus TIM Play flow differences that overlap with this note; keep that file for the
case-level comparison and this one for the distilled reusable rule set.


## The fact

In CTAP's `cue` component, repo **`IH/ctap`**, file **`cue/lib/utils/cmaConfigConstructors.js`**, function `AggContentConfig` (reused by `SharedContentConfig` for the `/ctap/v1/shared/content` route):

```js
// limit - integer ≥ 1, default: 40      <-- stale comment, ignore it
queryParams.limit = validatePositiveNumber(queryParams.limit, 10);
```

If a client omits `limit` on **any** `shared/content` or `agg/content` call (`categoryId=`, `showId=`, `seasonId=`, etc.), CTAP silently defaults it to **10** before forwarding to `vodcontent-get` as
`count=10`. This is a generic default, not endpoint-specific — but it's most visible on the `showId=` "list all seasons for a show" flow, because that particular client call never sends
`limit`/`offset` (unlike `seasonId=`→episodes or `categoryId=`→browse calls, which do pass explicit `limit`).

An identical `validatePositiveNumber(queryParams.limit, 10)` default also exists in the older deprecated `ContentConfig` function (pre refAPI 1.7.0), so the behavior isn't new.

## Why this matters for future investigations

- **Symptom pattern:** a show/category/season listing that mysteriously caps out at exactly 10 items, with the response's own `"total"` field *also* reporting 10 (not the true count) — that
  combination is the signature of this default kicking in, because CTAP passes its hardcoded `limit` through as `count` to `vodcontent-get`, and `vodcontent-get`'s reported total reflects that page,
  not the full catalog.
- **How to confirm quickly:** check the client HAR request for a missing `limit`/`offset` param, then check the matching Lightstep span's downstream `vodContentGet/content` `http.target` for
  `count=10`. If present, this is the cause — no further theory needed.
- **Don't confuse with:** requests that *do* pass an explicit `limit` (e.g. `categoryId=...&limit=15`) — those correctly forward the client's own value as `count` and are unaffected.
- **No related Jira ticket exists yet** (checked as of 2026-08-05) — if you hit this again, it may be worth filing one instead of assuming it's already tracked.

## Where to look in code

- `IH/ctap` → `cue/lib/utils/cmaConfigConstructors.js`
  - `AggContentConfig` (~line 706) / `SharedContentConfig` (line 894) — current, active path (refApi ≥ 1.7.0)
  - `ContentConfig` (~line 588) — deprecated pre-1.7.0 path, same default

## Working reference client pattern (Astro, contrast case)

Checked 2026-08-05 against `investigations/har/astrogo.astro.com.my_INC0254814.har` (show "Upin & Ipin", Lightstep project `bt-inf-prod-astroprod-eks`, US region) — Astro's `shared/content?showId=`
calls **always pass an explicit `limit=255`** (seen consistently across both a Chrome web client and a Tizen Smart-TV client), so they never fall into CTAP's hardcoded `limit=10` default and get the
show's full season list back (`count: 18, total: 18`). This is the opposite of MTN SA's onetv1 client (INC0254814), which sends no `limit` at all on this route and gets truncated to 10.

**Takeaway:** the bug only bites clients that omit `limit` on `shared/content?showId=`. Any client that defensively sends a large explicit `limit` (e.g. 255) sidesteps it entirely — this is the same
backend/repo/hardcoded-default in both cases, the difference is purely client-side query construction.

**Also confirmed:** the `total` field in the response is *not* an independent true-catalog-size count — it mirrors whatever `limit` was effectively used. Astro HAR entry with `limit=1` on the same
show returns `count:1, total:1`, not `18`. This is harmless for Astro only because its real limit (255) exceeds the actual season count — it's the same underlying API quirk as the MTN truncation, just
not observable there since nothing gets cut off.

## Live re-verification (2026-08-05, MTN SA prod, `showId=MNBG_47_0001100000` "Little Baby Bum")

Replayed the onetv1 client's captured `shared/content?showId=` request directly against `https://api-iye9omdf.go.synamedia.com/ctap/v1/shared/content` with three variants, confirming both the bug and
the fix, plus a new `sort` interaction not previously documented:

| Params appended | `count`/`total` | Order |
|---|---|---|
| *(none — client default)* | 10 / 10 | Arbitrary subset (seasons 1,4,5,8,17,... — not the lowest 10) |
| `&limit=255` | 22 / 22 | **Unsorted** — seasons returned in arbitrary order (e.g. 4,5,17,8,1,13,9,7,10,12,11,16,22,2,18,19,20,6,3,15,14,21) |
| `&limit=255&sort=seasonNumber` | 22 / 22 | Correctly ordered 1→22 |

**New takeaway:** `limit` and `sort` are independent fixes for two separate defaults — `limit=255` alone solves the truncation (confirms the `count:10` default from the fact above) but does **not**
imply any ordering guarantee; CTAP/`vodcontent-get` returns seasons in whatever underlying storage order it has unless `sort=seasonNumber` (or equivalent) is explicitly requested. A client that only
adds `limit` without `sort` will get the complete list but potentially in a confusing/non-chronological order — worth checking for on any client that already patched the truncation but still reports
"seasons look out of order."
