"""Storefront ORM model for public customer-facing surfaces."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
    from src.infrastructure.database.models.brand_model import BrandModel
    from src.infrastructure.database.models.communication_profile_model import CommunicationProfileModel
    from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
    from src.infrastructure.database.models.support_profile_model import SupportProfileModel


class StorefrontModel(Base):
    __tablename__ = "storefronts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storefront_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    host: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    merchant_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchant_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    support_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("support_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    communication_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    brand: Mapped["BrandModel"] = relationship(back_populates="storefronts", lazy="raise")
    auth_realm: Mapped["AuthRealmModel | None"] = relationship(back_populates="storefronts", lazy="raise")
    merchant_profile: Mapped["MerchantProfileModel | None"] = relationship(
        back_populates="storefronts",
        lazy="raise",
    )
    support_profile: Mapped["SupportProfileModel | None"] = relationship(
        back_populates="storefronts",
        lazy="raise",
    )
    communication_profile: Mapped["CommunicationProfileModel | None"] = relationship(
        back_populates="storefronts",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Storefront(id={self.id}, key={self.storefront_key}, host={self.host})>"
