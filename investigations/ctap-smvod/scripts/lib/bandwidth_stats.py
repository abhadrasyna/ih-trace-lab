"""Pure statistics for the bandwidth-vs-playback-failure analysis (no file or network I/O).

Rows are dicts as read from `<date>_session_bandwidth.csv` (`run_athena_session_bandwidth.py`); empty strings mean "not logged".
"""
import math
from typing import Iterable, Mapping, Sequence

MIN_N = 5
BUFFERING_STALL_THRESHOLD = 3
ABR_BUCKETS_MBPS = ((0.0, 1.0, "<1"), (1.0, 3.0, "1-3"), (3.0, 6.0, "3-6"), (6.0, math.inf, ">=6"))


def num(value: str | None) -> float | None:
    """Pure: '' / None -> None, otherwise float; raises ValueError on a non-numeric value so bad input fails loudly."""
    text = (value or "").strip()
    return float(text) if text else None


def is_true(value: str | None) -> bool:
    text = (value or "").strip().lower()
    if text not in {"true", "false", ""}:
        raise ValueError(f"expected true/false, got {value!r}")
    return text == "true"


def percentile(values: Sequence[float], q: float) -> float | None:
    """Pure: linear-interpolated percentile (q in 0..100); None for an empty input."""
    if not values:
        return None
    if not 0 <= q <= 100:
        raise ValueError(f"q must be in 0..100, got {q}")
    s = sorted(values)
    pos = (len(s) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def ranks(values: Sequence[float]) -> list[float]:
    """Pure: 1-based ranks with ties given the average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pure: Spearman rank correlation (-1..1); None when fewer than MIN_N pairs or either side is constant."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must be the same length")
    if len(xs) < MIN_N:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / math.sqrt(sxx * syy)


def mann_whitney(a: Sequence[float], b: Sequence[float]) -> dict[str, float] | None:
    """Pure: Mann-Whitney U test (normal approximation, tie-corrected, two-sided).

    Returns `p_value` and `prob_a_lower` (chance a random value from `a` is below one from `b`; 0.5 = no difference),
    or None when either group has fewer than MIN_N values.
    """
    n1, n2 = len(a), len(b)
    if n1 < MIN_N or n2 < MIN_N:
        return None
    pooled = list(a) + list(b)
    rk = ranks(pooled)
    u1 = sum(rk[:n1]) - n1 * (n1 + 1) / 2
    n = n1 + n2
    counts: dict[float, int] = {}
    for v in pooled:
        counts[v] = counts.get(v, 0) + 1
    tie_term = sum(c**3 - c for c in counts.values())
    var = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    if var == 0:
        return {"p_value": 1.0, "prob_a_lower": 0.5}
    z = (u1 - n1 * n2 / 2) / math.sqrt(var)
    return {"p_value": math.erfc(abs(z) / math.sqrt(2)), "prob_a_lower": 1 - u1 / (n1 * n2)}


def bandwidth(row: Mapping[str, str]) -> float | None:
    """Pure: the session's Shaka estimate in Mbps (the higher of its min/max across error events)."""
    return num(row.get("est_bw_mbps_max"))


def healthy_sessions(rows: Iterable[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Pure: sessions with no PLAYER_ERROR."""
    return [r for r in rows if not is_true(r.get("has_error"))]


def group_by_errorcode(rows: Iterable[Mapping[str, str]]) -> dict[str, list[Mapping[str, str]]]:
    """Pure: error sessions grouped by their first error code."""
    groups: dict[str, list[Mapping[str, str]]] = {}
    for r in rows:
        if is_true(r.get("has_error")):
            code = (r.get("first_errorcode") or "").strip() or "unknown"
            groups.setdefault(code, []).append(r)
    return groups


def summarize_code(rows: Sequence[Mapping[str, str]]) -> dict[str, float | int | None]:
    """Pure: one error code's session count, bandwidth coverage/spread, buffering, headroom and correlation."""
    bws = [b for b in (bandwidth(r) for r in rows) if b is not None]
    buffering = [num(r.get("buffering_events")) or 0.0 for r in rows]
    pairs = [(bandwidth(r), num(r.get("buffering_events")) or 0.0) for r in rows if bandwidth(r) is not None]
    headroom = [
        bw / sb for r in rows if (bw := bandwidth(r)) is not None and (sb := num(r.get("stream_bw_mbps")))
    ]
    p10, p50, p90 = (percentile(bws, q) for q in (10, 50, 90))
    return {
        "sessions": len(rows),
        "with_bandwidth": len(bws),
        "coverage_pct": 100 * len(bws) / len(rows) if rows else None,
        "bw_p10": p10, "bw_p50": p50, "bw_p90": p90,
        "bw_iqr": (percentile(bws, 75) - percentile(bws, 25)) if bws else None,
        "avg_buffering_events": sum(buffering) / len(buffering) if buffering else None,
        "pct_3plus_buffering": 100 * sum(1 for b in buffering if b >= BUFFERING_STALL_THRESHOLD) / len(buffering) if buffering else None,
        "spearman_bw_vs_buffering": spearman([p[0] for p in pairs], [p[1] for p in pairs]),
        "median_headroom": percentile(headroom, 50),
    }


def abr_bucket(mbps: float) -> str:
    for lo, hi, label in ABR_BUCKETS_MBPS:
        if lo <= mbps < hi:
            return label
    raise ValueError(f"negative bitrate {mbps}")


def failure_rate_by_abr_bucket(rows: Iterable[Mapping[str, str]]) -> list[dict[str, float | int | str]]:
    """Pure: per ABR-average-bitrate bucket, sessions with ABR data and the share that had an error (healthy-session proxy)."""
    tally = {label: [0, 0] for _, _, label in ABR_BUCKETS_MBPS}
    for r in rows:
        v = num(r.get("abr_bitrate_mbps_avg"))
        if v is None:
            continue
        t = tally[abr_bucket(v)]
        t[0] += 1
        t[1] += is_true(r.get("has_error"))
    return [
        {"abr_bucket_mbps": label, "sessions": t[0], "error_sessions": t[1], "error_rate_pct": 100 * t[1] / t[0] if t[0] else None}
        for label, t in tally.items()
    ]


def abr_error_vs_healthy(rows: Iterable[Mapping[str, str]]) -> dict[str, float | int | None]:
    """Pure: error vs healthy ABR bitrate (sessions with track-change data only) with a Mann-Whitney test."""
    err, ok = [], []
    for r in rows:
        v = num(r.get("abr_bitrate_mbps_avg"))
        if v is not None:
            (err if is_true(r.get("has_error")) else ok).append(v)
    test = mann_whitney(err, ok)
    return {
        "error_n": len(err), "healthy_n": len(ok),
        "error_median_mbps": percentile(err, 50), "healthy_median_mbps": percentile(ok, 50),
        "p_value": test["p_value"] if test else None,
        "prob_error_lower": test["prob_a_lower"] if test else None,
    }


def overall_bandwidth_vs_buffering(rows: Iterable[Mapping[str, str]]) -> dict[str, float | int | None]:
    """Pure: Spearman correlation of Shaka estimate vs BUFFERING events over every error session that has an estimate."""
    pairs = [(bandwidth(r), num(r.get("buffering_events")) or 0.0) for r in rows if is_true(r.get("has_error")) and bandwidth(r) is not None]
    return {"n": len(pairs), "spearman": spearman([p[0] for p in pairs], [p[1] for p in pairs])}
