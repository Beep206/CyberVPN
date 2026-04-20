"""Canonical provisioning profile ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ProvisioningProfileModel(Base):
    __tablename__ = "provisioning_profiles"
    __table_args__ = (
        UniqueConstraint(
            "service_identity_id",
            "profile_key",
            name="uq_provisioning_profiles_service_identity_profile_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_identity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_channel: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    delivery_method: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    profile_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_profile_ref: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    provisioning_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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
