"""Safe evidence redaction helpers for VPN Tester."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEY_PARTS = (
    "access_token",
    "authorization",
    "cookie",
    "jwt",
    "key",
    "password",
    "private",
    "secret",
    "short_uuid",
    "subscription_url",
    "token",
    "user_uuid",
    "uuid",
)

UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
URL_RE = re.compile(r"\b(?:https?|vless|vmess|trojan|ss)://[^\s]+", re.IGNORECASE)
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{28,}\b")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redacted_digest(value: str) -> dict[str, str | bool]:
    return {"redacted": True, "sha256": sha256_text(value)}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_evidence(value: Any, *, parent_key: str = "") -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, str):
        if (
            _is_sensitive_key(parent_key)
            or UUID_RE.search(value)
            or URL_RE.search(value)
            or LONG_TOKEN_RE.search(value)
        ):
            return _redacted_digest(value)
        return value

    if isinstance(value, Mapping):
        return {
            str(key): _redacted_digest(str(item))
            if _is_sensitive_key(str(key))
            else redact_evidence(item, parent_key=str(key))
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | str):
        return [redact_evidence(item, parent_key=parent_key) for item in value]

    return str(value)


def safe_artifact_preview(value: Any) -> tuple[dict[str, Any], str]:
    redacted = redact_evidence(value)
    if not isinstance(redacted, dict):
        redacted = {"value": redacted}
    digest = sha256_text(repr(redacted))
    return redacted, digest
