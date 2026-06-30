"""Use cases for flexible invite campaign administration."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.application.use_cases.invites.lifetime_policy import (
    INVITE_DURATION_LIFETIME,
    INVITE_EXPIRY_CAMPAIGN_DEFAULT,
    INVITE_EXPIRY_RELATIVE,
    display_days_for_duration,
    is_lifetime_duration,
    normalize_invite_duration_mode,
    normalize_invite_expiry_mode,
    resolve_invite_expiry,
    resolve_invite_grant,
)
from src.config.settings import settings
from src.infrastructure.database.models.growth_benefit_model import InviteBatchModel
from src.infrastructure.database.models.invite_campaign_model import (
    InviteCampaignModel,
    InviteCampaignVersionModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import observe_lifetime_invite_campaign_created

INVITE_USAGE_SINGLE = "single_use"
INVITE_USAGE_MULTI = "multi_use"
INVITE_USAGE_CAMPAIGN_DEFAULT = "campaign_default"
MULTI_USE_PRACTICAL_HARD_CAP = 1_000_000


@dataclass(frozen=True)
class CreateInviteCampaignCommand:
    campaign_key: str
    name: str
    description: str | None
    owner_mode: str
    starts_at: datetime | None
    expires_at: datetime | None
    allowed_surfaces: list[str]
    allowed_geos: list[str]
    allowed_markets: list[str]
    allowed_segments: list[str]
    risk_policy_key: str | None
    grant_plan_id: UUID | None
    grant_plan_code: str | None
    grant_duration_mode: str
    grant_duration_days: int | None
    grant_device_limit_override: int | None
    root_invite_expiry_mode: str
    root_invite_expiry_days: int | None
    root_invite_expires_at: datetime | None
    root_usage_mode: str
    root_max_redemptions: int | None
    root_per_user_redemption_cap: int
    child_grant_plan_id: UUID | None
    child_grant_plan_code: str | None
    child_grant_duration_mode: str
    child_grant_duration_days: int | None
    child_grant_device_limit_override: int | None
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_mode: str
    child_invite_expiry_days: int | None
    child_invite_expires_at: datetime | None
    child_usage_mode: str
    child_max_redemptions: int | None
    child_per_user_redemption_cap: int
    max_generation_depth: int
    require_no_active_access: bool
    block_self_redemption: bool
    risk_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
    caps: dict[str, Any]
    multi_use_policy: dict[str, Any]
    multi_use_acknowledgement: bool
    lifetime_campaign_acknowledgement: bool
    publish: bool
    reason: str | None


@dataclass(frozen=True)
class CreateInviteCampaignBatchCommand:
    campaign_id: UUID
    owner_user_id: UUID | None
    owner_user_ids: tuple[UUID, ...]
    count: int
    version_id: UUID | None
    idempotency_key: str | None
    expiry_mode: str
    expires_at: datetime | None
    expiry_days: int | None
    usage_mode: str
    max_redemptions_per_code: int | None
    per_user_redemption_cap: int | None
    reason: str


@dataclass(frozen=True)
class CreateInviteCampaignVersionCommand:
    grant_plan_id: UUID | None
    grant_plan_code: str | None
    grant_duration_mode: str
    grant_duration_days: int | None
    grant_device_limit_override: int | None
    root_invite_expiry_mode: str
    root_invite_expiry_days: int | None
    root_invite_expires_at: datetime | None
    root_usage_mode: str
    root_max_redemptions: int | None
    root_per_user_redemption_cap: int
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_mode: str
    child_invite_expiry_days: int | None
    child_invite_expires_at: datetime | None
    child_usage_mode: str
    child_max_redemptions: int | None
    child_per_user_redemption_cap: int
    child_grant_plan_id: UUID | None
    child_grant_plan_code: str | None
    child_grant_duration_mode: str
    child_grant_duration_days: int | None
    child_grant_device_limit_override: int | None
    max_generation_depth: int
    require_no_active_access: bool
    block_self_redemption: bool
    allowed_surfaces: list[str]
    risk_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
    caps: dict[str, Any]
    multi_use_policy: dict[str, Any]
    multi_use_acknowledgement: bool
    lifetime_campaign_acknowledgement: bool
    reason: str | None


@dataclass(frozen=True)
class ValidateInviteCampaignVersionResult:
    version_id: UUID
    checksum: str
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class InviteCampaignBatchResult:
    campaign: InviteCampaignModel
    version: InviteCampaignVersionModel
    batch: InviteBatchModel
    raw_codes: tuple[str, ...]


class CreateInviteCampaignUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plans = SubscriptionPlanRepository(session)

    async def execute(self, *, command: CreateInviteCampaignCommand, admin_user_id: UUID) -> InviteCampaignModel:
        existing = await self._session.execute(
            select(InviteCampaignModel).where(InviteCampaignModel.campaign_key == command.campaign_key)
        )
        if existing.scalars().first() is not None:
            raise ValueError("Invite campaign key already exists")

        now = datetime.now(UTC)
        grant_duration_mode = normalize_invite_duration_mode(command.grant_duration_mode)
        child_grant_duration_mode = normalize_invite_duration_mode(command.child_grant_duration_mode)
        root_invite_expiry_mode = normalize_invite_expiry_mode(command.root_invite_expiry_mode)
        child_invite_expiry_mode = normalize_invite_expiry_mode(command.child_invite_expiry_mode)
        root_usage_mode = _normalize_invite_usage_mode(command.root_usage_mode)
        child_usage_mode = _normalize_invite_usage_mode(command.child_usage_mode)
        root_max_redemptions = _normalize_invite_max_redemptions(
            usage_mode=root_usage_mode,
            max_redemptions=command.root_max_redemptions,
            acknowledgement=command.multi_use_acknowledgement,
        )
        child_max_redemptions = _normalize_invite_max_redemptions(
            usage_mode=child_usage_mode,
            max_redemptions=command.child_max_redemptions,
            acknowledgement=command.multi_use_acknowledgement,
        )
        root_per_user_redemption_cap = _normalize_per_user_cap(command.root_per_user_redemption_cap)
        child_per_user_redemption_cap = _normalize_per_user_cap(command.child_per_user_redemption_cap)
        multi_use_policy = dict(command.multi_use_policy or {})
        if root_usage_mode == INVITE_USAGE_MULTI or child_usage_mode == INVITE_USAGE_MULTI:
            multi_use_policy = _validate_multi_use_campaign_policy(
                risk_policy=command.risk_policy,
                caps=command.caps,
                max_generation_depth=command.max_generation_depth,
                acknowledgement=command.multi_use_acknowledgement,
                policy=multi_use_policy,
            )
        _validate_lifetime_campaign_policy(
            grant_duration_mode=grant_duration_mode,
            child_grant_duration_mode=child_grant_duration_mode,
            child_invite_count=command.child_invite_count,
            max_generation_depth=command.max_generation_depth,
            require_no_active_access=command.require_no_active_access,
            block_self_redemption=command.block_self_redemption,
            root_invite_expiry_mode=root_invite_expiry_mode,
            child_invite_expiry_mode=child_invite_expiry_mode,
            campaign_expires_at=command.expires_at,
            caps=command.caps,
            risk_policy=command.risk_policy,
            lifetime_campaign_acknowledgement=command.lifetime_campaign_acknowledgement,
        )

        plan = await self._resolve_plan(command.grant_plan_id, command.grant_plan_code)
        base_grant_snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=None, status="active")
        grant_resolution = resolve_invite_grant(
            snapshot={**base_grant_snapshot, "source_type": "invite_campaign"},
            duration_mode=grant_duration_mode,
            duration_days=command.grant_duration_days,
            granted_at=now,
            device_limit_override=command.grant_device_limit_override,
        )
        grant_snapshot = grant_resolution.snapshot
        child_plan = plan
        child_duration_days = (
            None
            if child_grant_duration_mode == INVITE_DURATION_LIFETIME
            else int(command.child_grant_duration_days or command.child_invite_free_days)
        )
        child_display_days = display_days_for_duration(child_grant_duration_mode, child_duration_days)
        child_snapshot = dict(grant_snapshot)
        child_device_limit_override = command.child_grant_device_limit_override
        if command.child_invite_count > 0:
            child_plan = await self._resolve_plan(
                command.child_grant_plan_id,
                command.child_grant_plan_code or command.grant_plan_code,
            )
            base_child_snapshot = EntitlementsService.build_snapshot(plan=child_plan, expires_at=None, status="active")
            child_resolution = resolve_invite_grant(
                snapshot={**base_child_snapshot, "source_type": "invite_campaign_child"},
                duration_mode=child_grant_duration_mode,
                duration_days=child_duration_days,
                granted_at=now,
                device_limit_override=child_device_limit_override,
            )
            child_snapshot = child_resolution.snapshot
            child_display_days = child_resolution.display_days
        allowed_surfaces = _safe_surfaces(command.allowed_surfaces)
        allowed_geos = _safe_geo_policy(
            countries=command.allowed_geos,
            markets=command.allowed_markets,
            segments=command.allowed_segments,
        )
        risk_policy = dict(command.risk_policy)
        if command.risk_policy_key:
            risk_policy["risk_policy_key"] = command.risk_policy_key
        status = "active" if command.publish else "draft"

        campaign = InviteCampaignModel(
            id=uuid.uuid4(),
            campaign_key=command.campaign_key,
            name=command.name,
            description=command.description,
            status=status,
            owner_mode=command.owner_mode,
            starts_at=command.starts_at,
            expires_at=command.expires_at,
            allowed_surfaces=allowed_surfaces,
            allowed_geos=allowed_geos,
            risk_policy=risk_policy,
            export_policy=dict(command.export_policy),
            notification_policy=dict(command.notification_policy),
            caps=dict(command.caps),
            metadata_json={"created_reason": command.reason},
            created_by_admin_id=admin_user_id,
            updated_by_admin_id=admin_user_id,
            published_at=now if command.publish else None,
        )
        self._session.add(campaign)
        await self._session.flush()

        grant_duration_days = (
            None if grant_duration_mode == INVITE_DURATION_LIFETIME else int(command.grant_duration_days or 1)
        )
        root_invite_expiry_days = (
            command.root_invite_expiry_days if root_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )
        child_invite_expiry_days = (
            command.child_invite_expiry_days if child_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )
        child_policy_expiry_days = (
            command.child_invite_expiry_days if child_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )

        version = InviteCampaignVersionModel(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            version=1,
            status="published" if command.publish else "draft",
            grant_mode="plan_snapshot",
            grant_plan_id=plan.id,
            grant_duration_mode=grant_duration_mode,
            grant_duration_days=grant_duration_days,
            grant_device_limit_override=command.grant_device_limit_override,
            grant_snapshot=grant_snapshot,
            root_invite_expiry_mode=root_invite_expiry_mode,
            root_invite_expiry_days=root_invite_expiry_days,
            root_invite_expires_at=command.root_invite_expires_at if root_invite_expiry_mode == "absolute" else None,
            root_usage_mode=root_usage_mode,
            root_max_redemptions=root_max_redemptions,
            root_per_user_redemption_cap=root_per_user_redemption_cap,
            child_invite_count=int(command.child_invite_count),
            child_invite_free_days=child_display_days,
            child_invite_expiry_days=child_invite_expiry_days,
            child_invite_expiry_mode=child_invite_expiry_mode,
            child_invite_expires_at=command.child_invite_expires_at if child_invite_expiry_mode == "absolute" else None,
            child_usage_mode=child_usage_mode,
            child_max_redemptions=child_max_redemptions,
            child_per_user_redemption_cap=child_per_user_redemption_cap,
            child_grant_plan_id=child_plan.id if command.child_invite_count > 0 else None,
            child_grant_duration_mode=child_grant_duration_mode,
            child_grant_duration_days=child_duration_days if command.child_invite_count > 0 else None,
            child_grant_device_limit_override=child_device_limit_override if command.child_invite_count > 0 else None,
            child_grant_snapshot=child_snapshot if command.child_invite_count > 0 else {},
            max_generation_depth=int(command.max_generation_depth),
            block_self_redemption=command.block_self_redemption,
            require_no_active_access=command.require_no_active_access,
            allowed_surfaces=allowed_surfaces,
            risk_policy=risk_policy,
            multi_use_policy=multi_use_policy,
            redemption_policy={
                "allowed_surfaces": allowed_surfaces,
                "require_no_active_access": command.require_no_active_access,
                "block_self_redemption": command.block_self_redemption,
                "per_user_redeem_cap": root_per_user_redemption_cap,
            },
            child_policy={
                "count": int(command.child_invite_count),
                "friend_days": child_display_days,
                "usage_mode": child_usage_mode,
                "max_redemptions": child_max_redemptions,
                "per_user_redemption_cap": child_per_user_redemption_cap,
                "multi_use_policy": multi_use_policy,
                "grant_plan_id": str(child_plan.id) if command.child_invite_count > 0 else None,
                "grant_plan_code": child_plan.plan_code if command.child_invite_count > 0 else None,
                "grant_duration_mode": child_grant_duration_mode,
                "grant_duration_days": child_duration_days if command.child_invite_count > 0 else None,
                "grant_device_limit_override": child_device_limit_override if command.child_invite_count > 0 else None,
                "grant_snapshot": child_snapshot if command.child_invite_count > 0 else {},
                "expiry_mode": child_invite_expiry_mode,
                "expiry_days": child_policy_expiry_days,
                "expires_at": command.child_invite_expires_at.isoformat()
                if child_invite_expiry_mode == "absolute" and command.child_invite_expires_at
                else None,
                "max_generation_depth": int(command.max_generation_depth),
                "issue_timing": "immediately",
            },
            issue_policy={
                "root_batch_kind": "root_campaign",
                "raw_codes_one_time": True,
                "root_invite_expiry_mode": root_invite_expiry_mode,
                "root_invite_expiry_days": command.root_invite_expiry_days,
                "root_usage_mode": root_usage_mode,
                "root_max_redemptions": root_max_redemptions,
                "root_per_user_redemption_cap": root_per_user_redemption_cap,
                "lifetime_campaign_acknowledgement": command.lifetime_campaign_acknowledgement,
                "multi_use_acknowledgement": command.multi_use_acknowledgement,
            },
            export_policy=dict(command.export_policy),
            notification_policy=dict(command.notification_policy),
            checksum=_version_checksum(
                {
                    "campaign_key": command.campaign_key,
                    "grant_plan_id": str(plan.id),
                    "grant_duration_mode": grant_duration_mode,
                    "grant_duration_days": command.grant_duration_days,
                    "grant_device_limit_override": command.grant_device_limit_override,
                    "root_invite_expiry_mode": root_invite_expiry_mode,
                    "root_invite_expiry_days": command.root_invite_expiry_days,
                    "root_invite_expires_at": command.root_invite_expires_at,
                    "root_usage_mode": root_usage_mode,
                    "root_max_redemptions": root_max_redemptions,
                    "root_per_user_redemption_cap": root_per_user_redemption_cap,
                    "child_invite_count": command.child_invite_count,
                    "child_invite_free_days": child_display_days,
                    "child_usage_mode": child_usage_mode,
                    "child_max_redemptions": child_max_redemptions,
                    "child_per_user_redemption_cap": child_per_user_redemption_cap,
                    "child_grant_plan_id": str(child_plan.id) if command.child_invite_count > 0 else None,
                    "child_grant_duration_mode": child_grant_duration_mode,
                    "child_grant_duration_days": child_duration_days if command.child_invite_count > 0 else None,
                    "child_grant_device_limit_override": child_device_limit_override,
                    "child_invite_expiry_mode": child_invite_expiry_mode,
                    "child_invite_expiry_days": command.child_invite_expiry_days,
                    "child_invite_expires_at": command.child_invite_expires_at,
                    "max_generation_depth": command.max_generation_depth,
                    "allowed_surfaces": allowed_surfaces,
                    "allowed_geos": allowed_geos,
                    "risk_policy": risk_policy,
                    "multi_use_policy": multi_use_policy,
                    "export_policy": command.export_policy,
                }
            ),
            created_by_admin_id=admin_user_id,
            published_by_admin_id=admin_user_id if command.publish else None,
            published_at=now if command.publish else None,
        )
        self._session.add(version)
        await self._session.flush()
        if grant_duration_mode == INVITE_DURATION_LIFETIME or child_grant_duration_mode == INVITE_DURATION_LIFETIME:
            observe_lifetime_invite_campaign_created(
                plan_code=str(grant_snapshot.get("plan_code") or plan.plan_code),
                root_expiry_mode=root_invite_expiry_mode,
                child_expiry_mode=child_invite_expiry_mode,
                result="created",
            )
        campaign.current_version_id = version.id
        await self._session.flush()
        if command.publish:
            validation = await ValidateInviteCampaignVersionUseCase(self._session).execute(
                campaign_id=campaign.id,
                version_id=version.id,
            )
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
        return campaign

    async def _resolve_plan(self, plan_id: UUID | None, plan_code: str | None):
        if plan_id is not None:
            plan = await self._plans.get_by_id(plan_id)
        else:
            plan = await self._plans.get_by_plan_code(plan_code or "premium_smart_ru", duration_days=365)
            if plan is None:
                plan = await self._plans.get_by_plan_code(plan_code or "premium_smart_ru")
        if plan is None:
            raise ValueError("Invite campaign grant plan was not found")
        if not plan.is_active:
            raise ValueError("Invite campaign grant plan is inactive")
        return plan


class CreateInviteCampaignVersionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plans = SubscriptionPlanRepository(session)

    async def execute(
        self,
        *,
        campaign_id: UUID,
        command: CreateInviteCampaignVersionCommand,
        admin_user_id: UUID,
    ) -> InviteCampaignVersionModel:
        campaign = await self._session.get(InviteCampaignModel, campaign_id)
        if campaign is None:
            raise ValueError("Invite campaign was not found")
        if campaign.status == "archived":
            raise ValueError("Archived invite campaigns cannot receive new versions")

        latest = await self._session.execute(
            select(func.max(InviteCampaignVersionModel.version)).where(
                InviteCampaignVersionModel.campaign_id == campaign_id
            )
        )
        version_number = int(latest.scalar_one() or 0) + 1
        version = await self._build_version(
            campaign=campaign,
            version_number=version_number,
            command=command,
            admin_user_id=admin_user_id,
        )
        self._session.add(version)
        if command.caps:
            campaign.caps = {**dict(campaign.caps or {}), **dict(command.caps or {})}
        campaign.updated_by_admin_id = admin_user_id
        campaign.metadata_json = {**dict(campaign.metadata_json or {}), "last_version_reason": command.reason}
        await self._session.flush()
        if is_lifetime_duration(version.grant_duration_mode) or is_lifetime_duration(version.child_grant_duration_mode):
            observe_lifetime_invite_campaign_created(
                plan_code=str((version.grant_snapshot or {}).get("plan_code") or "unknown"),
                root_expiry_mode=version.root_invite_expiry_mode,
                child_expiry_mode=version.child_invite_expiry_mode,
                result="version_created",
            )
        return version

    async def _build_version(
        self,
        *,
        campaign: InviteCampaignModel,
        version_number: int,
        command: CreateInviteCampaignVersionCommand,
        admin_user_id: UUID,
    ) -> InviteCampaignVersionModel:
        now = datetime.now(UTC)
        grant_duration_mode = normalize_invite_duration_mode(command.grant_duration_mode)
        child_grant_duration_mode = normalize_invite_duration_mode(command.child_grant_duration_mode)
        root_invite_expiry_mode = normalize_invite_expiry_mode(command.root_invite_expiry_mode)
        child_invite_expiry_mode = normalize_invite_expiry_mode(command.child_invite_expiry_mode)
        merged_caps = {**dict(campaign.caps or {}), **dict(command.caps or {})}
        root_usage_mode = _normalize_invite_usage_mode(command.root_usage_mode)
        child_usage_mode = _normalize_invite_usage_mode(command.child_usage_mode)
        root_max_redemptions = _normalize_invite_max_redemptions(
            usage_mode=root_usage_mode,
            max_redemptions=command.root_max_redemptions,
            acknowledgement=command.multi_use_acknowledgement,
        )
        child_max_redemptions = _normalize_invite_max_redemptions(
            usage_mode=child_usage_mode,
            max_redemptions=command.child_max_redemptions,
            acknowledgement=command.multi_use_acknowledgement,
        )
        root_per_user_redemption_cap = _normalize_per_user_cap(command.root_per_user_redemption_cap)
        child_per_user_redemption_cap = _normalize_per_user_cap(command.child_per_user_redemption_cap)
        multi_use_policy = dict(command.multi_use_policy or {})
        if root_usage_mode == INVITE_USAGE_MULTI or child_usage_mode == INVITE_USAGE_MULTI:
            multi_use_policy = _validate_multi_use_campaign_policy(
                risk_policy=command.risk_policy,
                caps=merged_caps,
                max_generation_depth=command.max_generation_depth,
                acknowledgement=command.multi_use_acknowledgement,
                policy=multi_use_policy,
            )
        _validate_lifetime_campaign_policy(
            grant_duration_mode=grant_duration_mode,
            child_grant_duration_mode=child_grant_duration_mode,
            child_invite_count=command.child_invite_count,
            max_generation_depth=command.max_generation_depth,
            require_no_active_access=command.require_no_active_access,
            block_self_redemption=command.block_self_redemption,
            root_invite_expiry_mode=root_invite_expiry_mode,
            child_invite_expiry_mode=child_invite_expiry_mode,
            campaign_expires_at=campaign.expires_at,
            caps=merged_caps,
            risk_policy=command.risk_policy,
            lifetime_campaign_acknowledgement=command.lifetime_campaign_acknowledgement,
        )

        plan = await _resolve_plan(self._plans, command.grant_plan_id, command.grant_plan_code)
        base_grant_snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=None, status="active")
        grant_resolution = resolve_invite_grant(
            snapshot={**base_grant_snapshot, "source_type": "invite_campaign"},
            duration_mode=grant_duration_mode,
            duration_days=command.grant_duration_days,
            granted_at=now,
            device_limit_override=command.grant_device_limit_override,
        )
        grant_snapshot = grant_resolution.snapshot

        child_plan = None
        child_snapshot: dict[str, Any] = {}
        child_duration_days = (
            None
            if child_grant_duration_mode == INVITE_DURATION_LIFETIME
            else command.child_grant_duration_days or command.child_invite_free_days
        )
        child_display_days = display_days_for_duration(child_grant_duration_mode, child_duration_days)
        if command.child_invite_count > 0:
            child_plan = await _resolve_plan(
                self._plans,
                command.child_grant_plan_id,
                command.child_grant_plan_code or command.grant_plan_code,
            )
            base_child_snapshot = EntitlementsService.build_snapshot(plan=child_plan, expires_at=None, status="active")
            child_resolution = resolve_invite_grant(
                snapshot={**base_child_snapshot, "source_type": "invite_campaign_child"},
                duration_mode=child_grant_duration_mode,
                duration_days=child_duration_days,
                granted_at=now,
                device_limit_override=command.child_grant_device_limit_override,
            )
            child_snapshot = child_resolution.snapshot
            child_display_days = child_resolution.display_days

        allowed_surfaces = _safe_surfaces(command.allowed_surfaces)
        redemption_policy = {
            "allowed_surfaces": allowed_surfaces,
            "require_no_active_access": command.require_no_active_access,
            "block_self_redemption": command.block_self_redemption,
            "per_user_redeem_cap": root_per_user_redemption_cap,
        }
        child_policy_grant_duration_days = (
            int(child_duration_days) if child_plan is not None and child_duration_days else None
        )
        child_policy_device_limit_override = (
            command.child_grant_device_limit_override if child_plan is not None else None
        )
        child_policy_expiry_days = (
            command.child_invite_expiry_days if child_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )
        child_policy = {
            "enabled": command.child_invite_count > 0,
            "count": int(command.child_invite_count),
            "friend_days": child_display_days,
            "usage_mode": child_usage_mode,
            "max_redemptions": child_max_redemptions,
            "per_user_redemption_cap": child_per_user_redemption_cap,
            "multi_use_policy": multi_use_policy,
            "grant_plan_id": str(child_plan.id) if child_plan is not None else None,
            "grant_plan_code": child_plan.plan_code if child_plan is not None else None,
            "grant_duration_mode": child_grant_duration_mode,
            "grant_duration_days": child_policy_grant_duration_days,
            "grant_device_limit_override": child_policy_device_limit_override,
            "grant_snapshot": child_snapshot,
            "expiry_mode": child_invite_expiry_mode,
            "expiry_days": child_policy_expiry_days,
            "expires_at": command.child_invite_expires_at.isoformat()
            if child_invite_expiry_mode == "absolute" and command.child_invite_expires_at
            else None,
            "max_generation_depth": int(command.max_generation_depth),
            "issue_timing": "immediately",
        }
        checksum_payload = {
            "campaign_key": campaign.campaign_key,
            "version": version_number,
            "grant_plan_id": str(plan.id),
            "grant_duration_mode": grant_duration_mode,
            "grant_duration_days": command.grant_duration_days,
            "grant_device_limit_override": command.grant_device_limit_override,
            "root_invite_expiry_mode": root_invite_expiry_mode,
            "root_invite_expiry_days": command.root_invite_expiry_days,
            "root_invite_expires_at": command.root_invite_expires_at,
            "root_usage_mode": root_usage_mode,
            "root_max_redemptions": root_max_redemptions,
            "root_per_user_redemption_cap": root_per_user_redemption_cap,
            "child_invite_count": command.child_invite_count,
            "child_usage_mode": child_usage_mode,
            "child_max_redemptions": child_max_redemptions,
            "child_per_user_redemption_cap": child_per_user_redemption_cap,
            "child_grant_plan_id": str(child_plan.id) if child_plan is not None else None,
            "child_grant_duration_mode": child_grant_duration_mode,
            "child_grant_duration_days": int(child_duration_days) if child_plan is not None else None,
            "child_grant_device_limit_override": command.child_grant_device_limit_override,
            "child_invite_expiry_mode": child_invite_expiry_mode,
            "child_invite_expiry_days": command.child_invite_expiry_days,
            "child_invite_expires_at": command.child_invite_expires_at,
            "max_generation_depth": command.max_generation_depth,
            "allowed_surfaces": allowed_surfaces,
            "risk_policy": command.risk_policy,
            "multi_use_policy": multi_use_policy,
            "export_policy": command.export_policy,
            "caps": merged_caps,
        }
        grant_duration_days = (
            None if grant_duration_mode == INVITE_DURATION_LIFETIME else int(command.grant_duration_days or 1)
        )
        root_invite_expiry_days = (
            command.root_invite_expiry_days if root_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )
        child_invite_expiry_days = (
            command.child_invite_expiry_days if child_invite_expiry_mode == INVITE_EXPIRY_RELATIVE else None
        )
        return InviteCampaignVersionModel(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            version=version_number,
            status="draft",
            grant_mode="plan_snapshot",
            grant_plan_id=plan.id,
            grant_duration_mode=grant_duration_mode,
            grant_duration_days=grant_duration_days,
            grant_device_limit_override=command.grant_device_limit_override,
            grant_snapshot=grant_snapshot,
            root_invite_expiry_mode=root_invite_expiry_mode,
            root_invite_expiry_days=root_invite_expiry_days,
            root_invite_expires_at=command.root_invite_expires_at if root_invite_expiry_mode == "absolute" else None,
            root_usage_mode=root_usage_mode,
            root_max_redemptions=root_max_redemptions,
            root_per_user_redemption_cap=root_per_user_redemption_cap,
            child_invite_count=int(command.child_invite_count),
            child_invite_free_days=child_display_days,
            child_invite_expiry_days=child_invite_expiry_days,
            child_invite_expiry_mode=child_invite_expiry_mode,
            child_invite_expires_at=command.child_invite_expires_at if child_invite_expiry_mode == "absolute" else None,
            child_usage_mode=child_usage_mode,
            child_max_redemptions=child_max_redemptions,
            child_per_user_redemption_cap=child_per_user_redemption_cap,
            child_grant_plan_id=child_plan.id if child_plan is not None else None,
            child_grant_duration_mode=child_grant_duration_mode,
            child_grant_duration_days=child_policy_grant_duration_days,
            child_grant_device_limit_override=child_policy_device_limit_override,
            child_grant_snapshot=child_snapshot,
            max_generation_depth=int(command.max_generation_depth),
            block_self_redemption=command.block_self_redemption,
            require_no_active_access=command.require_no_active_access,
            allowed_surfaces=allowed_surfaces,
            risk_policy=dict(command.risk_policy),
            multi_use_policy=multi_use_policy,
            redemption_policy=redemption_policy,
            child_policy=child_policy,
            issue_policy={
                "root_batch_kind": "root_campaign",
                "raw_codes_one_time": True,
                "root_invite_expiry_mode": root_invite_expiry_mode,
                "root_invite_expiry_days": command.root_invite_expiry_days,
                "root_usage_mode": root_usage_mode,
                "root_max_redemptions": root_max_redemptions,
                "root_per_user_redemption_cap": root_per_user_redemption_cap,
                "lifetime_campaign_acknowledgement": command.lifetime_campaign_acknowledgement,
                "multi_use_acknowledgement": command.multi_use_acknowledgement,
            },
            export_policy=dict(command.export_policy),
            notification_policy=dict(command.notification_policy),
            checksum=_version_checksum(checksum_payload),
            created_by_admin_id=admin_user_id,
        )


class ValidateInviteCampaignVersionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, campaign_id: UUID, version_id: UUID) -> ValidateInviteCampaignVersionResult:
        campaign = await self._session.get(InviteCampaignModel, campaign_id)
        version = await self._session.get(InviteCampaignVersionModel, version_id)
        if campaign is None or version is None or version.campaign_id != campaign.id:
            raise ValueError("Invite campaign version was not found")

        errors: list[str] = []
        warnings: list[str] = []
        if version.grant_mode == "plan_snapshot" and version.grant_plan_id is None:
            errors.append("grant_plan_id is required for plan_snapshot invite campaigns")
        if version.child_invite_count > 0 and version.child_grant_plan_id is None:
            errors.append("child_grant_plan_id is required when child invites are enabled")
        if version.max_generation_depth > 12:
            errors.append("max_generation_depth exceeds the safe limit")
        max_child_invites = _positive_int((campaign.caps or {}).get("max_child_invites"), default=100)
        if version.child_invite_count > max_child_invites:
            errors.append("child_invite_count exceeds campaign cap")
        global_issue_cap = _optional_positive_int((campaign.caps or {}).get("global_issue_cap"))
        if global_issue_cap is None:
            global_issue_cap = _optional_positive_int((campaign.caps or {}).get("max_total_issued"))
        root_max_redemptions = _optional_positive_int(version.root_max_redemptions)
        if version.root_usage_mode == INVITE_USAGE_MULTI and root_max_redemptions and version.child_invite_count > 0:
            minimum_root_issues = 1
            projected_child_issues = root_max_redemptions * int(version.child_invite_count)
            recommended_issue_cap = minimum_root_issues + projected_child_issues
            if global_issue_cap is not None and global_issue_cap < recommended_issue_cap:
                warnings.append(
                    "global_issue_cap is lower than the minimum recommended root issue count plus "
                    "root_max_redemptions multiplied by child_invite_count"
                )
        if _policy_contains_raw_code(version.redemption_policy) or _policy_contains_raw_code(version.child_policy):
            errors.append("policy snapshot must not contain raw invite codes")
        if is_lifetime_duration(version.grant_duration_mode) and version.grant_duration_days is not None:
            errors.append("lifetime root grants must not store grant_duration_days")
        if is_lifetime_duration(version.child_grant_duration_mode) and version.child_grant_duration_days is not None:
            errors.append("lifetime child grants must not store child_grant_duration_days")
        try:
            _validate_lifetime_campaign_policy(
                grant_duration_mode=version.grant_duration_mode,
                child_grant_duration_mode=version.child_grant_duration_mode,
                child_invite_count=version.child_invite_count,
                max_generation_depth=version.max_generation_depth,
                require_no_active_access=version.require_no_active_access,
                block_self_redemption=version.block_self_redemption,
                root_invite_expiry_mode=version.root_invite_expiry_mode,
                child_invite_expiry_mode=version.child_invite_expiry_mode,
                campaign_expires_at=campaign.expires_at,
                caps=dict(campaign.caps or {}),
                risk_policy=dict(version.risk_policy or {}),
                lifetime_campaign_acknowledgement=bool(
                    (version.issue_policy or {}).get("lifetime_campaign_acknowledgement")
                ),
            )
        except ValueError as exc:
            errors.append(str(exc))
        if version.root_usage_mode == INVITE_USAGE_MULTI or version.child_usage_mode == INVITE_USAGE_MULTI:
            try:
                _validate_multi_use_campaign_policy(
                    risk_policy=dict(version.risk_policy or {}),
                    caps=dict(campaign.caps or {}),
                    max_generation_depth=int(version.max_generation_depth or 0),
                    acknowledgement=bool((version.issue_policy or {}).get("multi_use_acknowledgement")),
                    policy=dict(version.multi_use_policy or {}),
                )
                _normalize_invite_max_redemptions(
                    usage_mode=version.root_usage_mode,
                    max_redemptions=version.root_max_redemptions,
                    acknowledgement=bool((version.issue_policy or {}).get("multi_use_acknowledgement")),
                )
                _normalize_invite_max_redemptions(
                    usage_mode=version.child_usage_mode,
                    max_redemptions=version.child_max_redemptions,
                    acknowledgement=bool((version.issue_policy or {}).get("multi_use_acknowledgement")),
                )
            except ValueError as exc:
                errors.append(str(exc))

        plan_codes = {
            str((version.grant_snapshot or {}).get("plan_code") or ""),
            str((version.child_grant_snapshot or {}).get("plan_code") or ""),
        }
        smart_ru_codes = {item.strip() for item in settings.remnawave_smart_ru_plan_codes.split(",") if item.strip()}
        if plan_codes & smart_ru_codes:
            if not settings.remnawave_smart_ru_external_squad_uuid:
                errors.append("REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID is required for Premium Smart RU campaigns")
            if not settings.remnawave_smart_ru_internal_squad_uuid:
                errors.append("REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID is required for Premium Smart RU campaigns")
            if not settings.remnawave_smart_ru_subscription_template_name:
                errors.append(
                    "REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME is required for Premium Smart RU campaigns"
                )

        if campaign.status == "archived":
            errors.append("archived campaigns cannot publish new versions")
        if campaign.expires_at is not None and _coerce_utc(campaign.expires_at) <= datetime.now(UTC):
            errors.append("campaign expiry is in the past")
        if not errors and version.status == "published":
            warnings.append("version is already published")
        return ValidateInviteCampaignVersionResult(
            version_id=version.id,
            checksum=version.checksum,
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )


class PublishInviteCampaignVersionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, campaign_id: UUID, version_id: UUID, admin_user_id: UUID) -> InviteCampaignModel:
        campaign = await self._session.get(InviteCampaignModel, campaign_id)
        version = await self._session.get(InviteCampaignVersionModel, version_id)
        if campaign is None or version is None or version.campaign_id != campaign.id:
            raise ValueError("Invite campaign version was not found")
        validation = await ValidateInviteCampaignVersionUseCase(self._session).execute(
            campaign_id=campaign_id,
            version_id=version_id,
        )
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        version.status = "published"
        version.published_by_admin_id = admin_user_id
        version.published_at = datetime.now(UTC)
        campaign.current_version_id = version.id
        campaign.status = "active"
        campaign.published_at = campaign.published_at or version.published_at
        campaign.updated_by_admin_id = admin_user_id
        await self._session.flush()
        return campaign


class CreateInviteCampaignBatchUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        command: CreateInviteCampaignBatchCommand,
        admin_user_id: UUID,
    ) -> InviteCampaignBatchResult:
        campaign = await self._session.get(InviteCampaignModel, command.campaign_id)
        if campaign is None:
            raise ValueError("Invite campaign was not found")
        version_id = command.version_id or campaign.current_version_id
        version = await self._session.get(InviteCampaignVersionModel, version_id) if version_id else None
        if version is None or version.campaign_id != campaign.id:
            raise ValueError("Invite campaign version was not found")
        if version.status != "published":
            raise ValueError("Invite campaign version must be published before issuing root codes")
        if campaign.status not in {"active", "scheduled"}:
            raise ValueError("Invite campaign is not active")
        self._validate_campaign_window(campaign)
        owner_mode = _normalize_owner_mode(campaign.owner_mode)
        owner_user_ids = tuple(command.owner_user_ids)
        if owner_mode == "selected_user" and command.owner_user_id is None:
            raise ValueError("owner_user_id is required for selected-user invite campaigns")
        if owner_mode == "uploaded_user_list":
            if not owner_user_ids:
                raise ValueError("owner_user_ids is required for uploaded-user-list invite campaigns")
            if len(owner_user_ids) != int(command.count):
                raise ValueError("owner_user_ids count must match requested invite count")
            if len(set(owner_user_ids)) != len(owner_user_ids):
                raise ValueError("owner_user_ids must not contain duplicate users")
        if owner_mode == "system" and owner_user_ids:
            raise ValueError("system invite campaigns do not accept uploaded owner_user_ids")

        await _pg_advisory_xact_lock(self._session, f"invite-campaign-issue:{campaign.id}:global")
        if owner_user_ids:
            for owner_user_id in sorted(owner_user_ids, key=str):
                await _pg_advisory_xact_lock(
                    self._session,
                    f"invite-campaign-issue:{campaign.id}:{owner_user_id}",
                )
        else:
            await _pg_advisory_xact_lock(
                self._session,
                f"invite-campaign-issue:{campaign.id}:{command.owner_user_id or 'system'}",
            )
        await validate_invite_campaign_issue_caps(
            self._session,
            campaign=campaign,
            owner_user_id=command.owner_user_id,
            requested_count=int(command.count),
            enforce_owner_cap=not owner_user_ids,
        )
        for owner_user_id in owner_user_ids:
            await validate_invite_campaign_issue_caps(
                self._session,
                campaign=campaign,
                owner_user_id=owner_user_id,
                requested_count=1,
            )

        owner_scope = (
            hashlib.sha256(",".join(str(item) for item in owner_user_ids).encode("utf-8")).hexdigest()[:24]
            if owner_user_ids
            else str(command.owner_user_id or "system")
        )
        idempotency_key = command.idempotency_key or (
            f"invite-root-batch:{campaign.id}:{version.id}:{owner_scope}:{command.count}"
        )
        existing = await self._session.execute(
            select(InviteBatchModel).where(InviteBatchModel.idempotency_key == idempotency_key)
        )
        existing_batch = existing.scalars().first()
        if existing_batch is not None:
            # Raw codes are intentionally not returned on idempotency replay.
            return InviteCampaignBatchResult(
                campaign=campaign,
                version=version,
                batch=existing_batch,
                raw_codes=(),
            )

        expiry_mode = str(command.expiry_mode or INVITE_EXPIRY_CAMPAIGN_DEFAULT)
        if expiry_mode == INVITE_EXPIRY_CAMPAIGN_DEFAULT:
            resolved_expiry_mode = version.root_invite_expiry_mode or INVITE_EXPIRY_RELATIVE
            resolved_expiry_days = version.root_invite_expiry_days or 30
            resolved_expires_at = version.root_invite_expires_at
        else:
            resolved_expiry_mode = expiry_mode
            resolved_expiry_days = command.expiry_days
            resolved_expires_at = command.expires_at
        expiry = resolve_invite_expiry(
            expiry_mode=resolved_expiry_mode,
            expiry_days=resolved_expiry_days,
            expires_at=resolved_expires_at,
            now=datetime.now(UTC),
        )
        usage_mode = (
            version.root_usage_mode
            if command.usage_mode == INVITE_USAGE_CAMPAIGN_DEFAULT
            else _normalize_invite_usage_mode(command.usage_mode)
        )
        max_redemptions_per_code = (
            command.max_redemptions_per_code
            if command.max_redemptions_per_code is not None
            else version.root_max_redemptions
        )
        max_redemptions_per_code = _normalize_invite_max_redemptions(
            usage_mode=usage_mode,
            max_redemptions=max_redemptions_per_code,
            acknowledgement=bool((version.issue_policy or {}).get("multi_use_acknowledgement")),
        )
        per_user_redemption_cap = _normalize_per_user_cap(
            command.per_user_redemption_cap
            if command.per_user_redemption_cap is not None
            else version.root_per_user_redemption_cap
        )
        multi_use_policy = dict(version.multi_use_policy or {})
        if usage_mode == INVITE_USAGE_MULTI:
            multi_use_policy = _validate_multi_use_campaign_policy(
                risk_policy=dict(version.risk_policy or {}),
                caps=dict(campaign.caps or {}),
                max_generation_depth=int(version.max_generation_depth or 0),
                acknowledgement=bool((version.issue_policy or {}).get("multi_use_acknowledgement")),
                policy=multi_use_policy,
            )
        grant_snapshot = dict(version.grant_snapshot or {})
        display_days = display_days_for_duration(version.grant_duration_mode, version.grant_duration_days)
        batch = InviteBatchModel(
            owner_user_id=command.owner_user_id,
            invite_campaign_id=campaign.id,
            invite_campaign_version_id=version.id,
            root_owner_user_id=command.owner_user_id,
            generation_depth=0,
            batch_kind="root_campaign",
            source_type="root_campaign",
            requested_count=int(command.count),
            issued_count=int(command.count),
            friend_days=display_days,
            expiry_mode=expiry.expiry_mode,
            expiry_days=expiry.expiry_days,
            expires_at=expiry.expires_at,
            usage_mode=usage_mode,
            max_redemptions_per_code=max_redemptions_per_code,
            per_user_redemption_cap=per_user_redemption_cap,
            multi_use_policy=multi_use_policy,
            entitlement_mode=version.grant_mode,
            entitlement_profile_key=f"{campaign.campaign_key}_v{version.version}",
            plan_id=version.grant_plan_id,
            entitlement_snapshot=grant_snapshot,
            grant_mode=version.grant_mode,
            grant_plan_id=version.grant_plan_id,
            grant_duration_mode=version.grant_duration_mode,
            grant_duration_days=version.grant_duration_days,
            grant_device_limit_override=version.grant_device_limit_override,
            grant_snapshot=grant_snapshot,
            child_grant_plan_id=version.child_grant_plan_id,
            child_grant_duration_mode=version.child_grant_duration_mode,
            child_grant_duration_days=version.child_grant_duration_days,
            child_grant_device_limit_override=version.child_grant_device_limit_override,
            child_invite_expiry_mode=version.child_invite_expiry_mode,
            child_policy=dict(version.child_policy or {}),
            risk_policy=dict(version.risk_policy or {}),
            redemption_policy=dict(version.redemption_policy or {}),
            issue_policy={
                **dict(version.issue_policy or {}),
                "created_by_admin_id": str(admin_user_id),
                "reason": command.reason,
            },
            status="issued",
            idempotency_key=idempotency_key,
        )
        self._session.add(batch)
        await self._session.flush()

        invites: list[InviteCodeModel] = []
        for index in range(int(command.count)):
            raw_code = await _generate_unique_code(self._session)
            owner_user_id = owner_user_ids[index] if owner_user_ids else command.owner_user_id
            invites.append(
                InviteCodeModel(
                    code=raw_code,
                    owner_user_id=owner_user_id,
                    free_days=display_days,
                    plan_id=version.grant_plan_id,
                    batch_id=batch.id,
                    campaign_id=campaign.id,
                    campaign_version_id=version.id,
                    generation_depth=0,
                    status="issued",
                    usage_mode=usage_mode,
                    max_redemptions=max_redemptions_per_code,
                    per_user_redemption_cap=per_user_redemption_cap,
                    multi_use_policy=multi_use_policy,
                    code_hash=hash_growth_code(raw_code),
                    code_prefix=build_growth_code_prefix(raw_code),
                    entitlement_mode=version.grant_mode,
                    entitlement_profile_key=f"{campaign.campaign_key}_v{version.version}",
                    entitlement_snapshot=grant_snapshot,
                    grant_mode=version.grant_mode,
                    grant_plan_id=version.grant_plan_id,
                    grant_duration_mode=version.grant_duration_mode,
                    grant_duration_days=version.grant_duration_days,
                    grant_device_limit_override=version.grant_device_limit_override,
                    grant_snapshot=grant_snapshot,
                    child_grant_plan_id=version.child_grant_plan_id,
                    child_grant_duration_mode=version.child_grant_duration_mode,
                    child_grant_duration_days=version.child_grant_duration_days,
                    child_grant_device_limit_override=version.child_grant_device_limit_override,
                    child_invite_expiry_mode=version.child_invite_expiry_mode,
                    child_policy=dict(version.child_policy or {}),
                    risk_policy=dict(version.risk_policy or {}),
                    redemption_policy=dict(version.redemption_policy or {}),
                    issue_policy={"source": "root_campaign", "created_by_admin_id": str(admin_user_id)},
                    source="root_campaign",
                    expires_at=expiry.expires_at,
                )
            )
        self._session.add_all(invites)
        await self._session.flush()
        for invite in invites:
            invite.root_invite_code_id = invite.id
        await self._session.flush()
        return InviteCampaignBatchResult(
            campaign=campaign,
            version=version,
            batch=batch,
            raw_codes=tuple(invite.code for invite in invites),
        )

    def _validate_campaign_window(self, campaign: InviteCampaignModel) -> None:
        now = datetime.now(UTC)
        starts_at = _coerce_utc(campaign.starts_at)
        expires_at = _coerce_utc(campaign.expires_at)
        if campaign.status == "scheduled" and starts_at is not None and starts_at > now:
            return
        if starts_at is not None and starts_at > now:
            raise ValueError("Invite campaign has not started")
        if expires_at is not None and expires_at <= now:
            raise ValueError("Invite campaign has expired")

    async def _validate_issue_caps(
        self,
        *,
        campaign: InviteCampaignModel,
        owner_user_id: UUID | None,
        requested_count: int,
    ) -> None:
        await validate_invite_campaign_issue_caps(
            self._session,
            campaign=campaign,
            owner_user_id=owner_user_id,
            requested_count=requested_count,
        )


async def validate_invite_campaign_issue_caps(
    session: AsyncSession,
    *,
    campaign: InviteCampaignModel,
    owner_user_id: UUID | None,
    requested_count: int,
    enforce_owner_cap: bool = True,
) -> None:
    caps = dict(campaign.caps or {})
    max_per_batch = _positive_int(caps.get("max_per_batch"), default=1_000)
    if requested_count > max_per_batch:
        raise ValueError("Invite campaign batch exceeds per-batch cap")

    max_total_issued = _optional_positive_int(caps.get("max_total_issued") or caps.get("global_issue_cap"))
    if max_total_issued is not None:
        issued = await session.execute(
            select(func.count()).select_from(InviteCodeModel).where(InviteCodeModel.campaign_id == campaign.id)
        )
        if int(issued.scalar_one()) + requested_count > max_total_issued:
            raise ValueError("Invite campaign total issue cap exceeded")

    max_per_owner = _optional_positive_int(caps.get("max_per_owner"))
    if enforce_owner_cap and max_per_owner is not None:
        owner_filter = (
            InviteCodeModel.owner_user_id.is_(None)
            if owner_user_id is None
            else InviteCodeModel.owner_user_id == owner_user_id
        )
        owner_issued = await session.execute(
            select(func.count())
            .select_from(InviteCodeModel)
            .where(
                InviteCodeModel.campaign_id == campaign.id,
                owner_filter,
            )
        )
        if int(owner_issued.scalar_one()) + requested_count > max_per_owner:
            raise ValueError("Invite campaign owner issue cap exceeded")

    max_daily_issued = _optional_positive_int(caps.get("max_daily_issued"))
    if max_daily_issued is not None:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_issued = await session.execute(
            select(func.count())
            .select_from(InviteCodeModel)
            .where(
                InviteCodeModel.campaign_id == campaign.id,
                InviteCodeModel.created_at >= today,
            )
        )
        if int(daily_issued.scalar_one()) + requested_count > max_daily_issued:
            raise ValueError("Invite campaign daily issue cap exceeded")


async def list_invite_campaigns(
    session: AsyncSession,
    *,
    status: str | None,
    campaign_key: str | None,
    offset: int,
    limit: int,
) -> tuple[list[InviteCampaignModel], int]:
    filters = []
    if status:
        filters.append(InviteCampaignModel.status == status)
    if campaign_key:
        filters.append(InviteCampaignModel.campaign_key == campaign_key)
    total_result = await session.execute(select(func.count()).select_from(InviteCampaignModel).where(*filters))
    result = await session.execute(
        select(InviteCampaignModel)
        .where(*filters)
        .order_by(InviteCampaignModel.created_at.desc(), InviteCampaignModel.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), int(total_result.scalar_one())


async def _generate_unique_code(session: AsyncSession) -> str:
    for _ in range(20):
        raw_code = secrets.token_urlsafe(7)[:10].upper()
        existing = await session.execute(select(InviteCodeModel.id).where(InviteCodeModel.code == raw_code))
        if existing.scalar_one_or_none() is None:
            return raw_code
    raise ValueError("Unable to generate a unique invite code")


def _safe_surfaces(values: list[str]) -> list[str]:
    allowed = {"web", "miniapp", "telegram_bot"}
    surfaces = [value for value in values if value in allowed]
    return surfaces or ["web", "miniapp", "telegram_bot"]


def _safe_geo_policy(*, countries: list[str], markets: list[str], segments: list[str]) -> dict[str, list[str]]:
    return {
        "countries": _safe_policy_values(countries),
        "markets": _safe_policy_values(markets),
        "segments": _safe_policy_values(segments),
    }


def _safe_policy_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result[:200]


def _normalize_owner_mode(value: str | None) -> str:
    normalized = (value or "selected_user").strip()
    aliases = {
        "admin_pool": "system",
        "customer_owned": "selected_user",
        "partner_owned": "selected_user",
    }
    return aliases.get(normalized, normalized)


def _version_checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _pg_advisory_xact_lock(session: AsyncSession, scope: str) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    lock_id = int.from_bytes(hashlib.blake2b(scope.encode("utf-8"), digest_size=8).digest(), "big", signed=True)
    await session.execute(select(func.pg_advisory_xact_lock(lock_id)))


async def _resolve_plan(plans: SubscriptionPlanRepository, plan_id: UUID | None, plan_code: str | None):
    if plan_id is not None:
        plan = await plans.get_by_id(plan_id)
    else:
        plan = await plans.get_by_plan_code(plan_code or "premium_smart_ru", duration_days=365)
        if plan is None:
            plan = await plans.get_by_plan_code(plan_code or "premium_smart_ru")
    if plan is None:
        raise ValueError("Invite campaign grant plan was not found")
    if not plan.is_active:
        raise ValueError("Invite campaign grant plan is inactive")
    return plan


def _policy_contains_raw_code(value: object) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {"code", "raw_code", "raw_codes"}:
                return True
            if _policy_contains_raw_code(nested):
                return True
    if isinstance(value, list):
        return any(_policy_contains_raw_code(item) for item in value)
    return False


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _optional_positive_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_invite_usage_mode(value: object) -> str:
    normalized = str(value or INVITE_USAGE_SINGLE).strip().lower()
    if normalized == INVITE_USAGE_CAMPAIGN_DEFAULT:
        return INVITE_USAGE_CAMPAIGN_DEFAULT
    return INVITE_USAGE_MULTI if normalized == INVITE_USAGE_MULTI else INVITE_USAGE_SINGLE


def _normalize_invite_max_redemptions(
    *,
    usage_mode: str,
    max_redemptions: int | None,
    acknowledgement: bool,
) -> int | None:
    if usage_mode == INVITE_USAGE_SINGLE:
        return 1
    parsed = _optional_positive_int(max_redemptions)
    if parsed is None:
        if not acknowledgement:
            raise ValueError("multi_use_acknowledgement is required when max_redemptions is omitted")
        return MULTI_USE_PRACTICAL_HARD_CAP
    if parsed <= 1:
        raise ValueError("multi_use invite codes require max_redemptions greater than 1")
    return parsed


def _normalize_per_user_cap(value: object) -> int:
    parsed = _positive_int(value, default=1)
    if parsed != 1:
        raise ValueError("per_user_redemption_cap greater than 1 is not enabled for invite codes")
    return 1


def _validate_multi_use_campaign_policy(
    *,
    risk_policy: dict[str, Any],
    caps: dict[str, Any],
    max_generation_depth: int,
    acknowledgement: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    if not acknowledgement:
        raise ValueError("multi_use_acknowledgement is required for multi_use invite campaigns")
    if max_generation_depth > 5:
        raise ValueError("multi_use invite campaigns require max_generation_depth <= 5")
    if _optional_positive_int(caps.get("global_issue_cap") or caps.get("max_total_issued")) is None:
        raise ValueError("multi_use invite campaigns require global_issue_cap or max_total_issued")

    max_per_device = _optional_positive_int(risk_policy.get("max_redemptions_per_device"))
    max_per_ip_window = _optional_positive_int(risk_policy.get("max_redemptions_per_ip_window"))
    velocity_window_hours = _optional_positive_int(risk_policy.get("velocity_window_hours"))
    if max_per_device is None or max_per_device > 1:
        raise ValueError("multi_use invite campaigns require max_redemptions_per_device <= 1")
    if max_per_ip_window is None or max_per_ip_window > 3:
        raise ValueError("multi_use invite campaigns require max_redemptions_per_ip_window <= 3")
    if velocity_window_hours is None or velocity_window_hours > 24:
        raise ValueError("multi_use invite campaigns require velocity_window_hours <= 24")
    if risk_policy.get("deny_disposable_email") is not True:
        raise ValueError("multi_use invite campaigns require deny_disposable_email=true")
    if risk_policy.get("deny_known_abuse_subject") is not True:
        raise ValueError("multi_use invite campaigns require deny_known_abuse_subject=true")

    result = dict(policy or {})
    result.setdefault("high_risk_context", True)
    result.setdefault("per_user_redemption_cap", 1)
    result.setdefault("device_cap", max_per_device)
    result.setdefault("ip_window_cap", max_per_ip_window)
    result.setdefault("velocity_window_hours", velocity_window_hours)
    return result


def _validate_lifetime_campaign_policy(
    *,
    grant_duration_mode: str,
    child_grant_duration_mode: str,
    child_invite_count: int,
    max_generation_depth: int,
    require_no_active_access: bool,
    block_self_redemption: bool,
    root_invite_expiry_mode: str,
    child_invite_expiry_mode: str,
    campaign_expires_at: datetime | None,
    caps: dict[str, Any],
    risk_policy: dict[str, Any],
    lifetime_campaign_acknowledgement: bool,
) -> None:
    root_lifetime = normalize_invite_duration_mode(grant_duration_mode) == INVITE_DURATION_LIFETIME
    child_lifetime = normalize_invite_duration_mode(child_grant_duration_mode) == INVITE_DURATION_LIFETIME
    if not root_lifetime and not child_lifetime:
        return
    if not require_no_active_access:
        raise ValueError("lifetime campaigns require require_no_active_access")
    if not block_self_redemption:
        raise ValueError("lifetime campaigns require block_self_redemption")
    if _positive_int(risk_policy.get("per_user_redeem_cap"), default=0) != 1:
        raise ValueError("lifetime campaigns require risk_policy.per_user_redeem_cap=1")
    max_redemptions_per_device = _optional_positive_int(risk_policy.get("max_redemptions_per_device"))
    if max_redemptions_per_device is None or max_redemptions_per_device > 1:
        raise ValueError("lifetime campaigns require risk_policy.max_redemptions_per_device<=1")
    max_redemptions_per_ip_window = _optional_positive_int(risk_policy.get("max_redemptions_per_ip_window"))
    if max_redemptions_per_ip_window is None or max_redemptions_per_ip_window > 3:
        raise ValueError("lifetime campaigns require risk_policy.max_redemptions_per_ip_window<=3")
    velocity_window_hours = _optional_positive_int(risk_policy.get("velocity_window_hours"))
    if velocity_window_hours is None or velocity_window_hours > 24:
        raise ValueError("lifetime campaigns require risk_policy.velocity_window_hours<=24")
    if risk_policy.get("deny_disposable_email") is not True:
        raise ValueError("lifetime campaigns require risk_policy.deny_disposable_email=true")
    if risk_policy.get("deny_known_abuse_subject") is not True:
        raise ValueError("lifetime campaigns require risk_policy.deny_known_abuse_subject=true")
    if child_invite_count > 0 and max_generation_depth > 5:
        raise ValueError("lifetime campaigns with child invites require max_generation_depth <= 5")
    if child_invite_count >= 10 and _optional_positive_int(caps.get("global_issue_cap")) is None:
        raise ValueError("lifetime campaigns with 10 or more child invites require global_issue_cap")
    if root_invite_expiry_mode == "none" and campaign_expires_at is None and not lifetime_campaign_acknowledgement:
        raise ValueError("root no-expiry lifetime campaigns require lifetime_campaign_acknowledgement")
    if (
        root_invite_expiry_mode == "none"
        and child_invite_expiry_mode == "none"
        and max_generation_depth > 3
        and not bool(risk_policy.get("high_risk_context"))
    ):
        raise ValueError("lifetime no-expiry campaigns deeper than 3 require risk_policy.high_risk_context")


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
