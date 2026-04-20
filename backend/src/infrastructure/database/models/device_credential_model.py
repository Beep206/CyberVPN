"""Canonical device credential ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class DeviceCredentialModel(Base):
    __tablename__ = "device_credentials"
    __table_args__ = (
        UniqueConstraint(
            "service_identity_id",
            "credential_type",
            "subject_key",
            name="uq_device_credentials_service_identity_type_subject",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
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
    credential_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    credential_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    subject_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_credential_ref: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    credential_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoke_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
