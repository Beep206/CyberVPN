"""Risk graph identifier ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class RiskIdentifierModel(Base):
    __tablename__ = "risk_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "risk_subject_id",
            "identifier_type",
            "value_hash",
            name="uq_risk_identifiers_subject_type_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identifier_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value_preview: Mapped[str] = mapped_column(String(120), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

