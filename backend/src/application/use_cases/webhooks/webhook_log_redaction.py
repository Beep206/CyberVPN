"""Retention-safe webhook log payload builders."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from typing import Any, Literal

from src.config.settings import settings

WEBHOOK_LOG_PAYLOAD_SCHEMA = "webhook_log.redacted.v2"

WebhookFingerprintNamespace = Literal[
    "cryptobot_event_id",
    "cryptobot_invoice_id",
    "payment_provider_reference",
    "remnawave_body",
    "remnawave_event_id",
    "remnawave_subject",
    "signature",
]

_FINGERPRINT_DOMAIN = b"cybervpn/webhook-log-fingerprint/v2"

_LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")


def signature_fingerprint(signature: str | None) -> str | None:
    """Return a non-replayable fingerprint for a webhook signature header."""
    return webhook_log_fingerprint(signature, namespace="signature")


def webhook_log_fingerprint(
    value: Any,
    *,
    namespace: WebhookFingerprintNamespace,
) -> str | None:
    """Pseudonymize a webhook identifier with a dedicated, domain-separated key.

    An absent key intentionally produces no fingerprint. Falling back to an
    authentication/provider secret or to an unkeyed digest would make a
    low-entropy identifier enumerable and would couple unrelated key domains.
    """
    if value is None:
        return None
    if isinstance(value, bytes):
        if not value:
            return None
        normalized = value
    else:
        text_value = str(value).strip()
        if not text_value:
            return None
        normalized = text_value.encode("utf-8")

    secret = settings.webhook_log_fingerprint_secret.get_secret_value().strip()
    if not secret:
        return None

    message = b"\x00".join(
        (
            _FINGERPRINT_DOMAIN,
            namespace.encode("ascii"),
            normalized,
        )
    )
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


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
            "event_id_fingerprint": webhook_log_fingerprint(
                payload.get("update_id"),
                namespace="cryptobot_event_id",
            ),
            "invoice_id_fingerprint": webhook_log_fingerprint(
                invoice.get("invoice_id"),
                namespace="cryptobot_invoice_id",
            ),
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
            "event_id_fingerprint": webhook_log_fingerprint(
                _first_present(payload, "id", "event_id", "eventId", "event_uuid", "eventUuid"),
                namespace="remnawave_event_id",
            ),
            "subject_fingerprint": webhook_log_fingerprint(
                _first_present(
                    data,
                    "uuid",
                    "user_uuid",
                    "userUuid",
                    "user_id",
                    "userId",
                    "node_uuid",
                    "nodeUuid",
                    "subscription_uuid",
                    "subscriptionUuid",
                ),
                namespace="remnawave_subject",
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
