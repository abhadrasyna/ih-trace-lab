# Knowledge: DASH MPD Restriction Fields & Shaka Player Selection Logic

> Distilled from a HAR/MPD analysis session (2026-07-27) comparing `investigations/xmls_or_mpd/index.mpd`, `second_screen.mpd`, and `second_screen_1.mpd` (MTN SA `iye9omdf` and TIM Play `iljyxcc3` VOD
> manifests), plus the Shaka Player source (`lib/util/mutex.js`, `lib/util/stream_utils.js`, `lib/util/periods.js`, `lib/player.js`, tag `main` as of 2026-07-27). Read this first when debugging why a
> player picked (or refused) a Representation, or decoding a Shaka mutex-log sequence.

**Related:** `knowledge/mtn-sa-timplay-drm-cross-tenant-trace-analysis.md` covers the tenant-specific MTN SA versus TIM Play flow differences that overlap with this note; keep that file for the
case-level comparison and this one for the distilled reusable rule set.


## 1. `minBandwidth`/`maxBandwidth` on `AdaptationSet` — informational only

```xml
<AdaptationSet ... minBandwidth="1675000" maxBandwidth="4945000"
                maxWidth="1920" maxHeight="1080" .../>
```

These are **summary hints**, not enforced limits — they tell a player the range of bitrates/resolutions contained in that set so it can quickly filter/skip sets without parsing every `Representation`.
The per-`Representation` `bandwidth` attribute is what ABR actually switches between; `AdaptationSet`-level `maxBandwidth` never overrides it.

## 2. Player-side `maxBandwidth` **restriction** (e.g. Shaka `restrictions.maxBandwidth`) is checked against combined variant bandwidth, not video alone

This is the critical gotcha. Shaka's `shaka.util.StreamUtils .meetsRestrictions(variant, restrictions, maxHwRes)` (`lib/util/stream_utils.js`) checks:

```js
if (!inRange(variant.bandwidth,
    restrictions.minBandwidth, restrictions.maxBandwidth)) {
  return false;
}
```

`variant.bandwidth` is **audio + video bandwidth summed** (`lib/util/periods.js`: `bandwidth = (audio.bandwidth || 0) + (video.bandwidth || 0)`). So a `maxBandwidth` restriction must clear **video
Representation bitrate + paired audio Representation bitrate**, not just the video track's own `bandwidth`.

**Worked example** (`second_screen_1.mpd`): lowest video `Video1` = 182,994 bps, audio `Audio1` = 342,103 bps → combined variant bandwidth = **525,097 bps**. A restriction of `maxBandwidth = 506176`
looks like it should permit `Video1` (well above its solo 182,994 bps) but actually **rejects every variant**, because 525,097 > 506,176. Result: Shaka throws `RESTRICTIONS_CANNOT_BE_MET` (category
`MANIFEST`) and no video plays at all — not even the lowest rendition.

**Rule of thumb when troubleshooting a "player won't play/select any quality" complaint tied to a bandwidth cap:** always add the paired audio Representation's `bandwidth` before comparing against the
configured cap. A cap that looks "obviously fine" against the video bitrate alone can still exclude everything.

## 3. How to read Representations quickly in a captured `.mpd`

```bash
grep -oE '<Representation width="[0-9]+" height="[0-9]+"[^>]*id="Video[0-9]+"[^>]*bandwidth="[0-9]+"' file.mpd \
  | sed -E 's/width="([0-9]+)" height="([0-9]+)".*id="(Video[0-9]+)".*bandwidth="([0-9]+)"/\3 bandwidth=\4 \1x\2/'
# Audio representation(s):
grep -n '<Representation.*mp4a\|<Representation.*audio' file.mpd
```

Also check `<Period>` count (`grep -c "<Period"` ) — SSAI-stitched VOD (e.g. MTN SA via `vod-dai-ott-eu2.ssai.iris.synamedia.com`) typically has many Periods (ad + content boundaries) and repeats the
same `ContentProtection`/`Representation` blocks once per Period, while a non-SSAI single-asset manifest has one Period.

## 4. `laurl`/license URL is never embedded in these MPDs

Across all three MTN SA/TIM Play manifests reviewed (`index.mpd`, `second_screen.mpd`, `second_screen_1.mpd`), there is **no** `laurl`, `<mspr:LA_URL>`, or DASH-IF `laurl` ContentProtection scheme
present, even when the `xmlns:mspr="urn:microsoft:playready"` namespace is declared. The license acquisition URL is delivered out-of-band via the CTAP play-session response (`_links.laUrl` → `POST
.../mdrmfe/1.0.0/<tenant>/license/<...>/playready|widevine/<contentId>`), not via the manifest. Don't expect to find it by grepping the MPD.

## 5. [MTN-specific] Highest-profile selection race vs. DRM authorization (Edge/PlayReady)

> Scope: this section is **MTN-specific** (MTN SA Windows Edge/PlayReady playback), from a 2026-07-28 meeting discussion. Do not generalize to other tenants/players without separate confirmation.

On initial manifest load, the player (Edge/Shaka) may request the **highest available profile immediately**, before the DRM license response — which carries the *authorized* profile/security-level
info — has been processed. If that highest profile isn't actually authorized, playback fails, even though a lower authorized profile would have worked.

**This is a timing/ordering issue distinct from the `maxBandwidth` combined-audio+video-bandwidth bug in Section 2 above — don't conflate the two.** Both can independently cause "playback fails to
start" on the same manifest. When triaging an MTN playback failure, check both:
1. Is `maxBandwidth` (or any bandwidth restriction) excluding all variants due to combined audio+video bandwidth? (Section 2)
2. Is the player selecting the highest profile *before* the license/authorization response is known, regardless of any bandwidth cap? (this section)

**Candidate mitigations discussed (not yet confirmed fixes — treat as open options pending staging validation):**
- `drm.delayLicenseRequestUntilPlayed` (Shaka config) — delays the license request until `play()` rather than eagerly on load. Note this changes *request timing* but doesn't by itself stop profile
  selection from happening before authorization is known.
- Starting ABR with a low default bandwidth estimate.
- Programmatically restricting to the lowest profile from the manifest instead of relying on a hard-coded bandwidth cap.

**Open/unconfirmed question — do not treat as settled:** whether Windows Edge + PlayReady is actually capable of playing the highest authorized profile (up to 1080p) when properly authorized, or
whether there's a separate DRM authorization gap unrelated to ABR/profile- selection logic. Needs staging validation (test streams with profiles up to 1080p) before being written up as a confirmed
root cause.

Source: 2026-07-28 MTN meeting summary (highest profile / DRM authorization discussion).

## 6. Shaka Mutex log sequence (`lib/util/mutex.js`) — normal serialization, not an error

Log format: `<operationName> has requested/acquired/released mutex` (emitted at `shaka.log.v2`). A typical sequence:

```
waitForFinish has released mutex   // prior load() step (preloadManager.waitForFinish()) finished
unload has requested mutex         // unload() called (stop/destroy/switch content)
unload has acquired mutex          // no contention, unload proceeds into its try{} block
Player changing buffering state to false   // unload()'s cleanup calls updateBufferState_()
unload has released mutex          // unload()'s finally{} releases the lock
```

This is Shaka's cooperative locking (`shaka.util.Mutex` in `lib/util/mutex.js`) serializing async operations (`load`, `unload`, `attach`, `detach`) so they can't run concurrently. By itself this
sequence is **benign** — expected on stop/`src` change/destroy/content switch. Only worth flagging if `unload` fires unexpectedly right after a successful license/manifest fetch (premature playback
stop) — in that case, look at what's calling `unload()`/`load()` in the app layer, not at the mutex log itself.

Source session: 2026-07-27 MPD/Shaka analysis (see `investigations/xmls_or_mpd/` for the manifests referenced above).
