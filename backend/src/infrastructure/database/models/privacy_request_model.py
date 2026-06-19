"""Privacy request ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


_ACTIVE_PRIVACY_REQUEST_WHERE = text(
    "status IN ('submitted', 'identity_verification', 'pending_decision', 'approved', 'scheduled', 'failed')"
)


class PrivacyRequestModel(Base):
    __tablename__ = "privacy_requests"
    __table_args__ = (
        Index("ix_privacy_requests_status_submitted", "status", "submitted_at"),
        Index("ix_privacy_requests_type_status_submitted", "request_type", "status", "submitted_at"),
        Index("ix_privacy_requests_assignee_status_updated", "assigned_admin_id", "status", "updated_at"),
        Index("ix_privacy_requests_principal_submitted", "principal_subject", "submitted_at"),
        Index(
            "ix_privacy_requests_scheduled_due",
            "scheduled_for",
            postgresql_where=text("status IN ('approved', 'scheduled', 'failed')"),
            sqlite_where=text("status IN ('approved', 'scheduled', 'failed')"),
        ),
        Index(
            "uq_privacy_requests_active_principal",
            "auth_realm_id",
            "principal_type",
            "principal_subject",
            "request_type",
            unique=True,
            postgresql_where=_ACTIVE_PRIVACY_REQUEST_WHERE,
            sqlite_where=_ACTIVE_PRIVACY_REQUEST_WHERE,
        ),
        Index(
            "uq_privacy_requests_idempotency_key_hash",
            "idempotency_key_hash",
            unique=True,
            postgresql_where=text("idempotency_key_hash IS NOT NULL"),
            sqlite_where=text("idempotency_key_hash IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    principal_type: Mapped[str] = mapped_column(String(40), nullable=False)
    principal_subject: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    customer_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    support_ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes_redacted: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    identity_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    identity_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_redacted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    events: Mapped[list[PrivacyRequestEventModel]] = relationship(
        back_populates="privacy_request",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PrivacyRequestEventModel.created_at",
    )


class PrivacyRequestEventModel(Base):
    __tablename__ = "privacy_request_events"
    __table_args__ = (
        Index("ix_privacy_request_events_request_created", "privacy_request_id", "created_at"),
        Index("ix_privacy_request_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    privacy_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("privacy_requests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    safe_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    privacy_request: Mapped[PrivacyRequestModel] = relationship(back_populates="events", lazy="raise")
