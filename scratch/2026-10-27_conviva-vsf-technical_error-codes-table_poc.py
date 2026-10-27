"""POC: extended VSF-T error codes table (share of attempts, impacted households, timing).

Purpose: for each error code seen before start in VSF-T sessions, print markdown rows with sessions,
% of VSF-T, % of attempts, impacted households, % of all households, sessions per household and the
first/last failure time (UTC). A session with several codes counts under each code.

Args:
    --tenant  Tenant identifier.
    --date    Date (YYYY-MM-DD).
    --top     Number of codes (default 10).
"""
import argparse
import importlib.util
from collections import defaultdict
from pathlib import Path


def load_poc():
    spec = importlib.util.spec_from_file_location("poc", Path(__file__).with_name("2026-10-27_conviva-vsf-technical_timeseries_poc.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def code_rows(tech: dict, households: dict[str, str], attempts: set, top: int) -> tuple[list[list[str]], int, int]:
    """(rows, distinct attempt households, VSF-T sessions without a household)."""
    by_code: dict[str, list[str]] = defaultdict(list)
    for sid, (_, codes) in tech.items():
        for c in set(codes):
            by_code[c].append(sid)
    all_hh = {households[s] for s in attempts if households.get(s)}
    if not all_hh:
        raise SystemExit("no householdId found for any attempt (check session.csv)")
    rows = []
    for code, sids in sorted(by_code.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:top]:
        hh_sids = [s for s in sids if households.get(s)]
        hh = {households[s] for s in hh_sids}
        per_hh = f"{len(hh_sids) / len(hh):.1f}" if hh else "n/a"
        times = [tech[s][0] for s in sids]
        rows.append([
            code, f"{len(sids):,}", f"{len(sids) / len(tech):.1%}", f"{len(sids) / len(attempts):.2%}",
            f"{len(hh):,}", f"{len(hh) / len(all_hh):.2%}", per_hh,
            f"{min(times):%H:%M}", f"{max(times):%H:%M}",
        ])
    return rows, len(all_hh), sum(1 for s in tech if not households.get(s))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    if args.top < 1:
        ap.error("--top must be >= 1")

    poc = load_poc()
    athena = poc.DATA / "athena" / args.tenant
    sessions = poc.read_sessions(athena / f"{args.date}_debug_all_events.csv")
    attempts = {s for s, ev in sessions.items() if (t := poc.create_time(ev)) and t.date().isoformat() == args.date}
    tech = {s: f for s in attempts if (f := poc.start_failure(sessions[s]))}
    if not tech:
        raise SystemExit("no VSF-T sessions found")
    content = poc.read_content_by_session(athena / f"{args.date}_session.csv")
    households = {s: content.get(s, ("", ""))[1] for s in attempts}

    rows, all_hh, no_hh = code_rows(tech, households, attempts, args.top)
    print(f"attempts={len(attempts)} VSF-T={len(tech)} all_households={all_hh} vsft_without_household={no_hh}")
    for r in rows:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
