"""Offer-layer ORM model for channel and surface commercial overlays."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.pricebook_model import PricebookEntryModel
    from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel


class OfferModel(Base):
    __tablename__ = "offer_versions"
    __table_args__ = (UniqueConstraint("offer_key", "effective_from", name="uq_offer_versions_key_effective_from"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    subscription_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    included_addon_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sale_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    visibility_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    invite_bundle: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    trial_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gift_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    referral_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    renewal_incentives: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

    subscription_plan: Mapped[SubscriptionPlanModel] = relationship(lazy="raise")
    pricebook_entries: Mapped[list[PricebookEntryModel]] = relationship(back_populates="offer", lazy="raise")
