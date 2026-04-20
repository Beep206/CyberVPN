"""Partner workspace legal acceptance ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PartnerWorkspaceLegalAcceptanceModel(Base):
    """Acceptance evidence for partner-facing workspace legal documents."""

    __tablename__ = "partner_workspace_legal_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "partner_account_id",
            "document_kind",
            "document_version",
            name="uq_partner_workspace_legal_acceptance_document_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    partner_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    document_version: Mapped[str] = mapped_column(String(40), nullable=False)

    accepted_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

