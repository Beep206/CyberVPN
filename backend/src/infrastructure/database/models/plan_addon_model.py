"""Plan add-on catalog and purchased add-on ORM models."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class PlanAddonModel(Base):
    """Catalog of purchasable plan add-ons."""

    __tablename__ = "plan_addons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="inherits_subscription")
    is_stackable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quantity_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    price_rub: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_quantity_by_plan: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    delta_entitlements: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requires_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sale_channels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SubscriptionAddonModel(Base):
    """Purchased add-ons attached to a user's active subscription window."""

    __tablename__ = "subscription_addons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mobile_users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_addon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plan_addons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    location_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
