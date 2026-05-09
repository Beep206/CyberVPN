"""Sentry privacy helpers for the task worker."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_FIELD_MARKERS = (
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "jwt",
    "payload",
    "config",
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


def before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    user = event.get("user")
    if isinstance(user, dict):
        for key in ("ip_address", "email", "username"):
            user.pop(key, None)

    for section_name in ("extra", "contexts"):
        section = event.get(section_name)
        if isinstance(section, dict):
            _scrub_sensitive_mapping(section)

    return event
