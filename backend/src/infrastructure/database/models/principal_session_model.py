"""Principal session ORM model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
    from src.infrastructure.database.models.refresh_token_model import RefreshToken


class PrincipalSessionModel(Base):
    __tablename__ = "principal_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_realm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    principal_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    scope_family: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token_jti: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    refresh_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    auth_realm: Mapped["AuthRealmModel"] = relationship(back_populates="principal_sessions", lazy="raise")
    refresh_token: Mapped["RefreshToken | None"] = relationship(back_populates="principal_session", lazy="raise")

    def __repr__(self) -> str:
        return f"<PrincipalSession(id={self.id}, subject={self.principal_subject}, audience={self.audience})>"
