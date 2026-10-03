#!/usr/bin/env python3
"""
Enrich the existing CTAP/SM-VOD report with playback outcome + error detail,
sourced from Athena tables (separate from the Lightstep-based
merge_ctap_smvod_csv.py pipeline -- kept as its own script since the data
source, join semantics, and dedup logic are quite different).

Two additional Athena-derived inputs, joined on `sessionId`:

    1. data/athena/YYYY-MM-DD_session.csv
       Export of:
           SELECT
             parent_session_id AS sessionId,
             MAX(user_id)   AS householdId,
             MAX(device_id) AS deviceId,
             MAX(content)   AS content,
             MAX(CASE WHEN event_type = 'PLAY' THEN endreason END)   AS playback_outcome,
             MAX(CASE WHEN event_type = 'PLAY' THEN event_start END) AS event_start,
             MAX(CASE WHEN event_type = 'PLAY' THEN event_end END)   AS event_end,
             MAX(CASE WHEN event_type = 'REQUEST_VIEWING'
                      THEN date_diff('millisecond', event_start, event_end) END) AS startup_time_ms,
             SUM(CASE WHEN event_type = 'BUFFERING' THEN 1 ELSE 0 END) AS buffering_count,
             SUM(CASE WHEN event_type = 'BUFFERING'
                      THEN date_diff('millisecond', event_start, event_end) ELSE 0 END) AS buffering_total_ms
           FROM "unified_e6auj7k7"."unified_sessions"
           WHERE timestamp_formatted = '<YYYY-MM-DD>'
           GROUP BY parent_session_id;
       (see queries/athena_session_outcome.md)
       One row per session -- aggregates ALL event_type rows for that
       session (PLAY, REQUEST_VIEWING, BUFFERING, ...) instead of filtering
       down to just PLAY, so nothing is lost: `playback_outcome` (from
       PLAY, e.g. DESTROY = ok, PLAYER_ERROR = failed), `startup_time_ms`
       (from REQUEST_VIEWING -- time to first frame), `buffering_count` /
       `buffering_total_ms` (aggregated across all BUFFERING rows -- QoE
       signal), plus `content` (title, constant across all rows for a
       session).

    2. data/athena/YYYY-MM-DD_debug_states.csv  (preferred -- combined error + lifecycle + position)
       Export of (columns already extracted via json_extract_scalar, not raw
       eventdata JSON):
           SELECT DISTINCT
             json_extract_scalar(eventdata, '$.sessionid') AS sessionId,
             eventid,
             COALESCE(
               json_extract_scalar(eventdata, '$.eventtype'),  -- CREATE/DESTROY
               json_extract_scalar(eventdata, '$.state')       -- BUFFERING/PLAYING/PAUSED/STOPPED
             ) AS state,
             json_extract_scalar(eventdata, '$.position')          AS position,
             json_extract_scalar(eventdata, '$.errorcode')        AS errorcode,
             json_extract_scalar(eventdata, '$.errordescription') AS errordescription,
             datetime
           FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
           WHERE eventid IN ('PLAYER_SESSION_EVENT', 'PLAYER_STATE_CHANGE', 'PLAYER_ERROR', 'PLAYER_POSITION', 'APP_KEEPALIVE')
             AND datetime >= '<day start ISO-8601>'
             AND datetime <  '<day end ISO-8601>'
             AND json_extract_scalar(eventdata, '$.sessionid') IN (...)
           ORDER BY sessionId, datetime;
       (see queries/QUERY_CATALOG.md §11/§11a/§11b and
       queries/exploration/04_position_tracking.md)
       Zero or more rows per session -- drives THREE enrichments from a
       single export:
         a) `state_sequence` -- chronological, arrow-joined lifecycle string,
            e.g. "CREATE->BUFFERING->PLAYING->BUFFERING->ERROR(1003)->DESTROY->STOPPED".
            `state` is NULL on PLAYER_ERROR rows (no eventtype/state key in
            that eventdata shape), so PLAYER_ERROR rows are rendered inline
            as "ERROR(<errorcode>)" instead of being silently dropped.
            PLAYER_POSITION and APP_KEEPALIVE rows are NOT lifecycle
            transitions and are excluded from this sequence entirely
            (handled by (c) instead).
         b) error_codes / error_descriptions / error_count / first_error_time
            -- same fields as the legacy debug_errors_* format below, derived
            from whichever rows in this same export have a non-empty
            errorcode (i.e. PLAYER_ERROR rows).
         c) position_samples / min_position / max_position / position_delta /
            position_not_moved -- derived from PLAYER_POSITION rows AND
            APP_KEEPALIVE rows (`state`/`errorcode` are blank on these,
            `position` is the only populated field besides
            sessionId/datetime). APP_KEEPALIVE's `position` is in
            MILLISECONDS (unlike every other eventid, which use seconds) --
            confirmed 13 Jul 2026 via session
            abr-vod-b2255524-92d6-4302-b422-8ef9cd6051ae, whose only
            PLAYER_POSITION row was `position: 0` but whose APP_KEEPALIVE
            heartbeats climbed steadily (106000ms -> 2206000ms), proving the
            session progressed normally -- the eventclass='PLAYER'-only view
            had missed this and would have misclassified it as stalled.
            `parse_position_seconds()` converts APP_KEEPALIVE ms to seconds
            before comparing. Used to catch sessions that
            look "started" (and may even show a clean DESTROY) but never
            actually advanced playback position -- a stall the outcome/error
            fields alone can't reveal. `position_not_moved` is true when
            `max_position - min_position` is under POSITION_NOT_MOVED_THRESHOLD_SECONDS.
       This table is known to emit exact-duplicate rows (at-least-once log
       delivery) -- both the Athena `DISTINCT` and this script's own dedup
       (on the full row tuple) handle that.

    2b. data/athena/YYYY-MM-DD_debug_errors.csv  (legacy fallback -- error-only)
       Raw export of:
           SELECT *
           FROM "unified_e6auj7k7"."e6auj7k7_ccl_debug_events"
           WHERE eventclass = 'PLAYER'
             AND eventid = 'PLAYER_ERROR'
             AND datetime >= TIMESTAMP '<day start>'
             AND datetime <  TIMESTAMP '<day end>';
       (see queries/exploration/02_sample_rows.md)
       Zero or more rows per session -- optional enrichment giving the
       *reason* for a failure (errorcode / errordescription), not just the
       flag. `sessionid`, `errorcode`, `errordescription` are nested inside
       the `eventdata` JSON string column, not first-class columns.
       This table is known to emit exact-duplicate rows (at-least-once log
       delivery) -- this script dedupes them.
       Used only if YYYY-MM-DD_debug_states.csv is not present for the given
       date -- in that case `state_sequence` stays blank (no lifecycle data
       in this legacy format), but error_codes/error_descriptions/etc. are
       still populated same as before.

Both are merged into the existing CTAP/SM-VOD report
(output/YYYY-MM-DD_setupsession.csv, produced by merge_ctap_smvod_csv.py) via
`sessionId`, producing a new enriched report -- the original report is left
untouched.

Usage:
    python3 merge_session_outcome.py --date 08072026
    python3 merge_session_outcome.py --date 08072026 \
        --input-dir ../data/athena --report ../output/2026-07-08_setupsession.csv \
        --out ../output/2026-07-08_setupsession_with_outcome.csv
"""
import argparse
from lib import csv_io_compat as csv
import glob
import json
import os
import re
import sys
from datetime import datetime

from lib.runtime import investigation_output_dir, snapshot_output_path

SESSION_KEY = "sessionId"

ATHENA_FIELDS = ["content", "playback_outcome", "event_start", "event_end",
                 "startup_time_ms", "buffering_count", "buffering_total_ms"]
ERROR_FIELDS = ["error_codes", "error_descriptions", "error_count", "first_error_time"]
STATE_FIELDS = ["state_sequence"]
POSITION_FIELDS = ["position_samples", "min_position", "max_position",
                   "position_delta", "position_not_moved"]

# Below this delta (seconds), a session's PLAYER_POSITION samples are
# considered "not moved" -- tolerates minor rounding/single-sample noise.
POSITION_NOT_MOVED_THRESHOLD_SECONDS = 1.0

OUTPUT_EXTRA_FIELDS = (ATHENA_FIELDS + ERROR_FIELDS + STATE_FIELDS + POSITION_FIELDS
                       + ["outcome_match_status"])


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def find_input_file(input_dir, prefix, date, required=True):
    iso_date = datetime.strptime(date, "%d%m%Y").strftime("%Y-%m-%d")
    pattern = os.path.join(input_dir, f"{iso_date}_{prefix}*.csv")
    matches = sorted(glob.glob(pattern))
    if not matches:
        if required:
            print(f"ERROR: no file matching {pattern}", file=sys.stderr)
            sys.exit(1)
        print(f"NOTE: no file matching {pattern} -- outcome/error columns will be blank", file=sys.stderr)
        return []
    return matches


def load_athena_outcomes(files):
    """One row per sessionId: content, playback_outcome, event_start,
    event_end, startup_time_ms, buffering_count, buffering_total_ms."""
    by_session = {}
    for path in files:
        for row in load_csv(path):
            sid = row.get(SESSION_KEY)
            if not sid:
                continue
            by_session[sid] = {f: row.get(f, "") for f in ATHENA_FIELDS}
    return by_session


def load_debug_errors(files):
    """
    Parse raw e6auj7k7_ccl_debug_events export (eventid=PLAYER_ERROR rows),
    extract sessionid/errorcode/errordescription from the eventdata JSON
    column, dedupe exact-duplicate rows, and aggregate all distinct errors
    per sessionId (a session can have more than one PLAYER_ERROR event,
    e.g. retries).
    """
    seen = set()  # dedupe key: (sessionid, datetime, errorcode, errordescription)
    by_session = {}  # sessionid -> list of (datetime, errorcode, errordescription)

    for path in files:
        for row in load_csv(path):
            if row.get("eventid") != "PLAYER_ERROR":
                continue
            raw = row.get("eventdata", "")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                print(f"WARNING: could not parse eventdata JSON in {path}: {raw[:120]!r}", file=sys.stderr)
                continue

            sid = data.get("sessionid")
            if not sid:
                continue
            errorcode = data.get("errorcode", "")
            errordescription = data.get("errordescription", "")
            dt = row.get("datetime", "")

            dedup_key = (sid, dt, errorcode, errordescription)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            by_session.setdefault(sid, []).append((dt, errorcode, errordescription))

    result = {}
    for sid, errors in by_session.items():
        errors.sort(key=lambda e: e[0])  # chronological
        result[sid] = {
            "error_codes": "; ".join(str(e[1]) for e in errors),
            "error_descriptions": "; ".join(e[2] for e in errors),
            "error_count": str(len(errors)),
            "first_error_time": errors[0][0],
        }
    return result


def parse_position_seconds(raw, eventid=""):
    """
    Parse a raw `position` value into float seconds.

    Confirmed 13 Jul 2026: position is NOT always a plain float -- some
    rows (observed on PLAYER_STATE_CHANGE, likely a client/platform
    difference) report it as an "MM:SS" string (e.g. "00:24", "01:35",
    "0:00") instead of raw seconds (e.g. "1627", "0.001"). Handles both.

    Also confirmed 13 Jul 2026: `APP_KEEPALIVE` rows (eventclass
    APPLICATION, not PLAYER -- e.g. `{"currentscreen":"Player",
    "position":106000,...}`) carry `position` in MILLISECONDS, unlike
    every other eventid which uses seconds. Found via session
    abr-vod-b2255524-92d6-4302-b422-8ef9cd6051ae, whose only PLAYER_POSITION
    row was `position: 0` (session just started) but whose APP_KEEPALIVE
    heartbeats (~5 min apart) climbed steadily from 106000ms to 2206000ms --
    proof the session was progressing normally, which the PLAYER-only view
    would have missed / misclassified as stalled. `eventid` param lets the
    caller signal ms-vs-seconds; converts to seconds here so all position
    values are comparable regardless of source eventid.

    Returns None if unparseable (caller should warn and skip).
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        seconds = None
        parts = raw.split(":")
        if 2 <= len(parts) <= 3 and all(re.fullmatch(r"\d+(\.\d+)?", p) for p in parts):
            seconds = 0.0
            for p in parts:
                seconds = seconds * 60 + float(p)
        if seconds is None:
            return None

    if eventid == "APP_KEEPALIVE":
        seconds = seconds / 1000.0
    return seconds


def load_debug_states(files):
    """
    Parse the combined debug_states export (eventid IN PLAYER_SESSION_EVENT,
    PLAYER_STATE_CHANGE, PLAYER_ERROR, PLAYER_POSITION, APP_KEEPALIVE;
    already flattened via json_extract_scalar into sessionId/eventid/state/
    position/errorcode/errordescription/datetime columns -- see
    queries/QUERY_CATALOG.md §11/§11a/§11b). Drives THREE enrichments from
    one export:

      1. state_sequence -- chronological, arrow-joined lifecycle string per
         session, e.g. "CREATE->BUFFERING->PLAYING->ERROR(1003)->DESTROY->STOPPED".
         `state` is blank on PLAYER_ERROR rows (that eventdata shape has no
         eventtype/state key), so those rows are rendered inline as
         "ERROR(<errorcode>)" rather than silently dropped from the sequence.
         PLAYER_POSITION and APP_KEEPALIVE rows are excluded entirely from
         this sequence (they are not lifecycle transitions -- handled by #3
         instead).
      2. error_codes / error_descriptions / error_count / first_error_time --
         same fields/shape as load_debug_errors(), derived from whichever
         rows in this same export have a non-empty errorcode.
      3. position_samples / min_position / max_position / position_delta /
         position_not_moved -- derived from PLAYER_POSITION AND APP_KEEPALIVE
         rows (`state`/`errorcode` are blank on these, `position` is the
         only populated field besides sessionId/datetime). APP_KEEPALIVE's
         `position` is in milliseconds (converted to seconds via
         parse_position_seconds()) -- everything else is already seconds.
         `position_not_moved` is true
         when `max_position - min_position` is under
         POSITION_NOT_MOVED_THRESHOLD_SECONDS -- catches sessions that
         started (and may even show a clean state_sequence/DESTROY) but
         never actually advanced playback position, a stall that
         state_sequence/errorcode alone can't reveal.

    Dedupes on the full row tuple (sessionId, eventid, state, position,
    errorcode, errordescription, datetime) to guard against the table's
    known at-least-once exact-duplicate-row delivery.

    Returns (states_by_session, errors_by_session, positions_by_session) --
    three dicts, all keyed by sessionId, shaped like STATE_FIELDS /
    ERROR_FIELDS / POSITION_FIELDS respectively.
    """
    seen = set()
    by_session = {}  # sessionid -> list of (datetime, eventid, state, errorcode, errordescription, position)

    for path in files:
        for row in load_csv(path):
            sid = row.get(SESSION_KEY, "")
            if not sid:
                continue
            eventid = row.get("eventid", "")
            state = row.get("state", "")
            errorcode = row.get("errorcode", "")
            errordescription = row.get("errordescription", "")
            position = row.get("position", "")
            dt = row.get("datetime", "")

            dedup_key = (sid, eventid, state, position, errorcode, errordescription, dt)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            by_session.setdefault(sid, []).append((dt, eventid, state, errorcode, errordescription, position))

    states_result = {}
    errors_result = {}
    positions_result = {}
    for sid, events in by_session.items():
        events.sort(key=lambda e: e[0])  # chronological

        labels = []
        errors = []  # (datetime, errorcode, errordescription)
        positions = []  # (datetime, position as float)
        for dt, eventid, state, errorcode, errordescription, position in events:
            # `position` can appear in eventdata for eventids OTHER than
            # PLAYER_POSITION too (confirmed 13 Jul 2026: PLAYER_STATE_CHANGE
            # rows, e.g. STOPPED, can carry a non-trivial position value even
            # when no PLAYER_POSITION row captured it) -- so collect it from
            # every row where it's populated, not just PLAYER_POSITION rows.
            if position not in ("", None):
                parsed = parse_position_seconds(position, eventid=eventid)
                if parsed is not None:
                    positions.append((dt, parsed))
                else:
                    print(f"WARNING: could not parse position {position!r} "
                          f"for session {sid}", file=sys.stderr)

            if eventid in ("PLAYER_POSITION", "APP_KEEPALIVE"):
                continue  # not a lifecycle transition -- excluded from state_sequence

            if errorcode:
                labels.append(f"ERROR({errorcode})")
                errors.append((dt, errorcode, errordescription))
            else:
                labels.append(state or eventid)

        states_result[sid] = {"state_sequence": "->".join(labels)}

        if errors:
            errors_result[sid] = {
                "error_codes": "; ".join(str(e[1]) for e in errors),
                "error_descriptions": "; ".join(e[2] for e in errors),
                "error_count": str(len(errors)),
                "first_error_time": errors[0][0],
            }

        if positions:
            values = [p[1] for p in positions]
            min_position = min(values)
            max_position = max(values)
            position_delta = max_position - min_position
            positions_result[sid] = {
                "position_samples": str(len(positions)),
                "min_position": f"{min_position:.6f}",
                "max_position": f"{max_position:.6f}",
                "position_delta": f"{position_delta:.6f}",
                "position_not_moved": "true" if position_delta < POSITION_NOT_MOVED_THRESHOLD_SECONDS else "false",
            }

    return states_result, errors_result, positions_result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Date in DDMMYYYY format, e.g. 08072026")
    default_input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "athena")
    default_output_dir = str(investigation_output_dir())
    ap.add_argument("--input-dir", default=default_input_dir)
    ap.add_argument("--report", default=None,
                    help="Existing merged report to enrich (default: <output-dir>/YYYY-MM-DD_setupsession.csv)")
    ap.add_argument("--out", default=None,
                    help="Output CSV path (default: <output-dir>/YYYY-MM-DD_setupsession_with_outcome.csv)")
    args = ap.parse_args()

    report_path = args.report or snapshot_output_path(args.date, "setupsession", output_dir=default_output_dir)
    if not os.path.exists(report_path):
        print(f"ERROR: report file not found: {report_path} "
              f"(run merge_ctap_smvod_csv.py first)", file=sys.stderr)
        sys.exit(1)

    athena_files = find_input_file(args.input_dir, "session", args.date, required=False)
    debug_states_files = find_input_file(args.input_dir, "debug_states", args.date, required=False)
    debug_error_files = []
    if not debug_states_files:
        debug_error_files = find_input_file(args.input_dir, "debug_errors", args.date, required=False)

    report_rows = load_csv(report_path)
    if report_rows and not athena_files:
        print(
            "WARNING: no Athena session enrichment file was found in "
            f"{args.input_dir} for {args.date}; playback/session columns will remain blank "
            "unless you move the export into data/athena/ with the new ISO-prefixed name.",
            file=sys.stderr,
        )
    if report_rows and not debug_states_files and not debug_error_files:
        print(
            "WARNING: no Athena debug enrichment files were found in "
            f"{args.input_dir} for {args.date}; error/lifecycle/position columns will remain blank "
            "unless you move the exports into data/athena/ with the new ISO-prefixed names.",
            file=sys.stderr,
        )
    outcomes_by_session = load_athena_outcomes(athena_files)

    if debug_states_files:
        # Preferred: one combined export drives state_sequence,
        # error_codes/error_descriptions/etc., and position_* fields.
        states_by_session, errors_by_session, positions_by_session = load_debug_states(debug_states_files)
        debug_source_note = f"debug_states ({len(debug_states_files)} file(s))"
    else:
        # Legacy fallback: error-only export, no lifecycle/state_sequence/position data.
        states_by_session = {}
        positions_by_session = {}
        errors_by_session = load_debug_errors(debug_error_files)
        debug_source_note = f"debug_errors legacy ({len(debug_error_files)} file(s))" if debug_error_files else "none"

    outcome_matched = 0
    outcome_missing = 0
    error_enriched = 0
    state_enriched = 0
    position_enriched = 0

    out_rows = []
    for row in report_rows:
        sid = row.get(SESSION_KEY, "")
        outcome = outcomes_by_session.get(sid)
        errors = errors_by_session.get(sid)
        states = states_by_session.get(sid)
        positions = positions_by_session.get(sid)

        new_row = dict(row)
        if outcome:
            new_row.update(outcome)
            outcome_matched += 1
            status = "outcome_matched"
        else:
            for f in ATHENA_FIELDS:
                new_row[f] = ""
            outcome_missing += 1
            status = "outcome_missing (no unified_sessions row for this sessionId)"

        if errors:
            new_row.update(errors)
            error_enriched += 1
        else:
            for f in ERROR_FIELDS:
                new_row[f] = ""

        if states:
            new_row.update(states)
            state_enriched += 1
        else:
            for f in STATE_FIELDS:
                new_row[f] = ""

        if positions:
            new_row.update(positions)
            position_enriched += 1
        else:
            for f in POSITION_FIELDS:
                new_row[f] = ""

        new_row["outcome_match_status"] = status
        out_rows.append(new_row)

    out_path = args.out or snapshot_output_path(args.date, "setupsession_with_outcome", output_dir=default_output_dir)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    fieldnames = list(report_rows[0].keys()) if report_rows else []
    for f in OUTPUT_EXTRA_FIELDS:
        if f not in fieldnames:
            fieldnames.append(f)

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Report rows loaded:            {len(report_rows)}")
    print(f"Athena outcome rows loaded:    {sum(1 for _ in outcomes_by_session)}")
    print(f"Debug-events source used:      {debug_source_note}")
    print(f"Debug-error sessions loaded:   {len(errors_by_session)}")
    print(f"Debug-state sessions loaded:   {len(states_by_session)}")
    print(f"Debug-position sessions loaded: {len(positions_by_session)}")
    print(f"Outcome matched:               {outcome_matched}")
    print(f"Outcome missing:               {outcome_missing}")
    print(f"Sessions enriched with error detail:  {error_enriched}")
    print(f"Sessions enriched with state_sequence: {state_enriched}")
    print(f"Sessions enriched with position data:  {position_enriched}")
    print(f"\nWrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
