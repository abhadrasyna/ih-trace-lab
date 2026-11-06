"""Propose guest -> real device/HHID pairs for a tenant by joining ctap spans on the client IP and a time window.

There is no deterministic key linking a guest identity (random-UUID deviceId, ``sessionInfo.guestMode`` = 1) to the
identity created after login, so pairs are *candidates*: same ``http.client_ip``, the real identity first seen within
``--max-gap-minutes`` after the guest was last seen, and (when both spans carry one) the same user agent. A pair is
``unique`` only when it is the sole candidate in both directions; shared IPs (carrier NAT, offices) yield ``ambiguous``.
Read-only: queries the Lightstep public API (token from the environment / root ``.env``), never writes to Lightstep.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ENDPOINTS = {
    "eu": ("https://api.eu.lightstep.com/public/v0.2", "Synamedia-EU"),
    "us": ("https://api.lightstep.com/public/v0.2", "Synamedia"),
}
GROUP_BY = ["http.client_ip", "sessionInfo.deviceId", "sessionInfo.householdId", "sessionInfo.guestMode", "http.user_agent"]
GUEST_VALUES = {"1", "true"}
IP_BATCH = 16
FIELDS = [
    "client_ip", "guest_device", "guest_hhid", "guest_first", "guest_last", "real_device", "real_hhid", "real_first",
    "gap_s", "ua_match", "candidates", "confidence",
]


@dataclass
class Identity:
    ip: str
    device: str
    hhid: str
    is_guest: bool
    first_ms: int
    last_ms: int
    uas: set[str] = field(default_factory=set)


def _labels(series: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for label in series.get("group-labels", []):
        key, _, value = str(label).partition("=")
        out[key] = value
    return out


def parse_identities(series_list: list[dict[str, Any]]) -> list[Identity]:
    """Merge Lightstep series into one Identity per (ip, device, hhid, guest flag), with first/last non-zero point times."""
    merged: dict[tuple[str, str, str, bool], Identity] = {}
    for series in series_list:
        labels = _labels(series)
        device, hhid, ip = labels.get("sessionInfo.deviceId", ""), labels.get("sessionInfo.householdId", ""), labels.get("http.client_ip", "")
        stamps = [int(ts) for ts, value in series.get("points", []) if value]
        if not (device and ip and stamps):
            continue
        is_guest = labels.get("sessionInfo.guestMode", "").lower() in GUEST_VALUES
        ident = merged.setdefault((ip, device, hhid, is_guest), Identity(ip, device, hhid, is_guest, min(stamps), max(stamps)))
        ident.first_ms, ident.last_ms = min(ident.first_ms, min(stamps)), max(ident.last_ms, max(stamps))
        if labels.get("http.user_agent"):
            ident.uas.add(labels["http.user_agent"])
    return list(merged.values())


def _ua_match(guest: Identity, real: Identity) -> str:
    if not guest.uas or not real.uas:
        return "unknown"
    return "yes" if guest.uas & real.uas else "no"


def pair_identities(identities: list[Identity], max_gap_s: int) -> list[dict[str, Any]]:
    """Candidate guest->real pairs on the same IP where the real identity first appears 0..max_gap_s after the guest was last seen."""
    guests = [i for i in identities if i.is_guest]
    reals = [i for i in identities if not i.is_guest and i.hhid]
    pairs: list[tuple[Identity, Identity]] = []
    for guest in guests:
        for real in reals:
            gap_s = (real.first_ms - guest.last_ms) / 1000
            if guest.ip == real.ip and 0 <= gap_s <= max_gap_s:
                pairs.append((guest, real))
    rows = []
    for guest, real in pairs:
        per_guest = sum(1 for g, _ in pairs if g is guest)
        per_real = sum(1 for _, r in pairs if r is real)
        ua = _ua_match(guest, real)
        rows.append({
            "client_ip": guest.ip, "guest_device": guest.device, "guest_hhid": guest.hhid,
            "guest_first": _iso(guest.first_ms), "guest_last": _iso(guest.last_ms),
            "real_device": real.device, "real_hhid": real.hhid, "real_first": _iso(real.first_ms),
            "gap_s": round((real.first_ms - guest.last_ms) / 1000), "ua_match": ua,
            "candidates": max(per_guest, per_real), "confidence": _confidence(per_guest, per_real, ua),
        })
    return sorted(rows, key=lambda r: (r["client_ip"], r["guest_first"]))


def _confidence(per_guest: int, per_real: int, ua_match: str) -> str:
    if per_guest != 1 or per_real != 1:
        return "ambiguous"
    return "ua_mismatch" if ua_match == "no" else "unique"


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_uql(ips: list[str], tenant_filter: dict[str, str] | None) -> str:
    """UQL counting ctap spans for the given client IPs, grouped by the identity attributes."""
    ip_clause = " || ".join(f'http.client_ip == "{ip}"' for ip in ips)
    extra = ""
    for key, value in (tenant_filter or {}).items():
        if key != "sessionInfo.busUnitId":
            raise ValueError(f"Unsupported shared-project filter key: {key}")
        extra += f' && {key} == "{value}"'
    groups = ", ".join(f'"{g}"' for g in GROUP_BY)
    return f'spans count | delta | filter service == "ctap" && ({ip_clause}){extra} | group_by [{groups}], sum'


def main(argv: list[str] | None = None) -> int:
    # Imported here: the sibling `scripts` package of this investigation shadows the repo-level one at import time.
    sys.modules.pop("scripts", None)
    from scripts.lib.lightstep_api import Project, UrllibTransport, fetch_all_series, load_token
    from src.lib.logging.bootstrap import init_logging
    from src.tenant_registry import LightstepGoQueryTarget, TenantRegistry

    init_logging("propose-guest-pairs")
    logger = logging.getLogger("scripts.propose_guest_pairs")
    logger.info("Run started")
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--tenant", required=True, help="tenant code, e.g. ZA")
        parser.add_argument("--ip", required=True, action="append", help="client IP (repeatable)")
        parser.add_argument("--start", required=True, help="UTC window start, e.g. 2026-11-06T04:00:00")
        parser.add_argument("--minutes", type=int, default=30)
        parser.add_argument("--lookback-minutes", type=int, default=60, help="extra history so already-active real identities are not mistaken for new ones")
        parser.add_argument("--max-gap-minutes", type=int, default=10)
        parser.add_argument("--out", required=True, type=Path)
        args = parser.parse_args(argv)

        context = LightstepGoQueryTarget().build_context(TenantRegistry().get(args.tenant))
        region = str(context["region"]).lower()
        base_url, org = ENDPOINTS[region]
        start = datetime.fromisoformat(args.start)
        start = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start.astimezone(timezone.utc)
        oldest = start - timedelta(minutes=args.lookback_minutes)
        youngest = start + timedelta(minutes=args.minutes)
        series: list[dict[str, Any]] = []
        for i in range(0, len(args.ip), IP_BATCH):
            series += fetch_all_series(
                UrllibTransport(), project=Project(base_url, org, str(context["project"])), token=load_token(region),
                uql=build_uql(args.ip[i:i + IP_BATCH], context.get("filter")), oldest=oldest, youngest=youngest,
                output_period=60,
            )
        rows = pair_identities(parse_identities(series), args.max_gap_minutes * 60)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        unique = sum(r["confidence"] == "unique" for r in rows)
        print(f"{len(rows)} candidate pair(s), {unique} unique -> {args.out}")
        return 0
    finally:
        logger.info("Run finished")


if __name__ == "__main__":
    raise SystemExit(main())
