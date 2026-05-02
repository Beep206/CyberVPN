"""Partner bot runtime and provisioning ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerBotModel(Base):
    __tablename__ = "partner_bots"
    __table_args__ = (
        UniqueConstraint(
            "partner_account_id",
            "bot_key",
            name="uq_partner_bots_workspace_bot_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bot_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_bot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    managed_by_bot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    default_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-EN", server_default="en-EN")
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provisioning_path: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="managed_bot",
        server_default="managed_bot",
        index=True,
    )
    token_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="missing",
        server_default="missing",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    release_channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="stable",
        server_default="stable",
    )
    provisioning_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provisioning_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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


class PartnerBotProvisioningJobModel(Base):
    __tablename__ = "partner_bot_provisioning_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_bot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provisioning_path: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="managed_bot",
        server_default="managed_bot",
    )
    job_status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
