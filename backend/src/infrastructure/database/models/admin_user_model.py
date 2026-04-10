"""AdminUserModel ORM model for CyberVPN backend authentication."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)

    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    totp_secret: Mapped[str | None] = mapped_column(String(32), nullable=True)

    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    backup_codes_hash: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    anti_phishing_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Modern Auth Tracking (Devise-style)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sign_in_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_sign_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_sign_in_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # SaaS/VPN Anti-Fraud & Legal Compliance
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fraud_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    tos_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Email verification flag
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Soft-delete timestamp (FEAT-03)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Trial period tracking
    trial_activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Profile fields (BF2-3)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Notification preferences (BF2-5)
    notification_prefs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationship to OTP codes
    otp_codes = relationship("OtpCodeModel", back_populates="user", lazy="raise")

    def __repr__(self) -> str:
        return f"<AdminUserModel(id={self.id}, login='{self.login}', role='{self.role}')>"
