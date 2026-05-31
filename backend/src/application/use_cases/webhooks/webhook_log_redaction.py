"""Retention-safe webhook log payload builders."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

WEBHOOK_LOG_PAYLOAD_SCHEMA = "webhook_log.redacted.v1"

_LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")


def signature_fingerprint(signature: str | None) -> str | None:
    """Return a non-replayable fingerprint for a webhook signature header."""
    return _fingerprint(signature)


def build_cryptobot_webhook_log_payload(
    payload: Mapping[str, Any],
    *,
    signature: str | None,
    is_valid: bool,
) -> dict[str, Any]:
    """Build allowlisted CryptoBot metadata for persistent webhook logs."""
    invoice = _as_mapping(payload.get("payload"))
    return _drop_none(
        {
            "schema": WEBHOOK_LOG_PAYLOAD_SCHEMA,
            "source": "cryptobot",
            "event_type": _safe_label(payload.get("update_type")),
            "event_id_fingerprint": _fingerprint(payload.get("update_id")),
            "invoice_id_fingerprint": _fingerprint(invoice.get("invoice_id")),
            "status": _safe_label(invoice.get("status"), max_length=40),
            "signature_present": bool(signature),
            "validation_status": _validation_status(is_valid),
        }
    )


def build_remnawave_webhook_log_payload(
    payload: Mapping[str, Any],
    *,
    signature: str | None,
    is_valid: bool,
    validation_reason: str | None,
) -> dict[str, Any]:
    """Build allowlisted Remnawave metadata for persistent webhook logs."""
    data = _as_mapping(payload.get("data"))
    return _drop_none(
        {
            "schema": WEBHOOK_LOG_PAYLOAD_SCHEMA,
            "source": "remnawave",
            "event_type": _safe_label(payload.get("event")),
            "event_id_fingerprint": _fingerprint(
                _first_present(payload, "id", "event_id", "eventId", "event_uuid", "eventUuid")
            ),
            "subject_fingerprint": _fingerprint(
                _first_present(
                    data,
                    "uuid",
                    "user_uuid",
                    "userUuid",
                    "node_uuid",
                    "nodeUuid",
                    "subscription_uuid",
                    "subscriptionUuid",
                )
            ),
            "status": _safe_label(_first_present(data, "status", "state"), max_length=40),
            "signature_present": bool(signature),
            "validation_status": _validation_status(is_valid),
            "validation_reason": _safe_label(validation_reason, max_length=80),
        }
    )


def build_invalid_body_webhook_log_payload(
    *,
    source: str,
    body: bytes,
    signature: str | None,
    validation_reason: str,
) -> dict[str, Any]:
    """Build metadata for invalid JSON bodies without retaining raw content."""
    return _drop_none(
        {
            "schema": WEBHOOK_LOG_PAYLOAD_SCHEMA,
            "source": _safe_label(source, max_length=50),
            "body_parse_status": "invalid_json",
            "body_size_bytes": len(body),
            "signature_present": bool(signature),
            "validation_status": "invalid",
            "validation_reason": _safe_label(validation_reason, max_length=80),
        }
    )


def cryptobot_event_type(payload: Mapping[str, Any]) -> str | None:
    return _safe_label(payload.get("update_type"))


def remnawave_event_type(payload: Mapping[str, Any]) -> str | None:
    return _safe_label(payload.get("event"))


def _validation_status(is_valid: bool) -> str:
    return "valid" if is_valid else "invalid"


def _fingerprint(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _safe_label(value: Any, *, max_length: int = 100) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or len(normalized) > max_length:
        return None
    if any(char not in _LABEL_CHARS for char in normalized):
        return None
    return normalized


def _drop_none(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}
