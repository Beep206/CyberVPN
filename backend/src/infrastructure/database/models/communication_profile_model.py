"""Communication profile ORM model for storefront messaging surfaces."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.storefront_model import StorefrontModel


class CommunicationProfileModel(Base):
    __tablename__ = "communication_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
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

    storefronts: Mapped[list["StorefrontModel"]] = relationship(
        back_populates="communication_profile",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<CommunicationProfile(id={self.id}, key={self.profile_key}, status={self.status})>"
