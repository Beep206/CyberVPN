"""Support profile ORM model for storefront routing."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.storefront_model import StorefrontModel


class SupportProfileModel(Base):
    __tablename__ = "support_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    support_email: Mapped[str] = mapped_column(String(255), nullable=False)
    help_center_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
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
        back_populates="support_profile",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<SupportProfile(id={self.id}, key={self.profile_key}, status={self.status})>"
