"""Redact persisted webhook log storage.

Revision ID: 20260531_redact_webhook_logs
Revises: 20260529_support_tickets
Create Date: 2026-05-31
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260531_redact_webhook_logs"
down_revision = "20260529_support_tickets"
branch_labels = None
depends_on = None

_SCHEMA = "webhook_log.redacted.v1"
_LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")
_FINGERPRINT_KEYS = frozenset({"event_id_fingerprint", "invoice_id_fingerprint", "subject_fingerprint"})


def _uuid_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid()


def _json_type() -> sa.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def upgrade() -> None:
    webhook_logs = _webhook_logs_table()
    bind = op.get_bind()

    rows = list(
        bind.execute(
            sa.select(
                webhook_logs.c.id,
                webhook_logs.c.source,
                webhook_logs.c.event_type,
                webhook_logs.c.payload,
                webhook_logs.c.signature,
                webhook_logs.c.is_valid,
                webhook_logs.c.error_message,
            )
        ).mappings()
    )

    for row in rows:
        payload = row["payload"] if isinstance(row["payload"], Mapping) else {}
        if payload.get("schema") == _SCHEMA:
            sanitized_payload = _sanitize_redacted_payload(row, payload)
            signature_fingerprint = _existing_fingerprint_or_hash(row["signature"])
        else:
            sanitized_payload = _sanitize_legacy_payload(row)
            signature_fingerprint = _fingerprint(row["signature"])

        bind.execute(
            webhook_logs.update()
            .where(webhook_logs.c.id == row["id"])
            .values(
                event_type=sanitized_payload.get("event_type"),
                payload=sanitized_payload,
                signature=signature_fingerprint,
            )
        )

    if bind.dialect.name == "postgresql":
        op.alter_column(
            "webhook_logs",
            "signature",
            type_=sa.String(length=64),
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "webhook_logs",
            "signature",
            type_=sa.String(length=255),
            existing_type=sa.String(length=64),
            existing_nullable=True,
        )


def _webhook_logs_table() -> sa.Table:
    return sa.table(
        "webhook_logs",
        sa.column("id", _uuid_type()),
        sa.column("source", sa.String(length=50)),
        sa.column("event_type", sa.String(length=100)),
        sa.column("payload", _json_type()),
        sa.column("signature", sa.String(length=255)),
        sa.column("is_valid", sa.Boolean()),
        sa.column("error_message", sa.Text()),
    )


def _existing_fingerprint_or_hash(value: Any) -> str | None:
    if _looks_like_sha256(value):
        return str(value).strip()
    return _fingerprint(value)


def _looks_like_sha256(value: Any) -> bool:
    if value is None:
        return False
    normalized = str(value).strip()
    return len(normalized) == 64 and all(char in "0123456789abcdefABCDEF" for char in normalized)


def _sanitize_legacy_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = row["payload"] if isinstance(row["payload"], Mapping) else {}
    source = _safe_label(row["source"], max_length=50) or "unknown"
    event_type = _event_type(source, row["event_type"], payload)

    sanitized: dict[str, Any] = {
        "schema": _SCHEMA,
        "source": source,
        "legacy_payload_removed": True,
        "signature_present": bool(row["signature"]),
        "validation_status": _validation_status(row["is_valid"]),
    }
    if event_type:
        sanitized["event_type"] = event_type

    if source == "cryptobot":
        _add_cryptobot_metadata(sanitized, payload)
    elif source == "remnawave":
        _add_remnawave_metadata(sanitized, payload)
    else:
        _set_if(sanitized, "event_id_fingerprint", _fingerprint(_first_present(payload, "id", "event_id", "eventId")))
        _set_if(sanitized, "status", _safe_label(_first_present(payload, "status", "state"), max_length=40))

    return sanitized


def _sanitize_redacted_payload(row: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    source = _safe_label(payload.get("source"), max_length=50) or _safe_label(row["source"], max_length=50) or "unknown"
    event_type = _safe_label(payload.get("event_type")) or _event_type(source, row["event_type"], payload)
    sanitized: dict[str, Any] = {
        "schema": _SCHEMA,
        "source": source,
        "signature_present": _safe_bool(payload.get("signature_present"), fallback=bool(row["signature"])),
        "validation_status": _safe_validation_status(payload.get("validation_status"))
        or _validation_status(row["is_valid"]),
    }
    if event_type:
        sanitized["event_type"] = event_type

    _set_if(sanitized, "legacy_payload_removed", _safe_bool(payload.get("legacy_payload_removed")))
    _set_if(sanitized, "status", _safe_label(payload.get("status"), max_length=40))
    _set_if(sanitized, "validation_reason", _safe_label(payload.get("validation_reason"), max_length=80))
    _set_if(sanitized, "body_parse_status", _safe_label(payload.get("body_parse_status"), max_length=40))
    _set_if(sanitized, "body_size_bytes", _safe_non_negative_int(payload.get("body_size_bytes")))

    for key in _FINGERPRINT_KEYS:
        value = payload.get(key)
        if _looks_like_sha256(value):
            sanitized[key] = str(value).strip().lower()

    if source == "cryptobot":
        _add_cryptobot_metadata(sanitized, payload)
    elif source == "remnawave":
        _add_remnawave_metadata(sanitized, payload)

    return sanitized


def _add_cryptobot_metadata(sanitized: dict[str, Any], payload: Mapping[str, Any]) -> None:
    invoice = _as_mapping(payload.get("payload"))
    _set_if(sanitized, "event_id_fingerprint", _fingerprint(payload.get("update_id")))
    _set_if(sanitized, "invoice_id_fingerprint", _fingerprint(invoice.get("invoice_id")))
    _set_if(sanitized, "status", _safe_label(invoice.get("status"), max_length=40))


def _add_remnawave_metadata(sanitized: dict[str, Any], payload: Mapping[str, Any]) -> None:
    data = _as_mapping(payload.get("data"))
    _set_if(sanitized, "event_id_fingerprint", _fingerprint(_first_present(payload, "id", "event_id", "eventId")))
    _set_if(
        sanitized,
        "subject_fingerprint",
        _fingerprint(
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
    )
    _set_if(sanitized, "status", _safe_label(_first_present(data, "status", "state"), max_length=40))


def _event_type(source: str, row_event_type: Any, payload: Mapping[str, Any]) -> str | None:
    if source == "cryptobot":
        return _safe_label(payload.get("update_type")) or _safe_label(row_event_type)
    if source == "remnawave":
        return _safe_label(payload.get("event")) or _safe_label(row_event_type)
    return _safe_label(row_event_type)


def _validation_status(is_valid: Any) -> str:
    if is_valid is True:
        return "valid"
    if is_valid is False:
        return "invalid"
    return "unknown"


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


def _safe_bool(value: Any, *, fallback: bool | None = None) -> bool | None:
    if isinstance(value, bool):
        return value
    return fallback


def _safe_validation_status(value: Any) -> str | None:
    normalized = _safe_label(value, max_length=20)
    if normalized in {"valid", "invalid", "unknown"}:
        return normalized
    return None


def _safe_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _set_if(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        payload[key] = value
