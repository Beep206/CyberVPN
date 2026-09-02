"""Remove legacy unkeyed webhook-log fingerprints.

Revision ID: 20260830_webhook_hmac_cleanup
Revises: 20260830_remnawave_3_expand
Create Date: 2026-08-30

The v1 values were plain SHA-256 digests of identifiers whose input space can
be small enough to enumerate. Their source values are intentionally absent
from storage, so they cannot be safely converted to keyed HMACs. This bounded
cleanup removes them; v2 rows created by the application are fingerprinted
with WEBHOOK_LOG_FINGERPRINT_SECRET.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260830_webhook_hmac_cleanup"
down_revision: str | Sequence[str] | None = "20260830_remnawave_3_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH_SIZE = 500
# Alembic owns one transaction for the whole revision. Keep the emergency
# in-migration cleanup small and force larger backlogs through the resumable
# pre-cutover command, which commits every batch.
_MAX_MIGRATION_ROWS = 5_000
_TARGET_SCHEMA = "webhook_log.redacted.v2"
_LEGACY_FINGERPRINT_KEYS = frozenset(
    {
        "body_sha256",
        "event_id_fingerprint",
        "invoice_id_fingerprint",
        "subject_fingerprint",
    }
)
_SAFE_METADATA_KEYS = frozenset(
    {
        "body_parse_status",
        "body_size_bytes",
        "event_type",
        "legacy_fingerprints_removed",
        "legacy_payload_removed",
        "signature_present",
        "source",
        "status",
        "validation_reason",
        "validation_status",
    }
)


def upgrade() -> None:
    """Remove a small residual v1 backlog in deterministic batches.

    A large historical backlog must be drained before Alembic is started with
    ``scripts/cleanup_legacy_webhook_fingerprints.py``. Failing at the count
    preflight prevents a nominal batch size from hiding one large migration
    transaction.
    """
    webhook_logs = _webhook_logs_table()
    bind = op.get_bind()
    candidate_filter = _cleanup_candidate_filter(webhook_logs)
    candidate_count = int(
        bind.execute(sa.select(sa.func.count()).select_from(webhook_logs).where(candidate_filter)).scalar_one()
    )
    if candidate_count > _MAX_MIGRATION_ROWS:
        raise RuntimeError(
            "Legacy webhook fingerprint backlog exceeds the safe Alembic cap; "
            "run scripts/cleanup_legacy_webhook_fingerprints.py before upgrading"
        )
    if candidate_count == 0:
        return

    upper_bound = bind.execute(
        sa.select(webhook_logs.c.id).where(candidate_filter).order_by(webhook_logs.c.id.desc()).limit(1)
    ).scalar_one_or_none()
    if upper_bound is None:
        return
    last_id: Any | None = None

    while True:
        statement = (
            sa.select(
                webhook_logs.c.id,
                webhook_logs.c.payload,
                webhook_logs.c.signature,
            )
            .where(webhook_logs.c.id <= upper_bound, candidate_filter)
            .order_by(webhook_logs.c.id)
            .limit(_BATCH_SIZE)
        )
        if last_id is not None:
            statement = statement.where(webhook_logs.c.id > last_id)

        rows = list(bind.execute(statement).mappings())
        if not rows:
            break

        for row in rows:
            sanitized_payload = _sanitize_payload(
                row["payload"],
                signature_fingerprint_present=row["signature"] is not None,
            )
            bind.execute(
                webhook_logs.update()
                .where(webhook_logs.c.id == row["id"])
                .values(payload=sanitized_payload, signature=None)
            )
        last_id = rows[-1]["id"]


def _cleanup_candidate_filter(webhook_logs: sa.TableClause) -> sa.ColumnElement[bool]:
    """Select legacy/unmarked rows while making a completed cleanup resumable."""

    schema_value = webhook_logs.c.payload["schema"].as_string()
    return sa.or_(
        webhook_logs.c.signature.is_not(None),
        sa.func.coalesce(schema_value, "") != _TARGET_SCHEMA,
    )


def downgrade() -> None:
    """Keep the privacy cleanup while remaining readable by the prior app.

    Removed unkeyed digests cannot be reconstructed without their source
    identifiers. The previous application already treats fingerprint fields as
    optional, so leaving v2 metadata in place preserves an operational rollback
    without restoring enumerable identifiers.
    """


def _webhook_logs_table() -> sa.Table:
    return sa.table(
        "webhook_logs",
        sa.column("id", _uuid_type()),
        sa.column("payload", _json_type()),
        sa.column("signature", sa.String(length=64)),
    )


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


def _sanitize_payload(
    value: Any,
    *,
    signature_fingerprint_present: bool,
) -> dict[str, Any]:
    payload = value if isinstance(value, Mapping) else {}
    sanitized = {key: payload[key] for key in _SAFE_METADATA_KEYS if key in payload}
    sanitized["schema"] = _TARGET_SCHEMA
    if signature_fingerprint_present or any(key in payload for key in _LEGACY_FINGERPRINT_KEYS):
        sanitized["legacy_fingerprints_removed"] = True
    return sanitized
