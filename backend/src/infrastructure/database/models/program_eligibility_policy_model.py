"""Program eligibility ORM model for partner and growth program participation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class ProgramEligibilityPolicyModel(Base):
    __tablename__ = "program_eligibility_versions"
    __table_args__ = (
        UniqueConstraint("policy_key", "effective_from", name="uq_program_eligibility_key_effective_from"),
        CheckConstraint(
            """
            ((subscription_plan_id IS NOT NULL)::integer +
             (plan_addon_id IS NOT NULL)::integer +
             (offer_id IS NOT NULL)::integer) = 1
            """,
            name="ck_program_eligibility_exactly_one_subject",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subscription_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    plan_addon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plan_addons.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    invite_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    referral_credit_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creator_affiliate_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    performance_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reseller_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    renewal_commissionable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    addon_commissionable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
