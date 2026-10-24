"""Map a flat 3014/3015/3016 error row to a Media Playback Errors triage sub-category and priority."""
from __future__ import annotations

MSE_APPEND = "MSE append failed (3014/3015)"
REINIT = "Video decoder re-initialisation failed"
NO_DATA = "No data / source not supported"
AUDIO = "Audio decode / pipeline disconnected"
VIDEO_DECODE = "Video decode error"
UNCATEGORISED = "Uncategorised"

PRIORITY: dict[str, str] = {
    MSE_APPEND: "P3",
    REINIT: "P2",
    NO_DATA: "P2",
    AUDIO: "P3",
    VIDEO_DECODE: "P1",
    UNCATEGORISED: "P?",
}


def classify(row: dict) -> str:
    """First matching rule wins; rows matching nothing are "Uncategorised", never dropped."""
    code = (row.get("errorcode") or "").strip()
    status = (row.get("pipeline_status") or "").strip()
    media_type = (row.get("media_error_type") or "").strip()
    low = status.lower()
    if code in ("3014", "3015"):
        return MSE_APPEND
    if "reinitialization failed" in low:
        return REINIT
    if media_type == "4" and not status:
        return NO_DATA
    if "audio" in low or "disconnected" in low:
        return AUDIO
    if "decode" in low:
        return VIDEO_DECODE
    return UNCATEGORISED
