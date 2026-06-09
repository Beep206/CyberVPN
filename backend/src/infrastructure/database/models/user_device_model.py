"""User device ORM model for realm-scoped auth sessions."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
    from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel


class UserDeviceModel(Base):
    """Stable device identity separated from refresh token rotation history."""

    __tablename__ = "user_devices"
    __table_args__ = (
        Index("ix_user_devices_principal", "auth_realm_id", "principal_class", "principal_subject"),
        Index("ix_user_devices_last_seen_at", "last_seen_at"),
        Index("ix_user_devices_revoked_at", "revoked_at"),
        Index(
            "uq_user_devices_active_principal_device_key",
            "auth_realm_id",
            "principal_class",
            "principal_subject",
            "device_key_hash",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    auth_realm_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    principal_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    device_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    device_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    auth_realm: Mapped["AuthRealmModel"] = relationship(back_populates="user_devices", lazy="raise")
    principal_sessions: Mapped[list["PrincipalSessionModel"]] = relationship(
        back_populates="user_device",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<UserDevice(id={self.id}, subject={self.principal_subject}, revoked={self.revoked_at is not None})>"
