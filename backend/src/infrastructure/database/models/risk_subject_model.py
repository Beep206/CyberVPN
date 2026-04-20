"""Risk graph subject ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class RiskSubjectModel(Base):
    __tablename__ = "risk_subjects"
    __table_args__ = (
        UniqueConstraint(
            "principal_class",
            "principal_subject",
            "auth_realm_id",
            name="uq_risk_subjects_principal_realm",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principal_class: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    principal_subject: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low", server_default="low")
    metadata_payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
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
