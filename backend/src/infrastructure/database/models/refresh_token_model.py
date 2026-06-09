"""RefreshToken ORM model for JWT refresh token management."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base

if TYPE_CHECKING:
    from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel


class RefreshToken(Base):
    """
    Refresh token model for JWT token rotation and revocation.

    Stores hashed refresh tokens to enable token rotation, revocation,
    and tracking of user sessions.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("uq_refresh_tokens_jti", "jti", unique=True, postgresql_where=text("jti IS NOT NULL")),
        Index("ix_refresh_tokens_principal_session_id", "principal_session_id"),
        Index("ix_refresh_tokens_family_id", "family_id"),
        Index("ix_refresh_tokens_parent_token_id", "parent_token_id"),
        Index("ix_refresh_tokens_replaced_by_token_id", "replaced_by_token_id"),
        Index("ix_refresh_tokens_consumed_at", "consumed_at"),
        Index("ix_refresh_tokens_session_family", "principal_session_id", "family_id"),
        Index("ix_refresh_tokens_principal_owner", "principal_class", "principal_subject", "auth_realm_id"),
        CheckConstraint(
            "principal_class in ('admin', 'partner_operator', 'customer')",
            name="ck_refresh_tokens_principal_class",
        ),
        CheckConstraint("principal_subject <> ''", name="ck_refresh_tokens_principal_subject_nonempty"),
        CheckConstraint("audience <> ''", name="ck_refresh_tokens_audience_nonempty"),
        CheckConstraint("scope_family <> ''", name="ck_refresh_tokens_scope_family_nonempty"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    auth_realm_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    principal_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    principal_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    scope_family: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    family_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    parent_token_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    principal_session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("principal_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Session tracking fields (BF2-4)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    principal_session: Mapped["PrincipalSessionModel | None"] = relationship(
        "PrincipalSessionModel",
        back_populates="refresh_token",
        foreign_keys="PrincipalSessionModel.refresh_token_id",
        uselist=False,
        lazy="raise",
    )
    rotation_session: Mapped["PrincipalSessionModel | None"] = relationship(
        "PrincipalSessionModel",
        back_populates="refresh_token_history",
        foreign_keys=[principal_session_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        status = "revoked" if self.revoked_at else "active"
        return (
            f"<RefreshToken(id={self.id}, principal_class={self.principal_class}, "
            f"principal_subject={self.principal_subject}, status='{status}')>"
        )
