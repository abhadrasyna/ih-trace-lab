# Knowledge: MTN HAR, Kinesis, and Manifest Analysis Methodology

## Read this first when

Consult this before parsing a raw HAR for a playback-flow timeline, before decoding Kinesis `PutRecords` telemetry from a HAR, or before analyzing a device-ID CSV for user-agent / browser-version
breakdown via Lightstep.

## HAR playback-flow analysis method

The HAR playback-flow playbook treats a browser HAR as a session timeline source, not just a bag of requests.

Reusable shape:

1. identify the playback sessions present in the HAR;
2. build a **per-session event timeline** from Play Tap (T0) to first frame;
3. build a **cross-session comparison table** so multiple attempts can be contrasted side by side;
4. finish with **root-cause observations** explaining what was slow and why, rather than dumping raw timings only.

That last framing matters: the methodology is meant to answer both chronology and diagnosis.

## Kinesis stream-analysis method

The Kinesis playbook focuses on the client's analytics/telemetry path, not the media path itself.

Reusable rules:

- locate every HAR request whose `X-Amz-Target` is `Kinesis_20131202.PutRecords`;
- extract and flatten every record payload;
- classify events into the three top-level families used in these sessions: `APPLICATION`, `ACTION`, and `PLAYER`;
- deduplicate by the message identity because the client SDK can re-send the same batch; and
- group the final output per session so state changes, positions, stalls, EOFs, and app-level events line up chronologically.

The source also calls out two extra gotchas worth preserving:

- cancelled / status-0 Kinesis requests should be reported explicitly as likely lost telemetry; and
- `APP_STATE_CHANGE` / `APP_KEEPALIVE` rows that name a `sessionId` belong inside that session's sub-table, not in a global top-level bucket.

## MPD / DASH analysis rules

The MPD playbook's reusable, non-MTN-specific rules are:

- report the **full** video ladder, not just the maximum rendition;
- separate audio, I-frame, and thumbnail tracks from the video ladder;
- extract tenant, content type, asset UUID, and DRM-profile clues from manifest paths and `BaseURL` values;
- treat multi-period manifests carefully: de-duplicate identical ladders but flag if periods differ; and
- remember that the manifest usually does **not** embed the license URL — the `laUrl` arrives out-of-band from playsession metadata.

For the deeper Shaka-source reasoning, worked examples, and the MTN-specific DRM-authorization-race detail, use `knowledge/mpd-shaka-restrictions-analysis.md` rather than duplicating that material
here.

## Device / user-agent / playsession CSV method

The device-UA playbook standardizes one specific recurring input/output shape:

- input file: `YYYYMMDD.csv` of device IDs;
- query target: `createPlaySession` spans in the chosen Lightstep project / region;
- grouping field: `http.user_agent`;
- enrichment goal: extract Android version and Chrome version from the user-agent string;
- output file: `{date}_user_agent.csv`.

This is a report-building method, not just a one-off query. The grouped user-agent export is the deliverable.

## What this file does not port

The executable wrappers from the source playbooks ("paste this file into Copilot", shell-snippet scaffolding, and direct invocation wording) stay in `github_copilot/investigations/instructions/`. This
file only distills the reusable analysis approach.

## Source

Source paths: `/Users/abhadra/github_copilot/investigations/instructions/har-playback-flow-analysis.md`, `/Users/abhadra/github_copilot/investigations/instructions/kinesis-stream-analysis.md`,
`/Users/abhadra/github_copilot/investigations/instructions/mpd-analysis.md`, and `/Users/abhadra/github_copilot/investigations/instructions/device-ua-playsession-analysis.md`. These files are
read-only reference, not a shared codebase.
