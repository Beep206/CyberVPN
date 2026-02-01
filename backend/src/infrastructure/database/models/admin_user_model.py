"""AdminUserModel ORM model for CyberVPN backend authentication."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class AdminUserModel(Base):
    """
    Admin user model for authentication and authorization.

    Supports multiple authentication methods:
    - Username/password authentication
    - OAuth providers (GitHub, Google, etc.)
    - Telegram bot authentication
    - TOTP two-factor authentication
    """

    __tablename__ = "admin_users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)

    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)

    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)

    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    totp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    backup_codes_hash: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    anti_phishing_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AdminUserModel(id={self.id}, login='{self.login}', role='{self.role}')>"
