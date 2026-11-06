"""Stream a large HAR and emit a CSV timeline of identity fields (HHID, deviceId, clientId, sub...).

Tokens/cookies are never written out: JWTs are decoded (claims only) and values for identity keys are
taken from URL query, JSON request/response bodies and JWT claims. Media segments are skipped.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlsplit

import ijson

ID_KEYS = {
    "householdid", "hhid", "deviceid", "clientid", "sub", "userid", "accountid",
    "tenantid", "applicationid", "granttype", "flowtype", "loghouseholdid",
}
HEADER_ALLOW = {"x-syna-deviceid", "x-syna-householdid", "x-syna-clientid"}
MEDIA_RE = re.compile(r"\.(m4s|mp4|ts|jpg|jpeg|png|webp|svg|css|woff2?|js|ico)(\?|$)", re.I)
JWT_RE = re.compile(r"^[\w-]+\.[\w-]+\.[\w-]*$")
FIELDS = ["idx", "started", "method", "status", "host", "path", "source", "key", "value"]


def norm(key: str) -> str:
    """Lowercase and drop `_`/`-` so `client_id`, `clientId` and `client-id` compare equal."""
    return key.lower().replace("_", "").replace("-", "")


def decode_jwt_claims(token: str) -> dict[str, Any]:
    """Return JWT payload claims, or {} if the token is not a decodable JWT."""
    token = token.removeprefix("Bearer ").strip()
    if not JWT_RE.match(token):
        return {}
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def walk_identity(obj: Any, prefix: str = "") -> Iterator[tuple[str, str]]:
    """Yield (dotted key, value) for scalar values whose key name is an identity key."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, (dict, list)):
                yield from walk_identity(val, path)
            elif norm(key) in ID_KEYS and val not in (None, ""):
                yield path, str(val)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_identity(item, prefix)


def _json_or_none(text: str | None) -> Any:
    if not text or not text.lstrip().startswith(("{", "[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def entry_rows(idx: int, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure: turn one HAR entry into identity rows (empty list if nothing identity-related)."""
    req, resp = entry["request"], entry["response"]
    url = req["url"]
    if MEDIA_RE.search(url.split("#")[0]):
        return []
    parts = urlsplit(url)
    host, path = parts.netloc, parts.path if parts.scheme in ("http", "https", "ws", "wss") else ""
    base = {"idx": idx, "started": entry.get("startedDateTime", ""), "method": req["method"],
            "status": resp["status"], "host": host, "path": path}
    hits: list[tuple[str, str, str]] = []
    for q in req.get("queryString", []):
        if norm(q["name"]) in ID_KEYS:
            hits.append(("query", q["name"], q["value"]))
    for h in req.get("headers", []):
        name = h["name"].lower()
        if name == "authorization":
            hits += [("jwt-claim", k, str(v)) for k, v in decode_jwt_claims(h["value"]).items()
                     if norm(k) in ID_KEYS]
        elif norm(name) in ID_KEYS or name in HEADER_ALLOW:
            hits.append(("req-header", h["name"], h["value"]))
        elif name == "x-syna-sessionobject":
            hits.append(("req-header", h["name"], "<present>"))
    post = req.get("postData") or {}
    body = _json_or_none(post.get("text"))
    form = post.get("params") or [{"name": k, "value": v} for k, v in parse_qsl(post.get("text") or "")]
    hits += [("req-body", p["name"], p.get("value", "")) for p in form if norm(p["name"]) in ID_KEYS]
    hits += [("req-body", k, v) for k, v in walk_identity(body)]
    resp_text = (resp.get("content") or {}).get("text")
    resp_json = _json_or_none(resp_text)
    hits += [("resp-body", k, v) for k, v in walk_identity(resp_json)]
    if isinstance(resp_json, dict):
        for k, v in resp_json.items():
            if k in ("id_token", "access_token") and isinstance(v, str):
                hits += [("resp-jwt-claim", ck, str(cv)) for ck, cv in decode_jwt_claims(v).items()
                         if norm(ck) in ID_KEYS]
    return [{**base, "source": s, "key": k, "value": v} for s, k, v in hits]


def stream_rows(har_path: Path, host_filter: str | None) -> Iterator[dict[str, Any]]:
    with har_path.open("rb") as fh:
        for idx, entry in enumerate(ijson.items(fh, "log.entries.item", use_float=True)):
            if host_filter and host_filter not in entry["request"]["url"]:
                continue
            yield from entry_rows(idx, entry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--har", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--host-contains", default=None, help="only entries whose URL contains this")
    args = parser.parse_args(argv)
    if not args.har.is_file():
        print(f"HAR not found: {args.har}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for row in stream_rows(args.har, args.host_contains):
            writer.writerow(row)
            count += 1
    print(f"wrote {count} identity rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
