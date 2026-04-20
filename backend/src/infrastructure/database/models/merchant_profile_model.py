"""Merchant profile ORM model for storefront billing surfaces."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
    from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
    from src.infrastructure.database.models.storefront_model import StorefrontModel


class MerchantProfileModel(Base):
    __tablename__ = "merchant_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    legal_entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_descriptor: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoice_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    settlement_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supported_currencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tax_behavior: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    refund_responsibility_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="merchant_of_record",
        server_default="merchant_of_record",
    )
    chargeback_liability_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="merchant_of_record",
        server_default="merchant_of_record",
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    invoice_profile: Mapped[InvoiceProfileModel | None] = relationship(
        back_populates="merchant_profiles",
        lazy="raise",
    )
    storefronts: Mapped[list[StorefrontModel]] = relationship(
        back_populates="merchant_profile",
        lazy="raise",
    )
    billing_descriptors: Mapped[list[BillingDescriptorModel]] = relationship(
        back_populates="merchant_profile",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<MerchantProfile(id={self.id}, key={self.profile_key}, status={self.status})>"
