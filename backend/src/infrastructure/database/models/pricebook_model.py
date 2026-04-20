"""Pricebook ORM models for storefront-bound pricing overlays."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
    from src.infrastructure.database.models.offer_model import OfferModel
    from src.infrastructure.database.models.storefront_model import StorefrontModel


class PricebookModel(Base):
    __tablename__ = "pricebook_versions"
    __table_args__ = (
        UniqueConstraint("pricebook_key", "effective_from", name="uq_pricebook_versions_key_effective_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pricebook_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    storefront_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storefronts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merchant_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchant_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", index=True)
    region_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    discount_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    renewal_pricing_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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

    storefront: Mapped[StorefrontModel] = relationship(lazy="raise")
    merchant_profile: Mapped[MerchantProfileModel | None] = relationship(lazy="raise")
    entries: Mapped[list[PricebookEntryModel]] = relationship(
        back_populates="pricebook",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PricebookEntryModel(Base):
    __tablename__ = "pricebook_entries"
    __table_args__ = (UniqueConstraint("pricebook_id", "offer_id", name="uq_pricebook_entries_pricebook_offer"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pricebook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pricebook_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visible_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    included_addon_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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

    pricebook: Mapped[PricebookModel] = relationship(back_populates="entries", lazy="raise")
    offer: Mapped[OfferModel] = relationship(back_populates="pricebook_entries", lazy="raise")
