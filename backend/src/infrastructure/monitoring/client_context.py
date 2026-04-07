"""Low-cardinality client context helpers for auth observability."""

from __future__ import annotations

from dataclasses import dataclass

CLIENT_TYPES = ("desktop", "mobile", "tablet", "bot", "unknown")
OS_FAMILIES = ("windows", "macos", "linux", "android", "ios", "other", "unknown")
CLIENT_APPS = ("chrome", "safari", "firefox", "edge", "telegram_webview", "mobile_app", "other", "unknown")
LOCKOUT_TIERS = ("none", "tier_1_30s", "tier_2_5m", "tier_3_30m", "permanent")
RISK_LEVELS = ("low", "medium", "high", "critical", "unknown")
VERIFICATION_STATES = ("verified", "unverified")
MOBILE_DEVICE_PLATFORMS = ("ios", "android", "unknown")


@dataclass(frozen=True)
class AuthClientContext:
    """Normalized auth client context with bounded label values."""

    client_type: str = "unknown"
    os_family: str = "unknown"
    client_app: str = "unknown"


def _normalize_known(value: str | None, allowed: tuple[str, ...], fallback: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in allowed:
        return normalized
    return fallback


def resolve_web_client_context(user_agent: str | None, sec_ch_ua_mobile: str | None = None) -> AuthClientContext:
    """Resolve client context for browser-based auth flows."""
    ua = (user_agent or "").lower()
    mobile_hint = (sec_ch_ua_mobile or "").strip().lower()

    if not ua:
        return AuthClientContext()

    if any(token in ua for token in ("bot", "crawler", "spider", "headless", "python-httpx", "curl/")):
        return AuthClientContext(client_type="bot", os_family="other", client_app="other")

    os_family = "other"
    if "android" in ua:
        os_family = "android"
    elif any(token in ua for token in ("iphone", "ipad", "ios", "cfnetwork", "darwin")):
        os_family = "ios"
    elif "windows" in ua:
        os_family = "windows"
    elif any(token in ua for token in ("mac os x", "macintosh")):
        os_family = "macos"
    elif any(token in ua for token in ("linux", "x11")):
        os_family = "linux"

    client_app = "other"
    if "telegram" in ua:
        client_app = "telegram_webview"
    elif "edg/" in ua or "edge/" in ua:
        client_app = "edge"
    elif "firefox/" in ua:
        client_app = "firefox"
    elif "chrome/" in ua or "crios/" in ua:
        client_app = "chrome"
    elif "safari/" in ua:
        client_app = "safari"

    client_type = "desktop"
    if any(token in ua for token in ("ipad", "tablet")):
        client_type = "tablet"
    elif mobile_hint == "?1" or any(token in ua for token in ("mobile", "iphone", "ipod")):
        client_type = "mobile"
    elif "android" in ua:
        client_type = "tablet" if "mobile" not in ua else "mobile"
    elif "telegram" in ua and any(token in ua for token in ("iphone", "android", "mobile")):
        client_type = "mobile"

    return AuthClientContext(client_type=client_type, os_family=os_family, client_app=client_app)


def resolve_mobile_client_context(platform: str | None) -> AuthClientContext:
    """Resolve client context for mobile API flows."""
    normalized_platform = _normalize_known(platform, MOBILE_DEVICE_PLATFORMS[:-1], "unknown")
    return AuthClientContext(
        client_type="mobile",
        os_family=normalized_platform if normalized_platform != "unknown" else "unknown",
        client_app="mobile_app",
    )

