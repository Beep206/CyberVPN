"""Partner application draft, lane application, review, and attachment ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerApplicationDraftModel(Base):
    __tablename__ = "partner_application_drafts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    applicant_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    draft_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    review_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PartnerLaneApplicationModel(Base):
    __tablename__ = "partner_lane_applications"
    __table_args__ = (
        UniqueConstraint(
            "partner_account_id",
            "lane_key",
            name="uq_partner_lane_applications_account_lane",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_application_draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_application_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lane_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    application_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    decision_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PartnerApplicationReviewRequestModel(Base):
    __tablename__ = "partner_application_review_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_application_draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_application_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lane_application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_lane_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_attachments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    requested_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PartnerApplicationAttachmentModel(Base):
    __tablename__ = "partner_application_attachments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_application_draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_application_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lane_application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_lane_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_application_review_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attachment_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    uploaded_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
