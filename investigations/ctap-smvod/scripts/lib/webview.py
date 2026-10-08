"""Android WebView detection shared by the ctap-smvod analysis and report scripts."""
from __future__ import annotations

import re

WV_TOKEN_RE = re.compile(r";\s*wv\b", re.IGNORECASE)


def is_wv(row: dict) -> bool | None:
    """True/False whether the session ran in an Android WebView; None when no user agent is available.

    Keyed on ``raw_user_agent`` and the parsed ``Platform`` column (either carrying the
    ``; wv`` token counts), so a missing user agent is never reported as non-wv.
    """
    values = [(row.get(k) or "").strip() for k in ("raw_user_agent", "Platform")]
    values = [v for v in values if v]
    if not values:
        return None
    return any(WV_TOKEN_RE.search(v) for v in values)


def is_wv_cell(row: dict) -> str:
    """Report-cell form of :func:`is_wv`: "true", "false", or "" when unknown."""
    value = is_wv(row)
    return "" if value is None else str(value).lower()
