"""OtpCodeModel ORM model for email verification codes."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class OtpCodeModel(Base):
    """
    OTP code model for email verification and other purposes.

    Stores 6-digit verification codes with:
    - Expiration time (default 3 hours)
    - Attempt tracking (max 5 attempts)
    - Resend tracking (max 3 resends per hour)
    - Purpose field for different use cases (email verification, password reset, 2FA)
    """

    __tablename__ = "otp_codes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="email_verification",
    )

    attempts_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    resend_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_resends: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    last_resend_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to user
    user = relationship("AdminUserModel", back_populates="otp_codes", lazy="raise")

    __table_args__ = (
        CheckConstraint("code ~ '^[0-9]{6}$'", name="ck_otp_codes_valid_code"),
        CheckConstraint(
            "purpose IN ('email_verification', 'password_reset', 'login_2fa')",
            name="ck_otp_codes_valid_purpose",
        ),
        Index("ix_otp_codes_expires_at", "expires_at", postgresql_where="verified_at IS NULL"),
    )

    def __repr__(self) -> str:
        return f"<OtpCodeModel(id={self.id}, user_id={self.user_id}, purpose='{self.purpose}')>"

    @property
    def is_expired(self) -> bool:
        """Check if the OTP code has expired."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    @property
    def is_verified(self) -> bool:
        """Check if the OTP code has been verified."""
        return self.verified_at is not None

    @property
    def is_exhausted(self) -> bool:
        """Check if max attempts have been reached."""
        return self.attempts_used >= self.max_attempts

    @property
    def can_resend(self) -> bool:
        """Check if resend is allowed."""
        return self.resend_count < self.max_resends

    @property
    def attempts_remaining(self) -> int:
        """Get remaining verification attempts."""
        return max(0, self.max_attempts - self.attempts_used)

    @property
    def resends_remaining(self) -> int:
        """Get remaining resend attempts."""
        return max(0, self.max_resends - self.resend_count)
