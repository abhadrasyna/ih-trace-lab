#!/usr/bin/env python3
"""List content titles for error sessions whose device reported a codec as supported (e.g. ec-3 = true).

The flattened PLAYER_ERROR eventdata (`flatten_error_eventdata.py`) carries a device capability probe in
`raw_eventdata` (`"audio/mp4; codecs=\\"ec-3\\"":true|false`). This says whether the *device* supports the codec,
not which codec the content uses. The content title is joined by sessionId from every
`output/<TENANT>/*_setupsession_with_outcome.csv`; unmatched sessions are labelled `(unmatched)`.

Usage:
    python3 find_codec_support_content.py --from 2026-10-08 --to 2026-10-11 --tenant SA --codec ec-3
"""
import argparse
import csv as std_csv
import logging
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from lib import csv_io_compat as csv
from lib.bootstrap import REPO_ROOT  # noqa: F401  # import side effect: sys.path bootstrap
from src.lib.logging.bootstrap import init_logging

LOGGER = logging.getLogger("investigations.ctap_smvod.scripts.find_codec_support_content")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def supported_mimes(raw_eventdata: str, codec: str, value: str = "true") -> list[str]:
    """Pure: mime types whose `codecs=\\"<codec>\\"` probe equals `value` in the raw eventdata text."""
    pattern = re.compile(rf'"([a-z]+/[\w.+-]+); codecs=\\+"{re.escape(codec)}\\+"":\s*{value}')
    return sorted(set(pattern.findall(raw_eventdata)))


def session_info(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Pure: sessionId -> content/position_not_moved/playback_outcome (first row with a title wins)."""
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        title = (r.get("content") or "").strip()
        if title and r.get("sessionId"):
            out.setdefault(r["sessionId"], {"content": title, "position_not_moved": r.get("position_not_moved", ""),
                                            "playback_outcome": r.get("playback_outcome", "")})
    return out


def probe_state(raw_eventdata: str, codec: str) -> str:
    """Pure: 'true' if any mime probe for `codec` is true, 'false' if probes exist but none true, else 'absent'."""
    if supported_mimes(raw_eventdata, codec, "true"):
        return "true"
    return "false" if supported_mimes(raw_eventdata, codec, "false") else "absent"


def split_by_probe(flat_rows: list[dict[str, str]], info: dict[str, dict[str, str]], codec: str) -> list[list[str]]:
    """Pure: rows [errorcode, content, true_sessions, true_position_moved, false_sessions, false_position_moved].

    A session counts once per (errorcode, content) and as `true` if any of its rows probes true. `position_moved`
    counts sessions whose `position_not_moved` is exactly 'false' (blank = unknown, not counted).
    """
    state: dict[tuple[str, str], str] = {}
    for r in flat_rows:
        s = probe_state(r.get("raw_eventdata") or "", codec)
        key = (r["errorcode"], r["sessionId"])
        if s == "true" or (s == "false" and key not in state):
            state[key] = s
    agg: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for (code, sid), s in state.items():
        meta = info.get(sid, {})
        slot = agg[(code, meta.get("content", "(unmatched)"))]
        off = 0 if s == "true" else 2
        slot[off] += 1
        slot[off + 1] += meta.get("position_not_moved") == "false"
    return [[c, t, *map(str, v)] for (c, t), v in sorted(agg.items(), key=lambda kv: (kv[0][0], -kv[1][0], kv[0][1]))]


def match_sessions(flat_rows: list[dict[str, str]], codec: str, value: str) -> list[dict[str, str]]:
    """Pure: flat rows whose probe matches, each with a `mimes` field."""
    hits = []
    for r in flat_rows:
        mimes = supported_mimes(r.get("raw_eventdata") or "", codec, value)
        if mimes:
            hits.append({**r, "mimes": "|".join(mimes)})
    return hits


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    init_logging("ctap-smvod-find_codec_support_content")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    ap.add_argument("--tenant", default="SA")
    ap.add_argument("--codec", default="ec-3")
    ap.add_argument("--value", default="true", choices=["true", "false"])
    args = ap.parse_args()

    tenant_dir = OUTPUT_DIR / args.tenant
    flat_files = [p for p in sorted((tenant_dir / "error_eventdata_flat").glob("*_all.csv"))
                  if args.start <= date.fromisoformat(p.name[:10]) <= args.end]
    if not flat_files:
        raise FileNotFoundError(f"no flattened *_all.csv for {args.tenant} in {args.start}..{args.end}")
    info: dict[str, dict[str, str]] = {}
    for p in sorted(tenant_dir.glob("*_setupsession_with_outcome.csv")):
        for sid, meta in session_info(read_csv(p)).items():
            info.setdefault(sid, meta)
    sessions = {sid: m["content"] for sid, m in info.items()}

    rows_out = []
    all_flat: list[dict[str, str]] = []
    for p in flat_files:
        flat = read_csv(p)
        all_flat.extend(flat)
        for r in match_sessions(flat, args.codec, args.value):
            meta = info.get(r["sessionId"], {})
            rows_out.append([p.name[:10], r["sessionId"], r["householdId"], r["deviceId"], r["errorcode"], r["mimes"],
                             sessions.get(r["sessionId"], "(unmatched)"), meta.get("position_not_moved", ""),
                             meta.get("playback_outcome", "")])
    stem = tenant_dir / f"{args.start}_{args.end}_{args.codec}_{args.value}_by_content"
    with open(f"{stem}_sessions.csv", "w", newline="", encoding="utf-8") as fh:
        w = std_csv.writer(fh)
        w.writerow(["date", "sessionId", "householdId", "deviceId", "errorcode", "mimes", "content", "position_not_moved", "playback_outcome"])
        w.writerows(rows_out)
    with open(f"{stem}_split.csv", "w", newline="", encoding="utf-8") as fh:
        w = std_csv.writer(fh)
        w.writerow(["errorcode", "content", f"{args.codec}_true_sessions", f"{args.codec}_true_position_moved",
                    f"{args.codec}_false_sessions", f"{args.codec}_false_position_moved"])
        w.writerows(split_by_probe(all_flat, info, args.codec))
    sessions_by_content: dict[str, set[str]] = defaultdict(set)
    households: dict[str, set[str]] = defaultdict(set)
    for r in rows_out:
        sessions_by_content[r[6]].add(r[1])
        households[r[6]].add(r[2])
    with open(f"{stem}.csv", "w", newline="", encoding="utf-8") as fh:
        w = std_csv.writer(fh)
        w.writerow(["content", "sessions", "unique_households"])
        for content, sids in sorted(sessions_by_content.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            w.writerow([content, len(sids), len(households[content])])
    LOGGER.info("%s: %d matching rows over %d flat files -> %s(.csv|_sessions.csv|_split.csv)", args.tenant, len(rows_out),
                len(flat_files), stem)


if __name__ == "__main__":
    main()
