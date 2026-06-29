"""Flexible invite campaign, redemption ledger, and tree ORM models."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.session import Base


class InviteCampaignModel(Base):
    """Admin-managed flexible invite campaign."""

    __tablename__ = "invite_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','scheduled','active','paused','archived')",
            name="ck_invite_campaigns_status",
        ),
        CheckConstraint(
            "owner_mode IN "
            "('system','selected_user','uploaded_user_list','admin_pool','customer_owned','partner_owned')",
            name="ck_invite_campaigns_owner_mode",
        ),
        UniqueConstraint("campaign_key", name="uq_invite_campaigns_campaign_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft", index=True)
    owner_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="selected_user",
        server_default="selected_user",
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaign_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    allowed_surfaces: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_geos: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    export_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notification_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    caps: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class InviteCampaignVersionModel(Base):
    """Immutable-ish invite campaign policy snapshot."""

    __tablename__ = "invite_campaign_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','submitted','approved','published','rolled_back')",
            name="ck_invite_campaign_versions_status",
        ),
        CheckConstraint(
            "grant_mode IN ('legacy_invite_access','plan_snapshot','custom_snapshot')",
            name="ck_invite_campaign_versions_grant_mode",
        ),
        CheckConstraint("version >= 1", name="ck_invite_campaign_versions_version_positive"),
        CheckConstraint("child_invite_count >= 0", name="ck_invite_campaign_versions_child_count_non_negative"),
        CheckConstraint("max_generation_depth >= 0", name="ck_invite_campaign_versions_max_depth_non_negative"),
        CheckConstraint(
            "grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_campaign_versions_grant_duration_mode",
        ),
        CheckConstraint(
            "child_grant_duration_mode IN ('fixed_days','lifetime')",
            name="ck_invite_campaign_versions_child_grant_duration_mode",
        ),
        CheckConstraint(
            "root_invite_expiry_mode IN ('relative','absolute','none')",
            name="ck_invite_campaign_versions_root_expiry_mode",
        ),
        CheckConstraint(
            "child_invite_expiry_mode IN ('relative','absolute','none')",
            name="ck_invite_campaign_versions_child_expiry_mode",
        ),
        CheckConstraint(
            "(grant_device_limit_override IS NULL OR grant_device_limit_override > 0) "
            "AND (child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0)",
            name="ck_invite_campaign_versions_device_override_positive",
        ),
        UniqueConstraint("campaign_id", "version", name="uq_invite_campaign_versions_campaign_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft", index=True)
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
    root_invite_expiry_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="relative",
        server_default="relative",
    )
    root_invite_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    child_invite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    child_invite_free_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    child_invite_expiry_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    child_invite_expiry_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="relative",
        server_default="relative",
    )
    child_invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    child_grant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    max_generation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    block_self_redemption: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    require_no_active_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    allowed_surfaces: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    risk_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    redemption_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    child_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    issue_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    export_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notification_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submitted_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class InviteRedemptionModel(Base):
    """Durable invite redemption ledger."""

    __tablename__ = "invite_redemptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('redeemed','blocked','reversed')",
            name="ck_invite_redemptions_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_invite_redemptions_idempotency_key"),
        Index(
            "uq_invite_redemptions_redeemed_invite_code_id",
            "invite_code_id",
            unique=True,
            postgresql_where=text("status = 'redeemed'"),
            sqlite_where=text("status = 'redeemed'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="RESTRICT"),
        nullable=False,
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
    inviter_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invitee_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    generation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    source_surface: Mapped[str] = mapped_column(String(30), nullable=False, default="web", server_default="web")
    entitlement_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("entitlement_grants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    granted_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    granted_plan_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    granted_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    child_issued_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="redeemed", server_default="redeemed")
    blocked_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    risk_decision: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    grant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    service_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class InviteTreeEdgeModel(Base):
    """One redeemed invite edge in the invite tree."""

    __tablename__ = "invite_tree_edges"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','blocked','reversed')",
            name="ck_invite_tree_edges_status",
        ),
        UniqueConstraint("redemption_id", name="uq_invite_tree_edges_redemption_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    root_invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_invite_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    redeemed_invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    redemption_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_redemptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaign_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    child_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    granted_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    granted_plan_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    inviter_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invitee_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mobile_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    generation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
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


class InviteTreeClosureModel(Base):
    """Closure table for invite tree ancestry queries."""

    __tablename__ = "invite_tree_closure"
    __table_args__ = (
        CheckConstraint("depth >= 0", name="ck_invite_tree_closure_depth_non_negative"),
        UniqueConstraint(
            "root_invite_code_id",
            "ancestor_invite_code_id",
            "descendant_invite_code_id",
            name="uq_invite_tree_closure_path",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    root_invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ancestor_invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    descendant_invite_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class InviteCampaignDailyRollupModel(Base):
    """Daily invite campaign operational rollup."""

    __tablename__ = "invite_campaign_daily_rollups"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "rollup_date",
            "plan_code",
            "source_surface",
            "generation_depth",
            name="uq_invite_campaign_daily_rollups_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invite_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invite_campaign_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rollup_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plan_code: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown", server_default="unknown")
    source_surface: Mapped[str] = mapped_column(String(30), nullable=False, default="all", server_default="all")
    generation_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    issued_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    redeemed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    expired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    revoked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    active_vpn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    child_issued_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
