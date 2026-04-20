"""Canonical access delivery channel ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class AccessDeliveryChannelModel(Base):
    __tablename__ = "access_delivery_channels"
    __table_args__ = (
        UniqueConstraint(
            "service_identity_id",
            "channel_type",
            "channel_subject_ref",
            name="uq_access_delivery_channels_service_identity_type_subject",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    service_identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    origin_storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provisioning_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provisioning_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("device_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    channel_subject_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    delivery_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    delivery_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    archive_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
