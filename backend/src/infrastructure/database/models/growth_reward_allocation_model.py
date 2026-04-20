"""Canonical non-cash growth reward allocation ORM model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthRewardAllocationModel(Base):
    __tablename__ = "growth_reward_allocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reward_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    allocation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="allocated",
        server_default="allocated",
        index=True,
    )
    beneficiary_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invite_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referral_commission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("referral_commissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        unique=True,
    )
    source_key: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=1, server_default="1")
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(12), nullable=True)
    reward_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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
