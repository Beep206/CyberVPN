"""Auth realm ORM model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
    from src.infrastructure.database.models.storefront_model import StorefrontModel


class AuthRealmModel(Base):
    __tablename__ = "auth_realms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    realm_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    realm_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    audience: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    cookie_namespace: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    storefronts: Mapped[list["StorefrontModel"]] = relationship(back_populates="auth_realm", lazy="raise")
    principal_sessions: Mapped[list["PrincipalSessionModel"]] = relationship(
        back_populates="auth_realm",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<AuthRealm(id={self.id}, key={self.realm_key}, audience={self.audience})>"
