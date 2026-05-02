"""Canonical customer growth code registry and lifecycle ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base
from src.infrastructure.database.types.encrypted_text import EncryptedText


class GrowthCodeModel(Base):
    __tablename__ = "growth_codes"
    __table_args__ = (
        UniqueConstraint("code_hash", "code_type", name="uq_growth_codes_hash_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    code_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    issuer_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    issuer_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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


class GrowthCodeIssuanceModel(Base):
    __tablename__ = "growth_code_issuances"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issuance_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    issued_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issued_to_partner_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partner_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issued_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
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
    source_plan_sku: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_code_encrypted: Mapped[str | None] = mapped_column(EncryptedText(), nullable=True)
    source_bundle_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class GrowthCodeTouchpointModel(Base):
    __tablename__ = "growth_code_touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    anonymous_session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    registered_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    surface: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    channel: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    click_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sub_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    converted_to_signup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    converted_to_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class GrowthSignupAttributionModel(Base):
    __tablename__ = "growth_signup_attributions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_growth_signup_attributions_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    touchpoint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_code_touchpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribution_source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    storefront_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storefronts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_realm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_realms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("risk_subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class InviteCodePolicyModel(Base):
    __tablename__ = "invite_code_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    friend_days: Mapped[int] = mapped_column(Integer, nullable=False)
    entitlement_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    conversion_reward_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    self_redemption_block: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    risk_ruleset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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


class ReferralProgramPolicyModel(Base):
    __tablename__ = "referral_program_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )
    program_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    friend_discount_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    friend_discount_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    eligible_durations: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    eligible_plan_families: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reward_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reward_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    hold_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_cap: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    lifetime_cap: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    anti_abuse_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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


class PromoCodePolicyModel(Base):
    __tablename__ = "promo_code_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    max_discount_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    eligible_plan_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    eligible_plan_families: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    eligible_durations: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    eligible_addons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_checkout_modes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_geos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    min_net_paid_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    usage_cap_per_user: Mapped[int | None] = mapped_column(Integer, nullable=True)
    global_usage_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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


class GiftCodePolicyModel(Base):
    __tablename__ = "gift_code_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    grant_type: Mapped[str] = mapped_column(String(40), nullable=False)
    plan_family: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entitlement_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    redemption_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transferable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
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


class GrowthCodeResolutionEventModel(Base):
    __tablename__ = "growth_code_resolution_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_code_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_session_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    checkout_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    surface: Mapped[str] = mapped_column(String(40), nullable=False, default="api", server_default="api", index=True)
    action_context: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    conflict_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )


class GrowthCodeReservationModel(Base):
    __tablename__ = "growth_code_reservations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quote_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checkout_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="reserved",
        server_default="reserved",
        index=True,
    )
    consumed_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    release_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
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


class GrowthCodeRedemptionModel(Base):
    __tablename__ = "growth_code_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    growth_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("growth_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    redeemer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    beneficiary_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entitlement_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entitlement_grants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_allocation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="redeemed",
        server_default="redeemed",
        index=True,
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
