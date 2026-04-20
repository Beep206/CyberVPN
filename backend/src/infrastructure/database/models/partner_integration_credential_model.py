"""Canonical partner integration credential ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerIntegrationCredentialModel(Base):
    __tablename__ = "partner_integration_credentials"
    __table_args__ = (
        UniqueConstraint(
            "partner_account_id",
            "credential_kind",
            name="uq_partner_integration_credentials_partner_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    credential_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_rotation",
        server_default="pending_rotation",
        index=True,
    )
    credential_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_hint: Mapped[str] = mapped_column(String(60), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rotated_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
