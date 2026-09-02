"""Persistence added for the Remnawave 3.x identity, stream, and delegated-access cutover."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class RemnawaveIdentityReconciliationModel(Base):
    """Auditable, fail-closed mapping result produced while panel 2.8 is online."""

    __tablename__ = "remnawave_identity_reconciliations"
    __table_args__ = (
        UniqueConstraint("subject_type", "subject_id", name="uq_remnawave_reconciliation_subject"),
        CheckConstraint(
            "reconciliation_state IN ('pending', 'mapped', 'missing', 'duplicate', 'conflict')",
            name="ck_remnawave_reconciliation_state",
        ),
        Index(
            "ix_remnawave_reconciliation_subject_numeric",
            "subject_type",
            "numeric_user_id",
        ),
        Index(
            "uq_remnawave_reconciliation_mapped_numeric",
            "subject_type",
            "numeric_user_id",
            unique=True,
            postgresql_where=text("numeric_user_id IS NOT NULL AND reconciliation_state = 'mapped'"),
        ),
        Index(
            "uq_remnawave_reconciliation_mapped_legacy",
            "subject_type",
            "legacy_uuid",
            unique=True,
            postgresql_where=text("legacy_uuid IS NOT NULL AND reconciliation_state = 'mapped'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    legacy_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    numeric_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    reconciliation_state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class PartnerRemnawaveResourceGrantModel(Base):
    """Explicit object-level partner grant; no built-in role receives one implicitly."""

    __tablename__ = "partner_remnawave_resource_grants"
    __table_args__ = (
        UniqueConstraint("workspace_id", "resource_type", "resource_uuid", name="uq_partner_remnawave_grant"),
        CheckConstraint(
            "resource_type IN "
            "('node', 'host', 'profile', 'squad', 'tag', 'integration', 'shared_list', 'service_identity')",
            name="ck_partner_remnawave_resource_type",
        ),
        Index(
            "uq_partner_remnawave_exclusive_active_resource",
            "resource_type",
            "resource_uuid",
            unique=True,
            postgresql_where=text(
                "revoked_at IS NULL AND resource_type IN ('node', 'service_identity', 'profile', 'integration')"
            ),
            sqlite_where=text(
                "revoked_at IS NULL AND resource_type IN ('node', 'service_identity', 'profile', 'integration')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_uuid: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    permission_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    granted_by_admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    revoked_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)


class RemnawaveConnectionDropReceiptModel(Base):
    """Canonical durable idempotency boundary for non-reconcilable drops.

    No client idempotency key, raw scope, provider payload, or raw IP is ever
    stored. Keyed, domain-separated HMACs remain stable across Valkey/process
    restarts while preventing offline enumeration of small IP spaces.
    """

    __tablename__ = "remnawave_connection_drop_receipts"
    __table_args__ = (
        UniqueConstraint("key_hmac", name="uq_remnawave_connection_drop_receipt_key_hmac"),
        UniqueConstraint("receipt_id", name="uq_remnawave_connection_drop_receipt_public_id"),
        CheckConstraint(
            "audience IN ('admin', 'partner', 'customer')",
            name="ck_remnawave_connection_drop_receipt_audience",
        ),
        CheckConstraint(
            "state IN ('outcome_unknown', 'accepted', 'rejected')",
            name="ck_remnawave_connection_drop_receipt_state",
        ),
        CheckConstraint(
            "(state = 'outcome_unknown' AND expires_at IS NULL "
            "AND reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
            "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL) OR "
            "(state IN ('accepted', 'rejected') AND expires_at IS NOT NULL AND ("
            "(reconciled_at IS NULL AND reconciled_by_admin_id IS NULL "
            "AND reconciliation_reason IS NULL AND reconciliation_reference IS NULL) OR "
            "(reconciled_at IS NOT NULL AND reconciled_by_admin_id IS NOT NULL "
            "AND reconciliation_reason IS NOT NULL AND reconciliation_reference IS NOT NULL "
            "AND updated_at = reconciled_at AND expires_at > reconciled_at)))",
            name="ck_remnawave_connection_drop_receipt_lifecycle",
        ),
        CheckConstraint(
            "reconciliation_reason IS NULL OR "
            "(state = 'accepted' AND reconciliation_reason IN "
            "('provider_confirmed_applied', 'postcondition_confirmed_applied')) OR "
            "(state = 'rejected' AND reconciliation_reason IN "
            "('provider_confirmed_not_applied', 'postcondition_confirmed_not_applied'))",
            name="ck_remnawave_connection_drop_receipt_reconciliation_reason",
        ),
        CheckConstraint(
            "(audience = 'partner' AND workspace_id IS NOT NULL) OR "
            "(audience IN ('admin', 'customer') AND workspace_id IS NULL)",
            name="ck_remnawave_connection_drop_receipt_workspace_scope",
        ),
        CheckConstraint(
            "char_length(key_hmac) = 64 AND char_length(hmac_key_id) = 64 "
            "AND char_length(scope_hmac) = 64 AND char_length(payload_hmac) = 64 "
            "AND char_length(receipt_id) = 43",
            name="ck_remnawave_connection_drop_receipt_digest_lengths",
        ),
        Index(
            "ix_remnawave_connection_drop_receipts_pending_actor",
            "audience",
            "actor_id",
            postgresql_where=text("state = 'outcome_unknown'"),
            sqlite_where=text("state = 'outcome_unknown'"),
        ),
        Index(
            "ix_remnawave_connection_drop_receipts_key_lifecycle",
            "hmac_key_id",
            "state",
            "expires_at",
        ),
        Index(
            "ix_remnawave_connection_drop_receipts_unresolved_public_id",
            "receipt_id",
            postgresql_where=text("state = 'outcome_unknown'"),
            sqlite_where=text("state = 'outcome_unknown'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    hmac_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_id: Mapped[str] = mapped_column(String(43), nullable=False)
    audience: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    scope_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="outcome_unknown", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=True
    )
    reconciliation_reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    reconciliation_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RemnawaveStreamReceiptModel(Base):
    __tablename__ = "remnawave_stream_receipts"
    __table_args__ = (
        UniqueConstraint("stream_name", "message_id", name="uq_remnawave_stream_receipt"),
        CheckConstraint(
            "processing_status IN ('processing', 'committed', 'retry', 'dead_letter')",
            name="ck_remnawave_stream_receipt_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(12), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(16), nullable=False, default="processing", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    redacted_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class RemnawaveStreamDeadLetterModel(Base):
    """Redacted DLQ metadata. Raw stream payloads are deliberately never persisted."""

    __tablename__ = "remnawave_stream_dead_letters"
    __table_args__ = (UniqueConstraint("stream_name", "message_id", name="uq_remnawave_stream_dlq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String(12), nullable=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    redacted_error: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class RemnawaveUserUsageHourlyModel(Base):
    __tablename__ = "remnawave_user_usage_hourly"
    __table_args__ = (UniqueConstraint("bucket_at", "node_id", "user_id", name="uq_remnawave_user_usage_hour"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class RemnawaveSubscriptionRequestEventModel(Base):
    __tablename__ = "remnawave_subscription_request_events"
    __table_args__ = (UniqueConstraint("stream_message_id", name="uq_remnawave_subscription_request_event"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    response_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    response_rule_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    request_ip_hmac: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent_family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class RemnawaveNodePresenceModel(Base):
    __tablename__ = "remnawave_node_user_presence"
    __table_args__ = (UniqueConstraint("node_id", "user_id", "ip_hmac", name="uq_remnawave_node_user_presence"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    ip_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class RemnawaveNodeConnectionsHourlyModel(Base):
    __tablename__ = "remnawave_node_connections_hourly"
    __table_args__ = (UniqueConstraint("bucket_at", "node_id", "user_id", name="uq_remnawave_node_connections_hour"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    connection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class RemnawaveStreamGapModel(Base):
    """Records gaps caused by ephemeral Valkey loss and REST reconciliation status."""

    __tablename__ = "remnawave_stream_gaps"
    __table_args__ = (
        UniqueConstraint("gap_fingerprint", name="uq_remnawave_stream_gap_fingerprint"),
        CheckConstraint(
            "reconciliation_status IN ('pending', 'running', 'reconciled', 'partial', 'failed')",
            name="ck_remnawave_stream_gap_status",
        ),
        CheckConstraint(
            "(loss_kind = 'exact_ids' AND missing_count >= 1 AND missing_count <= 1000) "
            "OR (loss_kind = 'unknown_range' AND missing_count = 0)",
            name="ck_remnawave_stream_gap_missing_count",
        ),
        CheckConstraint(
            "(reconciliation_status IN ('pending', 'running') AND expires_at IS NULL) OR "
            "(reconciliation_status IN ('reconciled', 'partial', 'failed') AND expires_at IS NOT NULL)",
            name="ck_remnawave_stream_gap_terminal_expiry",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gap_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    loss_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    stream_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    missing_message_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    from_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redacted_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class RemnawaveStreamCheckpointModel(Base):
    """Durable consumer checkpoint and last observed Valkey stream epoch."""

    __tablename__ = "remnawave_stream_checkpoints"
    __table_args__ = (
        CheckConstraint(
            "observed_group_lag IS NULL OR observed_group_lag >= 0",
            name="ck_remnawave_stream_checkpoint_group_lag_nonnegative",
        ),
        UniqueConstraint("stream_name", name="uq_remnawave_stream_checkpoint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_committed_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_committed_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_committed_sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    observed_identity_hmac: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_first_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_last_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_group_last_delivered_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_group_pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observed_group_pending_min_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_group_pending_max_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_group_lag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream_exists: Mapped[bool] = mapped_column(default=False, nullable=False)
    group_exists: Mapped[bool] = mapped_column(default=False, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
