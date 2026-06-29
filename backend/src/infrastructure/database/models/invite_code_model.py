"""InviteCode ORM model for friend-invite system."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class InviteCodeModel(Base):
    """Invite codes generated from purchases or granted by admin."""

    __tablename__ = "invite_codes"
    __table_args__ = (
        CheckConstraint(
            "grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_codes_grant_duration_mode",
        ),
        CheckConstraint(
            "child_grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_codes_child_grant_duration_mode",
        ),
        CheckConstraint(
            "child_invite_expiry_mode IN ('relative','absolute','none')",
            name="ck_invite_codes_child_expiry_mode",
        ),
        CheckConstraint(
            "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
            "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
            name="ck_invite_codes_device_override_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    free_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
    )

    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    campaign_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaign_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    root_invite_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_invite_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_redemption_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_redemptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    generation_depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    source_growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_benefit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_code_benefits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="issued",
        server_default="issued",
        index=True,
    )

    code_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    code_prefix: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
        index=True,
    )

    entitlement_mode: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    entitlement_profile_key: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    entitlement_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    grant_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="legacy_invite_access",
        server_default="legacy_invite_access",
    )

    grant_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    grant_duration_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fixed_days",
        server_default="fixed_days",
    )

    grant_duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    grant_device_limit_override: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    grant_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    child_grant_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    child_grant_duration_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="fixed_days",
        server_default="fixed_days",
    )

    child_grant_duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    child_grant_device_limit_override: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    child_invite_expiry_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="relative",
        server_default="relative",
    )

    child_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    risk_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    redemption_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    issue_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    used_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<InviteCode(id={self.id}, code_prefix={self.code_prefix}, is_used={self.is_used})>"
