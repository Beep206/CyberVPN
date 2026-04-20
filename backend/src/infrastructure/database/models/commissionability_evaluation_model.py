"""Commissionability evaluation ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class CommissionabilityEvaluationModel(Base):
    __tablename__ = "commissionability_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    commissionability_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    partner_context_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    program_allows_commissionability: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    positive_commission_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    paid_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    fully_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    open_payment_dispute_present: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    risk_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    evaluation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    explainability_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
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
