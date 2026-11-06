"""Scratch POC: ctap-smvod session presence funnel (Lightstep -> mDRM -> debug -> unified) as markdown."""
import argparse
import csv
from collections import Counter
from pathlib import Path

INV = Path(__file__).resolve().parent.parent / "investigations" / "ctap-smvod"


def read(path, col):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)]


def ids(path, col):
    return {r[col] for r in read(path, col) if r.get(col)}


def parts(lightstep, date, kind, required=True):
    found = sorted(lightstep.glob(f"{date}_[0-9][0-9]_{kind}.csv"))
    if required and not found:
        raise FileNotFoundError(f"no {kind} CSVs for {date} in {lightstep}")
    return found


def mdrm_sets(lightstep, date):
    """sessionIds with an mdrmfe hit, and those whose fcid also reached LRM and a CDM export."""
    fe = [r for p in parts(lightstep, date, "mdrmfe") for r in read(p, "")]
    fc_session = {r["fcid"]: r["drmAuthToken.sessionId"] for r in fe if r.get("fcid") and r.get("drmAuthToken.sessionId")}
    lrm = {r["fcId"] for p in parts(lightstep, date, "mdrm-lrm") for r in read(p, "")}
    cdm = {r["fcId"] for k in ("widevine", "playready", "fairplay") for p in parts(lightstep, date, f"mdrm-cdm-{k}", False)
           for r in read(p, "")}
    fe_sessions = set(fc_session.values())
    chain = {s for fc, s in fc_session.items() if fc in lrm and fc in cdm}
    return fe_sessions, chain


def pct(n, d):
    return f"{n / d * 100:.1f}%" if d else "-"


def write_ids(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sessionId", "bucket", "mdrm_stage"])
        w.writerows(rows)


def state_profile(debug_path, wanted):
    """Per session: set of (eventid,state) seen in debug states, for sessions in `wanted`."""
    seen: dict[str, set] = {}
    with open(debug_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["sessionId"] in wanted:
                seen.setdefault(r["sessionId"], set()).add((r["eventid"], r["state"]))
    return seen


def state_rows(label, S, seen):
    n = len(S)
    playing = sum(1 for s in S if ("PLAYER_STATE_CHANGE", "PLAYING") in seen.get(s, set()))
    destroy = sum(1 for s in S if ("PLAYER_SESSION_EVENT", "DESTROY") in seen.get(s, set()))
    error = sum(1 for s in S if any(e == "PLAYER_ERROR" for e, _ in seen.get(s, set())))
    create_only = sum(1 for s in S if seen.get(s, set()) <= {("PLAYER_SESSION_EVENT", "CREATE")})
    return (f"| {label} | {n:,} | {playing:,} ({pct(playing, n)}) | {destroy:,} ({pct(destroy, n)}) | "
            f"{error:,} ({pct(error, n)}) | {create_only:,} ({pct(create_only, n)}) |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="ZA")
    ap.add_argument("--date", default="2026-10-24")
    a = ap.parse_args()
    ls = INV / "data" / "lightstep" / a.tenant
    at = INV / "data" / "athena" / a.tenant
    out = INV / "output" / a.tenant / "session-funnel"
    out.mkdir(parents=True, exist_ok=True)

    smvod_rows = read(ls / f"{a.date}_smvod.csv", "sessionId")
    blank = sum(1 for r in smvod_rows if not r.get("sessionId"))
    light = {r["sessionId"] for r in smvod_rows if r.get("sessionId")}
    debug = ids(at / f"{a.date}_debug_states.csv", "sessionId")
    unified = ids(at / f"{a.date}_session.csv", "sessionId")
    fe, chain = mdrm_sets(ls, a.date)

    in_both = light & debug & unified
    debug_only = (light & debug) - unified
    unified_only = (light & unified) - debug
    neither = light - debug - unified
    n = len(light)

    def stage(s):
        return "full DRM chain" if s in chain else ("mdrmfe only" if s in fe else "no DRM trace")

    buckets = [("present_in_both", in_both), ("debug_not_unified", debug_only),
               ("unified_not_debug", unified_only), ("not_observed_in_athena", neither)]
    rows = [(s, b, stage(s)) for b, S in buckets for s in sorted(S)]
    write_ids(out / f"{a.date}_session_funnel_sessions.csv", rows)
    write_ids(out / f"{a.date}_athena_only_not_in_lightstep.csv",
              [(s, "athena_not_lightstep", "") for s in sorted((unified | debug) - light)])

    md = [f"# Session funnel - {a.tenant}, {a.date} (UTC)", "",
          "Read-only POC over the local exports. \"Present in Athena\" means in BOTH `unified_sessions` and the debug states. "
          "\"Not observed\" means absent from the Athena export only; cause is not proven, and late ingestion changes the counts.", "",
          "## Funnel (sessions dropped at each stage)", "",
          "| Stage | Sessions | % of Lightstep | Dropped vs previous |", "|---|---|---|---|",
          f"| Lightstep `sm-vod` sessions (distinct `sessionId`) | {n:,} | 100.0% | - |",
          f"| In debug states | {len(light & debug):,} | {pct(len(light & debug), n)} | {n - len(light & debug):,} |",
          f"| In debug states AND `unified_sessions` | {len(in_both):,} | {pct(len(in_both), n)} | "
          f"{len(light & debug) - len(in_both):,} |", "",
          f"Lightstep rows: {len(smvod_rows):,}, of which {blank} have a blank `sessionId` (setup spans that failed before a session existed; not in the funnel).", "",
          "## Where sessions are dropped", "", "| Bucket | Sessions | % | Meaning |", "|---|---|---|---|",
          f"| present_in_both | {len(in_both):,} | {pct(len(in_both), n)} | in debug and `unified_sessions` |",
          f"| debug_not_unified | {len(debug_only):,} | {pct(len(debug_only), n)} | in debug, no `unified_sessions` row |",
          f"| unified_not_debug | {len(unified_only):,} | {pct(len(unified_only), n)} | in `unified_sessions`, not in debug |",
          f"| not_observed_in_athena | {len(neither):,} | {pct(len(neither), n)} | in neither Athena table |", "",
          "## DRM trace per bucket (mdrmfe + LRM + CDM joined by `fcid`)", "",
          "DRM content only reaches mDRM, so compare buckets with care: a low rate can mean clear content, not a failure.", "",
          "| Bucket | Sessions | Full DRM chain | mdrmfe only | No DRM trace |", "|---|---|---|---|---|"]
    for b, S in buckets:
        c = Counter(stage(s) for s in S)
        md.append(f"| {b} | {len(S):,} | {c['full DRM chain']:,} | {c['mdrmfe only']:,} | {c['no DRM trace']:,} |")
    extra = (unified | debug) - light
    md += ["", "## In Athena but not in the Lightstep export", "",
           f"{len(extra):,} sessions (debug or unified) are not in the Lightstep export: {len(unified - light):,} in `unified_sessions`, "
           f"{len(debug - light):,} in debug. Earlier analysis found most were created within 1-2 minutes of an export part boundary (06:00, 09:00, 14:00, 18:00, 24:00 UTC), "
           "suggesting an export seam gap; not re-checked here."]
    seen = state_profile(at / f"{a.date}_debug_states.csv", debug)
    md += ["", "## Debug events per bucket: is PLAYING sent for the debug-only sessions?", "",
           "Only sessions that are in the debug table (`not_observed_in_athena` has no debug rows by definition). "
           "`debug_not_unified` is the group of interest; `present_in_both` is the control.", "",
           "| Bucket | Sessions | Has PLAYING | Has DESTROY | Has PLAYER_ERROR | CREATE only |", "|---|---|---|---|---|---|",
           state_rows("present_in_both (control)", in_both, seen), state_rows("debug_not_unified", debug_only, seen), "",
           "## Files", "", f"- `{a.date}_session_funnel_sessions.csv`: every Lightstep sessionId with bucket and DRM stage.",
           f"- `{a.date}_athena_only_not_in_lightstep.csv`: sessionIds in Athena only.", ""]
    (out / f"{a.date}_session_funnel.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
