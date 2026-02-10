"""PromoCode and PromoCodeUsage ORM models for discount system."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.session import Base


class PromoCodeModel(Base):
    """Admin-created discount codes with usage limits and expiry."""

    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    discount_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    discount_value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )

    max_uses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    current_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_single_use: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    plan_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=True,
    )

    min_amount: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    usages: Mapped[list["PromoCodeUsageModel"]] = relationship(
        back_populates="promo_code",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<PromoCode(id={self.id}, code={self.code}, active={self.is_active})>"


class PromoCodeUsageModel(Base):
    """Tracks which users have used which promo codes."""

    __tablename__ = "promo_code_usages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    discount_applied: Mapped[float] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    promo_code: Mapped["PromoCodeModel"] = relationship(
        back_populates="usages",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<PromoCodeUsage(id={self.id}, promo={self.promo_code_id}, user={self.user_id})>"
