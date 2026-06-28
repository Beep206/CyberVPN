"""Use cases for flexible invite campaign administration."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.config.settings import settings
from src.infrastructure.database.models.growth_benefit_model import InviteBatchModel
from src.infrastructure.database.models.invite_campaign_model import (
    InviteCampaignModel,
    InviteCampaignVersionModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository


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
    grant_duration_days: int
    child_grant_plan_id: UUID | None
    child_grant_plan_code: str | None
    child_grant_duration_days: int | None
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_days: int
    max_generation_depth: int
    require_no_active_access: bool
    block_self_redemption: bool
    risk_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
    caps: dict[str, Any]
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
    expires_at: datetime | None
    expiry_days: int | None
    reason: str


@dataclass(frozen=True)
class CreateInviteCampaignVersionCommand:
    grant_plan_id: UUID | None
    grant_plan_code: str | None
    grant_duration_days: int
    child_invite_count: int
    child_invite_free_days: int
    child_invite_expiry_days: int
    child_grant_plan_id: UUID | None
    child_grant_plan_code: str | None
    child_grant_duration_days: int | None
    max_generation_depth: int
    require_no_active_access: bool
    block_self_redemption: bool
    allowed_surfaces: list[str]
    risk_policy: dict[str, Any]
    export_policy: dict[str, Any]
    notification_policy: dict[str, Any]
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

        plan = await self._resolve_plan(command.grant_plan_id, command.grant_plan_code)
        grant_expires_at = datetime.now(UTC) + timedelta(days=int(command.grant_duration_days))
        grant_snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=grant_expires_at, status="active")
        grant_snapshot["period_days"] = int(command.grant_duration_days)
        grant_snapshot["source_type"] = "invite_campaign"
        child_plan = plan
        child_duration_days = int(command.child_grant_duration_days or command.child_invite_free_days)
        child_snapshot = dict(grant_snapshot)
        if command.child_invite_count > 0:
            child_plan = await self._resolve_plan(
                command.child_grant_plan_id,
                command.child_grant_plan_code or command.grant_plan_code,
            )
            child_expires_at = datetime.now(UTC) + timedelta(days=child_duration_days)
            child_snapshot = EntitlementsService.build_snapshot(
                plan=child_plan,
                expires_at=child_expires_at,
                status="active",
            )
            child_snapshot["period_days"] = child_duration_days
            child_snapshot["source_type"] = "invite_campaign_child"
        allowed_surfaces = _safe_surfaces(command.allowed_surfaces)
        allowed_geos = _safe_geo_policy(
            countries=command.allowed_geos,
            markets=command.allowed_markets,
            segments=command.allowed_segments,
        )
        risk_policy = dict(command.risk_policy)
        if command.risk_policy_key:
            risk_policy["risk_policy_key"] = command.risk_policy_key
        now = datetime.now(UTC)
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

        version = InviteCampaignVersionModel(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            version=1,
            status="published" if command.publish else "draft",
            grant_mode="plan_snapshot",
            grant_plan_id=plan.id,
            grant_duration_days=int(command.grant_duration_days),
            grant_snapshot=grant_snapshot,
            child_invite_count=int(command.child_invite_count),
            child_invite_free_days=int(command.child_invite_free_days),
            child_invite_expiry_days=int(command.child_invite_expiry_days),
            child_grant_plan_id=child_plan.id if command.child_invite_count > 0 else None,
            child_grant_duration_days=child_duration_days if command.child_invite_count > 0 else None,
            child_grant_snapshot=child_snapshot if command.child_invite_count > 0 else {},
            max_generation_depth=int(command.max_generation_depth),
            block_self_redemption=command.block_self_redemption,
            require_no_active_access=command.require_no_active_access,
            allowed_surfaces=allowed_surfaces,
            risk_policy=risk_policy,
            redemption_policy={
                "allowed_surfaces": allowed_surfaces,
                "require_no_active_access": command.require_no_active_access,
                "block_self_redemption": command.block_self_redemption,
                "per_user_redeem_cap": _positive_int(command.risk_policy.get("per_user_redeem_cap"), default=1),
            },
            child_policy={
                "count": int(command.child_invite_count),
                "friend_days": int(command.child_invite_free_days),
                "grant_plan_id": str(child_plan.id) if command.child_invite_count > 0 else None,
                "grant_plan_code": child_plan.plan_code if command.child_invite_count > 0 else None,
                "grant_duration_days": child_duration_days if command.child_invite_count > 0 else None,
                "grant_snapshot": child_snapshot if command.child_invite_count > 0 else {},
                "expiry_days": int(command.child_invite_expiry_days),
                "max_generation_depth": int(command.max_generation_depth),
                "issue_timing": "immediately",
            },
            issue_policy={"root_batch_kind": "root_campaign", "raw_codes_one_time": True},
            export_policy=dict(command.export_policy),
            notification_policy=dict(command.notification_policy),
            checksum=_version_checksum(
                {
                    "campaign_key": command.campaign_key,
                    "grant_plan_id": str(plan.id),
                    "grant_duration_days": command.grant_duration_days,
                    "child_invite_count": command.child_invite_count,
                    "child_invite_free_days": command.child_invite_free_days,
                    "child_grant_plan_id": str(child_plan.id) if command.child_invite_count > 0 else None,
                    "child_grant_duration_days": child_duration_days if command.child_invite_count > 0 else None,
                    "child_invite_expiry_days": command.child_invite_expiry_days,
                    "max_generation_depth": command.max_generation_depth,
                    "allowed_surfaces": allowed_surfaces,
                    "allowed_geos": allowed_geos,
                    "risk_policy": risk_policy,
                    "export_policy": command.export_policy,
                }
            ),
            created_by_admin_id=admin_user_id,
            published_by_admin_id=admin_user_id if command.publish else None,
            published_at=now if command.publish else None,
        )
        self._session.add(version)
        await self._session.flush()
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
        campaign.updated_by_admin_id = admin_user_id
        campaign.metadata_json = {**dict(campaign.metadata_json or {}), "last_version_reason": command.reason}
        await self._session.flush()
        return version

    async def _build_version(
        self,
        *,
        campaign: InviteCampaignModel,
        version_number: int,
        command: CreateInviteCampaignVersionCommand,
        admin_user_id: UUID,
    ) -> InviteCampaignVersionModel:
        plan = await _resolve_plan(self._plans, command.grant_plan_id, command.grant_plan_code)
        grant_expires_at = datetime.now(UTC) + timedelta(days=int(command.grant_duration_days))
        grant_snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=grant_expires_at, status="active")
        grant_snapshot["period_days"] = int(command.grant_duration_days)
        grant_snapshot["source_type"] = "invite_campaign"

        child_plan = None
        child_snapshot: dict[str, Any] = {}
        child_duration_days = command.child_grant_duration_days or command.child_invite_free_days
        if command.child_invite_count > 0:
            child_plan = await _resolve_plan(
                self._plans,
                command.child_grant_plan_id,
                command.child_grant_plan_code or command.grant_plan_code,
            )
            child_expires_at = datetime.now(UTC) + timedelta(days=int(child_duration_days))
            child_snapshot = EntitlementsService.build_snapshot(
                plan=child_plan,
                expires_at=child_expires_at,
                status="active",
            )
            child_snapshot["period_days"] = int(child_duration_days)
            child_snapshot["source_type"] = "invite_campaign_child"

        allowed_surfaces = _safe_surfaces(command.allowed_surfaces)
        redemption_policy = {
            "allowed_surfaces": allowed_surfaces,
            "require_no_active_access": command.require_no_active_access,
            "block_self_redemption": command.block_self_redemption,
            "per_user_redeem_cap": _positive_int(command.risk_policy.get("per_user_redeem_cap"), default=1),
        }
        child_policy = {
            "enabled": command.child_invite_count > 0,
            "count": int(command.child_invite_count),
            "friend_days": int(command.child_invite_free_days),
            "grant_plan_id": str(child_plan.id) if child_plan is not None else None,
            "grant_plan_code": child_plan.plan_code if child_plan is not None else None,
            "grant_duration_days": int(child_duration_days) if child_plan is not None else None,
            "grant_snapshot": child_snapshot,
            "expiry_days": int(command.child_invite_expiry_days),
            "max_generation_depth": int(command.max_generation_depth),
            "issue_timing": "immediately",
        }
        checksum_payload = {
            "campaign_key": campaign.campaign_key,
            "version": version_number,
            "grant_plan_id": str(plan.id),
            "grant_duration_days": command.grant_duration_days,
            "child_invite_count": command.child_invite_count,
            "child_grant_plan_id": str(child_plan.id) if child_plan is not None else None,
            "child_grant_duration_days": int(child_duration_days) if child_plan is not None else None,
            "max_generation_depth": command.max_generation_depth,
            "allowed_surfaces": allowed_surfaces,
            "risk_policy": command.risk_policy,
            "export_policy": command.export_policy,
        }
        return InviteCampaignVersionModel(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            version=version_number,
            status="draft",
            grant_mode="plan_snapshot",
            grant_plan_id=plan.id,
            grant_duration_days=int(command.grant_duration_days),
            grant_snapshot=grant_snapshot,
            child_invite_count=int(command.child_invite_count),
            child_invite_free_days=int(command.child_invite_free_days),
            child_invite_expiry_days=int(command.child_invite_expiry_days),
            child_grant_plan_id=child_plan.id if child_plan is not None else None,
            child_grant_duration_days=int(child_duration_days) if child_plan is not None else None,
            child_grant_snapshot=child_snapshot,
            max_generation_depth=int(command.max_generation_depth),
            block_self_redemption=command.block_self_redemption,
            require_no_active_access=command.require_no_active_access,
            allowed_surfaces=allowed_surfaces,
            risk_policy=dict(command.risk_policy),
            redemption_policy=redemption_policy,
            child_policy=child_policy,
            issue_policy={"root_batch_kind": "root_campaign", "raw_codes_one_time": True},
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
        if _policy_contains_raw_code(version.redemption_policy) or _policy_contains_raw_code(version.child_policy):
            errors.append("policy snapshot must not contain raw invite codes")

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
        if owner_mode == "system" and owner_user_ids:
            raise ValueError("system invite campaigns do not accept uploaded owner_user_ids")

        await _pg_advisory_xact_lock(
            self._session,
            f"invite-campaign-issue:{campaign.id}:{command.owner_user_id or 'system'}",
        )
        await self._validate_issue_caps(
            campaign=campaign,
            owner_user_id=command.owner_user_id,
            requested_count=int(command.count),
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

        expires_at = command.expires_at
        expiry_days = int(command.expiry_days or 30)
        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(days=expiry_days)
        grant_snapshot = dict(version.grant_snapshot or {})
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
            friend_days=int(version.grant_duration_days or 365),
            expiry_mode="absolute" if command.expires_at is not None else "relative",
            expiry_days=None if command.expires_at is not None else expiry_days,
            expires_at=expires_at,
            entitlement_mode=version.grant_mode,
            entitlement_profile_key=f"{campaign.campaign_key}_v{version.version}",
            plan_id=version.grant_plan_id,
            entitlement_snapshot=grant_snapshot,
            grant_mode=version.grant_mode,
            grant_plan_id=version.grant_plan_id,
            grant_duration_days=version.grant_duration_days,
            grant_snapshot=grant_snapshot,
            child_grant_plan_id=version.child_grant_plan_id,
            child_grant_duration_days=version.child_grant_duration_days,
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
                    free_days=int(version.grant_duration_days or 365),
                    plan_id=version.grant_plan_id,
                    batch_id=batch.id,
                    campaign_id=campaign.id,
                    campaign_version_id=version.id,
                    generation_depth=0,
                    status="issued",
                    code_hash=hash_growth_code(raw_code),
                    code_prefix=build_growth_code_prefix(raw_code),
                    entitlement_mode=version.grant_mode,
                    entitlement_profile_key=f"{campaign.campaign_key}_v{version.version}",
                    entitlement_snapshot=grant_snapshot,
                    grant_mode=version.grant_mode,
                    grant_plan_id=version.grant_plan_id,
                    grant_duration_days=version.grant_duration_days,
                    grant_snapshot=grant_snapshot,
                    child_grant_plan_id=version.child_grant_plan_id,
                    child_grant_duration_days=version.child_grant_duration_days,
                    child_policy=dict(version.child_policy or {}),
                    risk_policy=dict(version.risk_policy or {}),
                    redemption_policy=dict(version.redemption_policy or {}),
                    issue_policy={"source": "root_campaign", "created_by_admin_id": str(admin_user_id)},
                    source="root_campaign",
                    expires_at=expires_at,
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
        caps = dict(campaign.caps or {})
        max_per_batch = _positive_int(caps.get("max_per_batch"), default=1_000)
        if requested_count > max_per_batch:
            raise ValueError("Invite campaign batch exceeds per-batch cap")

        max_total_issued = _optional_positive_int(caps.get("max_total_issued") or caps.get("global_issue_cap"))
        if max_total_issued is not None:
            issued = await self._session.execute(
                select(func.count()).select_from(InviteCodeModel).where(InviteCodeModel.campaign_id == campaign.id)
            )
            if int(issued.scalar_one()) + requested_count > max_total_issued:
                raise ValueError("Invite campaign total issue cap exceeded")

        max_per_owner = _optional_positive_int(caps.get("max_per_owner"))
        if max_per_owner is not None:
            owner_filter = (
                InviteCodeModel.owner_user_id.is_(None)
                if owner_user_id is None
                else InviteCodeModel.owner_user_id == owner_user_id
            )
            owner_issued = await self._session.execute(
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
            daily_issued = await self._session.execute(
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


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
