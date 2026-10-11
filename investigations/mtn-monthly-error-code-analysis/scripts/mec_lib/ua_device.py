"""User-agent device parsing for error events.

``UA_RE`` is the same pattern as ``investigations/ctap-smvod/scripts/analyze_webview_devices.py``; that
module cannot be imported from here without clashing on its own ``lib`` package, so the pattern is kept
in step by hand (the parity is covered by a test on a real-shaped UA).
"""
from __future__ import annotations

import re

UA_RE = re.compile(r"Android\s+(?P<android>[\d.]+);\s*(?P<model>.+?)\s+Build/(?P<build>[^;]+)")
FAMILIES = (
    ("Android", "android"),
    ("iOS", "iphone|ipad|ipod"),
    ("Windows", "windows nt"),
    ("macOS", "macintosh|mac os x"),
    ("Linux", "linux|x11"),
)


def parse_device(user_agent: str) -> tuple[str, str, str]:
    """Return ``(device_model, android_version, build_id)``; blanks when the UA has no Android build segment."""
    match = UA_RE.search(user_agent or "")
    if not match:
        return "", "", ""
    return match.group("model"), match.group("android"), match.group("build")


def ua_family(user_agent: str) -> str:
    """Coarse OS family of a user agent; ``(blank)`` for an empty one and ``Other`` when nothing matches."""
    ua = (user_agent or "").strip()
    if not ua:
        return "(blank)"
    for name, pattern in FAMILIES:
        if re.search(pattern, ua, re.IGNORECASE):
            return name
    return "Other"
