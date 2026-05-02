"""Sentry privacy helpers for the task worker."""

from __future__ import annotations

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
    "payment",
)


def _scrub_sensitive_mapping(payload: dict[str, Any]) -> None:
    for key, value in list(payload.items()):
        lowered_key = key.lower()
        if any(marker in lowered_key for marker in SENSITIVE_FIELD_MARKERS):
            payload[key] = "[Filtered]"
            continue

        if isinstance(value, dict):
            _scrub_sensitive_mapping(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _scrub_sensitive_mapping(item)


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
