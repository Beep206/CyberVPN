"""
OAuthAccount ORM model for OAuth provider integration.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class OAuthAccount(Base):
    """
    OAuth account model for linking admin users with OAuth providers.

    Supports multiple OAuth providers (GitHub, Google, etc.) and stores
    provider-specific tokens and user information.
    """

    __tablename__ = "oauth_accounts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    provider_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    provider_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    provider_avatar_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, provider='{self.provider}', user_id={self.user_id})>"
