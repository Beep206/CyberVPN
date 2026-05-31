from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-observability-secret",
    "x-telegram-bot-api-secret-token",
}
SENSITIVE_FIELD_MARKERS = (
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "jwt",
    "payload",
    "config",
    "certificate",
    "private_key",
    "wireguard",
    "vless",
    "vmess",
    "remnawave",
    "openbao",
    "opentofu",
    "nats",
    "payment",
    "oauth",
    "totp",
    "initdata",
    "init_data",
    "tgwebappdata",
    "telegram_hash",
    "init_data_hash",
    "checkout",
    "invoice",
)
SENSITIVE_STRING_PATTERNS = (
    re.compile(r"\b(?:vless|vmess|trojan|wireguard|ss)://", re.IGNORECASE),
    re.compile(
        r"(?:access[_-]?token|refresh[_-]?token|id[_-]?token|auth[_-]?code|otp|totp|secret|password|telegram[_-]?init[_-]?data|initdata|tgWebAppData)=",
        re.IGNORECASE,
    ),
    re.compile(
        r"/api/v1/(?:vpn|xray|provisioning|subscriptions?)/(?:config|credentials|subscription)",
        re.IGNORECASE,
    ),
)


def _scrub_sensitive_value(value: Any) -> Any:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in SENSITIVE_STRING_PATTERNS):
            return "[Filtered]"
        return value

    if isinstance(value, dict):
        _scrub_sensitive_mapping(value)
        return value

    if isinstance(value, list):
        return [_scrub_sensitive_value(item) for item in value]

    return value


def _scrub_sensitive_mapping(payload: dict[str, Any]) -> None:
    for key, value in list(payload.items()):
        lowered_key = key.lower()
        if any(marker in lowered_key for marker in SENSITIVE_FIELD_MARKERS):
            payload[key] = "[Filtered]"
            continue

        payload[key] = _scrub_sensitive_value(value)


def _scrub_request_headers(headers: Any) -> None:
    if not isinstance(headers, dict):
        return

    for header_name in list(headers):
        if header_name.lower() in SENSITIVE_HEADER_NAMES:
            headers[header_name] = "[Filtered]"


def _strip_url_query(url: Any) -> Any:
    if not isinstance(url, str) or not url:
        return url

    parsed = urlparse(url)
    if not parsed.scheme and not parsed.netloc:
        return parsed.path or "/"

    sanitized = parsed._replace(query="", fragment="")
    return sanitized.geturl()


def before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        _scrub_request_headers(request.get("headers"))
        request["url"] = _strip_url_query(request.get("url"))
        if "data" in request:
            request["data"] = "[Filtered]"
        if "cookies" in request:
            request["cookies"] = "[Filtered]"

    user = event.get("user")
    if isinstance(user, dict):
        for key in ("ip_address", "email", "username"):
            user.pop(key, None)

    for section_name in ("extra", "contexts"):
        section = event.get(section_name)
        if isinstance(section, dict):
            _scrub_sensitive_mapping(section)

    return event


def before_send_transaction(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        request["url"] = _strip_url_query(request.get("url"))
        url = request.get("url")
        if isinstance(url, str):
            path = urlparse(url).path or url
            if path in {"/health", "/metrics"}:
                return None

    return event
