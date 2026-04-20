"""Invoice profile ORM model for order-facing invoice and tax behavior."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
    from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel


class InvoiceProfileModel(Base):
    __tablename__ = "invoice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    issuer_legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issuer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_behavior: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    invoice_footer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_footer: Mapped[str | None] = mapped_column(String(500), nullable=True)
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

    merchant_profiles: Mapped[list[MerchantProfileModel]] = relationship(
        back_populates="invoice_profile",
        lazy="raise",
    )
    billing_descriptors: Mapped[list[BillingDescriptorModel]] = relationship(
        back_populates="invoice_profile",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<InvoiceProfile(id={self.id}, key={self.profile_key}, status={self.status})>"
