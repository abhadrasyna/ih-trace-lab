"""Pure parsing logic for one row of `e6auj7k7_ccl_debug_events` (Athena).

No file I/O here on purpose -- every function takes already-loaded data
(a CSV row dict, or an already-parsed `eventdata` dict) and returns a flat
dict, so this module is trivially unit-testable and reusable from any
CLI/script/notebook. The thin CLI wrapper that streams a CSV file one row
at a time lives in `scripts/flatten_debug_events.py`.

Table shape (see queries/QUERY_CATALOG.md and
knowledge/mtn-athena-unified_e6auj7k7-tables.md for the full DDL):
    datetime, messageid, clibversion, clientid, eventclass, eventid, eventdata
`clientid` is `<deviceId>:<householdId>`. `eventdata` is a JSON blob whose
shape depends entirely on `eventid` -- that's what this module flattens.

Adapted from the per-eventid formatting logic in
`applauseInvestigation/scripts/analyze_athena_playback.py`
(`format_event_detail`), but restructured to return **structured fields**
per event type instead of a human-readable string, so the output can be
loaded back as a proper CSV/DataFrame for column-by-column analysis
(e.g. comparing against Lightstep CTAP/SM-VOD columns).
"""
import json

# Every eventid this module knows how to flatten, and the extra (beyond
# the common fields) column names it can contribute. Used to build a
# stable, superset fieldname list for CSV output -- see
# `flatten_debug_events.py`'s ALL_FIELDNAMES.
EXTRA_FIELDS_BY_EVENTID = {
    "PLAYER_STATE_CHANGE": ["state", "position"],
    "PLAYER_BUFFER_LEVEL": ["bufferlevel_cur", "bufferlevel_avg", "bufferlevel_min",
                             "bufferlevel_max", "position", "numsegments"],
    "PLAYER_SESSION_EVENT": ["eventtype", "content_id", "content_type", "content_source",
                              "content_title", "content_genre", "content_subgenre",
                              "resolution_quality", "user_entitlements", "result"],
    "PLAYER_SEEK": ["previous_position", "position"],
    "PLAYER_POSITION": ["position"],
    "PLAYER_ERROR": ["errorcode", "error_text", "shaka_code", "shaka_message",
                      "user_agent", "position"],
    "PLAYER_EOF": ["position"],
    "ACTION_SCREEN_CHANGE": ["screen_name", "eventtype"],
    "ACTION_PLAYBACK_REQUEST": ["content_id"],
    "APP_KEEPALIVE": ["current_screen"],
    "APP_STATE_CHANGE": ["state"],
    "APP_DISCOVERY": ["device_class", "app_version", "device_name", "device_os",
                       "country_code", "is_registered"],
    "PLAYER_TRACK_CHANGE": ["track_type", "bitrate", "resolution", "framerate",
                             "codecs", "position"],
    "PLAYER_SETTINGS": ["position", "audio_track", "subtitle_track", "speed",
                         "quality_resolution", "quality_bitrate"],
    "ACTION_SELECT": ["screen_id", "content_id", "swimlane_id", "swimlane_position"],
    "ACTION_PREF_UPDATE": ["setting_id", "setting_value"],
}

# Common fields present on every flattened row regardless of eventid.
COMMON_FIELDS = ["datetime", "device_id", "household_id", "eventclass", "eventid",
                  "session_id", "raw_eventdata"]


def parse_eventdata(raw_json):
    """Best-effort JSON parse of one row's `eventdata` string. Returns {}
    on missing/malformed input rather than raising -- a single corrupt
    row should never abort a whole-file flatten run."""
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def split_clientid(clientid):
    """`clientid` is '<deviceId>:<householdId>'. Returns (device_id,
    household_id), defensively -- both None if the value doesn't contain
    the expected separator (matches the "not yet confirmed" caveat on
    this split order noted in queries/QUERY_CATALOG.md #26/#29c)."""
    if not clientid or ":" not in clientid:
        return None, None
    device_id, household_id = clientid.split(":", 1)
    return device_id, household_id


def _human_error_text(errordescription):
    """`errordescription` can be a plain string or a nested JSON object
    carrying its own `errordescription` string plus `shakaerror`/
    `user_agent`/`playerstatesnapshot`."""
    if isinstance(errordescription, dict):
        return errordescription.get("errordescription", "")
    return errordescription or ""


def _shaka_error_info(errordescription):
    if isinstance(errordescription, dict):
        shaka = errordescription.get("shakaerror") or {}
        return shaka.get("code"), shaka.get("message"), errordescription.get("user_agent")
    return None, None, None


def extract_player_state_change(data):
    return {"state": data.get("state"), "position": data.get("position")}


def extract_player_buffer_level(data):
    level = data.get("level") or {}
    return {
        "bufferlevel_cur": level.get("cur"),
        "bufferlevel_avg": level.get("avg"),
        "bufferlevel_min": level.get("min"),
        "bufferlevel_max": level.get("max"),
        "position": data.get("position"),
        "numsegments": data.get("numsegments"),
    }


def extract_player_session_event(data):
    meta = data.get("contentmetadata") or {}
    return {
        "eventtype": data.get("eventtype"),
        "content_id": meta.get("contentid"),
        "content_type": meta.get("contenttype"),
        "content_source": meta.get("contentsource"),
        "content_title": meta.get("contenttitle"),
        "content_genre": meta.get("contentgenre"),
        "content_subgenre": meta.get("contentsubgenre"),
        "resolution_quality": meta.get("resolutionquality"),
        "user_entitlements": data.get("userentitlements"),
        "result": data.get("result"),
    }


def extract_player_seek(data):
    return {"previous_position": data.get("previousposition"), "position": data.get("position")}


def extract_player_position(data):
    return {"position": data.get("position")}


def extract_player_error(data):
    errordescription = data.get("errordescription")
    shaka_code, shaka_msg, user_agent = _shaka_error_info(errordescription)
    return {
        "errorcode": data.get("errorcode"),
        "error_text": _human_error_text(errordescription),
        "shaka_code": shaka_code,
        "shaka_message": shaka_msg,
        "user_agent": user_agent,
        "position": data.get("position"),
    }


def extract_player_eof(data):
    return {"position": data.get("position")}


def extract_action_screen_change(data):
    return {
        "screen_name": data.get("screenname", data.get("currentscreen", data.get("screen"))),
        "eventtype": data.get("eventtype"),
    }


def extract_action_playback_request(data):
    return {"content_id": data.get("contentid")}


def extract_app_keepalive(data):
    return {"current_screen": data.get("currentscreen")}


def extract_app_state_change(data):
    return {"state": data.get("state")}


def extract_app_discovery(data):
    info = data.get("deviceinfo") or {}
    return {
        "device_class": data.get("deviceclass"),
        "app_version": data.get("appversion"),
        "device_name": info.get("name"),
        "device_os": info.get("os"),
        "country_code": data.get("countrycode"),
        "is_registered": data.get("isregistered"),
    }


def extract_player_track_change(data):
    return {
        "track_type": data.get("type"),
        "bitrate": data.get("bitrate"),
        "resolution": data.get("resolution"),
        "framerate": data.get("framerate"),
        "codecs": data.get("codecs"),
        "position": data.get("position"),
    }


def extract_player_settings(data):
    settings = data.get("settings") or {}
    quality = settings.get("playbackquality") or {}
    return {
        "position": data.get("position"),
        "audio_track": settings.get("audiotrack"),
        "subtitle_track": settings.get("subtitletrack"),
        "speed": settings.get("speed"),
        "quality_resolution": (quality.get("resolution") or {}).get("max"),
        "quality_bitrate": (quality.get("bitrate") or {}).get("max"),
    }


def extract_action_select(data):
    swimlane = data.get("swimlane") or {}
    return {
        "screen_id": data.get("screenid"),
        "content_id": data.get("contentid"),
        "swimlane_id": swimlane.get("id"),
        "swimlane_position": swimlane.get("position"),
    }


def extract_action_pref_update(data):
    return {"setting_id": data.get("settingid"), "setting_value": data.get("settingvalue")}


# Dispatch table -- add a new eventid here + its EXTRA_FIELDS_BY_EVENTID
# entry above when a not-yet-handled eventid shows up in real data.
_EXTRACTORS = {
    "PLAYER_STATE_CHANGE": extract_player_state_change,
    "PLAYER_BUFFER_LEVEL": extract_player_buffer_level,
    "PLAYER_SESSION_EVENT": extract_player_session_event,
    "PLAYER_SEEK": extract_player_seek,
    "PLAYER_POSITION": extract_player_position,
    "PLAYER_ERROR": extract_player_error,
    "PLAYER_EOF": extract_player_eof,
    "ACTION_SCREEN_CHANGE": extract_action_screen_change,
    "ACTION_PLAYBACK_REQUEST": extract_action_playback_request,
    "APP_KEEPALIVE": extract_app_keepalive,
    "APP_STATE_CHANGE": extract_app_state_change,
    "APP_DISCOVERY": extract_app_discovery,
    "PLAYER_TRACK_CHANGE": extract_player_track_change,
    "PLAYER_SETTINGS": extract_player_settings,
    "ACTION_SELECT": extract_action_select,
    "ACTION_PREF_UPDATE": extract_action_pref_update,
}


def flatten_row(row):
    """Flatten one `e6auj7k7_ccl_debug_events` CSV row (a dict as produced
    by `csv.DictReader`) into a single flat dict: common fields (datetime,
    device_id, household_id, eventclass, eventid, session_id) plus
    whatever eventid-specific fields `_EXTRACTORS` knows how to pull out
    of the parsed `eventdata` JSON.

    Unhandled eventids (not yet in `_EXTRACTORS`) still get the common
    fields plus the untouched `raw_eventdata` string -- nothing is
    silently dropped, matching this repo's "tolerate, don't hard-fail on
    unknown/optional shape" convention (see scripts/.github instructions).
    """
    raw_eventdata = row.get("eventdata", "")
    data = parse_eventdata(raw_eventdata)
    device_id, household_id = split_clientid(row.get("clientid"))

    flat = {
        "datetime": row.get("datetime"),
        "device_id": device_id,
        "household_id": household_id,
        "eventclass": row.get("eventclass"),
        "eventid": row.get("eventid"),
        "session_id": data.get("sessionid"),
        "raw_eventdata": raw_eventdata,
    }

    extractor = _EXTRACTORS.get(row.get("eventid"))
    if extractor:
        flat.update(extractor(data))

    return flat
