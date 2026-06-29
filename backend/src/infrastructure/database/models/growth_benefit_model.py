"""Growth Codes v6 benefits, invite batches, and counter ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class GrowthCodeBenefitModel(Base):
    """Typed post-settlement benefit attached to a growth code or policy version."""

    __tablename__ = "growth_code_benefits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    benefit_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    merge_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="append", server_default="append")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    eligibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
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


class GrowthBenefitFulfillmentModel(Base):
    """Idempotent benefit side-effect ledger keyed by payment and benefit."""

    __tablename__ = "growth_benefit_fulfillments"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_growth_benefit_fulfillments_attempt_count_non_negative"),
        UniqueConstraint("idempotency_key", name="uq_growth_benefit_fulfillments_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benefit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_code_benefits.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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


class InviteBatchModel(Base):
    """Batch record for multi-invite issuance from benefits or admin grants."""

    __tablename__ = "invite_batches"
    __table_args__ = (
        CheckConstraint("requested_count > 0", name="ck_invite_batches_requested_count_positive"),
        CheckConstraint("issued_count >= 0", name="ck_invite_batches_issued_count_non_negative"),
        CheckConstraint("issued_count <= requested_count", name="ck_invite_batches_issued_lte_requested"),
        CheckConstraint("friend_days >= 0", name="ck_invite_batches_friend_days_non_negative"),
        CheckConstraint(
            "expiry_mode IN ('none', 'relative', 'absolute')",
            name="ck_invite_batches_expiry_mode",
        ),
        CheckConstraint(
            "grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_batches_grant_duration_mode",
        ),
        CheckConstraint(
            "child_grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_batches_child_grant_duration_mode",
        ),
        CheckConstraint(
            "child_invite_expiry_mode IN ('relative','absolute','none')",
            name="ck_invite_batches_child_expiry_mode",
        ),
        CheckConstraint(
            "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
            "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
            name="ck_invite_batches_device_override_positive",
        ),
        UniqueConstraint("idempotency_key", name="uq_invite_batches_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invite_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invite_campaign_version_id: Mapped[uuid.UUID | None] = mapped_column(
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
    root_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    batch_kind: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="legacy",
        server_default="legacy",
        index=True,
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
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    friend_days: Mapped[int] = mapped_column(Integer, nullable=False)
    expiry_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entitlement_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    entitlement_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entitlement_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
    grant_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
    child_grant_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_invite_expiry_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="relative",
        server_default="relative",
    )
    child_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    redemption_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    issue_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
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


class GrowthCodeUserCounterModel(Base):
    """Per-user reservation and consumption counters for code caps."""

    __tablename__ = "growth_code_user_counters"
    __table_args__ = (
        PrimaryKeyConstraint("growth_code_id", "user_id", name="pk_growth_code_user_counters"),
        CheckConstraint("reserved_uses >= 0", name="ck_growth_code_user_counters_reserved_non_negative"),
        CheckConstraint("consumed_uses >= 0", name="ck_growth_code_user_counters_consumed_non_negative"),
    )

    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reserved_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consumed_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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


class GrowthCodeCapacityCounterModel(Base):
    """Hashed non-user reservation and consumption counters for risk/device/velocity caps."""

    __tablename__ = "growth_code_capacity_counters"
    __table_args__ = (
        PrimaryKeyConstraint(
            "growth_code_id",
            "capacity_dimension",
            "capacity_key_hash",
            name="pk_growth_code_capacity_counters",
        ),
        CheckConstraint(
            "capacity_dimension IN ('risk_subject', 'device', 'velocity')",
            name="ck_growth_code_capacity_counters_dimension",
        ),
        CheckConstraint("reserved_uses >= 0", name="ck_growth_code_capacity_counters_reserved_non_negative"),
        CheckConstraint("consumed_uses >= 0", name="ck_growth_code_capacity_counters_consumed_non_negative"),
    )

    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    capacity_dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    capacity_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    reserved_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consumed_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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
