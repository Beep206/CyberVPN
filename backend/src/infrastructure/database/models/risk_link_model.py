"""Risk graph linkage ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class RiskLinkModel(Base):
    __tablename__ = "risk_links"
    __table_args__ = (
        UniqueConstraint(
            "left_subject_id",
            "right_subject_id",
            "identifier_type",
            name="uq_risk_links_subject_pair_identifier_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    left_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    right_subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_identifier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_identifiers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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

