"""Billing descriptor ORM model for order-facing statement identity."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
    from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel


class BillingDescriptorModel(Base):
    __tablename__ = "billing_descriptors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descriptor_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    merchant_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchant_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoice_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    statement_descriptor: Mapped[str] = mapped_column(String(64), nullable=False)
    soft_descriptor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    support_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    support_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
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

    merchant_profile: Mapped[MerchantProfileModel] = relationship(
        back_populates="billing_descriptors",
        lazy="raise",
    )
    invoice_profile: Mapped[InvoiceProfileModel | None] = relationship(
        back_populates="billing_descriptors",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<BillingDescriptor(id={self.id}, key={self.descriptor_key}, default={self.is_default})>"
