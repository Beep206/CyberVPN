"""Partner workspace organization profile and workspace preference ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerWorkspaceProfileModel(Base):
    """Workspace-owned organization profile and preference snapshot."""

    __tablename__ = "partner_workspace_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operating_regions: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technical_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finance_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    acquisition_channels: Mapped[str | None] = mapped_column(Text, nullable=True)

    preferred_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    require_mfa_for_workspace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_passkeys: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_active_sessions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

