"""Parse a browser/WebView ``user_agent`` string into OS, device, build and Chrome fields."""
from __future__ import annotations

import re

ANDROID_VERSION_RE = re.compile(r"Android\s+([\d.]+)")
DEVICE_MODEL_RE = re.compile(r"Android\s+[\d.]+;\s*([^;]+?)\s+Build/")
# Chrome's User-Agent Reduction drops "Build/" and reduces the model to a bare token, e.g. "Android 10; K)".
DEVICE_MODEL_NO_BUILD_RE = re.compile(r"Android\s+[\d.]+;\s*([^;)]+?)\)")
BUILD_ID_RE = re.compile(r"Build/([^;)]+)")
CHROME_VERSION_RE = re.compile(r"Chrome/([\d.]+)")
WEBVIEW_RE = re.compile(r";\s*wv\)")
WINDOWS_RE = re.compile(r"Windows NT ([\d.]+)")
MACOS_RE = re.compile(r"Mac OS X ([\d_]+)")
IOS_RE = re.compile(r"(?:iPhone|iPad|iPod).*?CPU (?:iPhone )?OS ([\d_]+)")
LINUX_DESKTOP_RE = re.compile(r"X11; Linux")

SHAPE_ANDROID_BUILD = "android_build"
SHAPE_ANDROID_REDUCED = "android_reduced"
SHAPE_DESKTOP = "desktop"
SHAPE_UNPARSED = "unparsed"


def is_webview(ua: str | None) -> bool:
    """True when the user agent carries the Android WebView ``; wv)`` token."""
    return bool(ua) and bool(WEBVIEW_RE.search(ua))


def _result(os_name: str, os_version: str, device_model: str, build_id: str, chrome_version: str,
            webview: bool, ua_shape: str) -> dict:
    return {
        "os_name": os_name,
        "os_version": os_version,
        "device_model": device_model,
        "build_id": build_id,
        "chrome_version": chrome_version,
        "is_webview": webview,
        "ua_shape": ua_shape,
    }


def parse_user_agent(ua: str | None) -> dict:
    """Extract os_name, os_version, device_model, build_id, chrome_version, is_webview and ua_shape.

    Fields default to '' / False when the UA matches no known shape (never raises). ``ua_shape`` is
    ``android_build`` (model + Build/ id present), ``android_reduced`` (Android without Build/, model
    masked or bare), ``desktop`` (Windows/macOS/Linux/iOS) or ``unparsed``.
    """
    if not ua:
        return _result("", "", "", "", "", False, SHAPE_UNPARSED)

    chrome_match = CHROME_VERSION_RE.search(ua)
    chrome_version = chrome_match.group(1) if chrome_match else ""

    android_match = ANDROID_VERSION_RE.search(ua)
    if android_match:
        device_match = DEVICE_MODEL_RE.search(ua)
        build_match = BUILD_ID_RE.search(ua)
        raw_model = device_match.group(1) if device_match else ""
        if not raw_model:
            fallback_match = DEVICE_MODEL_NO_BUILD_RE.search(ua)
            raw_model = fallback_match.group(1) if fallback_match else ""
        # "K" is Chrome's UA-reduction mask; keep it distinct from a genuinely unparsed UA.
        device_model = "K (device masked - UA reduction)" if raw_model == "K" else raw_model
        shape = SHAPE_ANDROID_BUILD if build_match else SHAPE_ANDROID_REDUCED
        return _result("Android", android_match.group(1), device_model,
                       build_match.group(1) if build_match else "", chrome_version, is_webview(ua), shape)

    for regex, os_name, model, clean_version in (
        (WINDOWS_RE, "Windows", "Desktop (Windows)", False),
        (MACOS_RE, "macOS", "Desktop (macOS)", True),
        (IOS_RE, "iOS", "iPhone/iPad", True),
    ):
        match = regex.search(ua)
        if match:
            version = match.group(1).replace("_", ".") if clean_version else match.group(1)
            return _result(os_name, version, model, "", chrome_version, False, SHAPE_DESKTOP)

    if LINUX_DESKTOP_RE.search(ua):
        return _result("Linux", "", "Desktop (Linux)", "", chrome_version, False, SHAPE_DESKTOP)

    return _result("Other/unparsed", "", "(unparsed)", "", chrome_version, False, SHAPE_UNPARSED)
