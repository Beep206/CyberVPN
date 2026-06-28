"""Use case for redeeming an invite code."""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.application.use_cases.growth_risk.runtime_guard import evaluate_growth_runtime_risk
from src.application.use_cases.service_access.entitlements import (
    ActivateEntitlementGrantUseCase,
    CreateEntitlementGrantUseCase,
    GetCurrentEntitlementStateUseCase,
)
from src.application.use_cases.service_access.service_identities import CreateServiceIdentityUseCase
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.infrastructure.database.models.growth_benefit_model import InviteBatchModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeRedemptionModel
from src.infrastructure.database.models.invite_campaign_model import (
    InviteCampaignModel,
    InviteCampaignVersionModel,
    InviteRedemptionModel,
    InviteTreeClosureModel,
    InviteTreeEdgeModel,
)
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_REDEEM_SURFACE,
    log_growth_code_event,
    observe_growth_code_redemption,
    observe_growth_code_redemption_duration,
    observe_invite_redeemed,
)
from src.presentation.dependencies.auth_realms import RealmResolution

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RedeemedInviteResult:
    invite: InviteCodeModel
    entitlement_grant_id: UUID
    entitlement_snapshot: dict
    redemption: GrowthCodeRedemptionModel
    invite_redemption: InviteRedemptionModel | None = None
    child_batch: InviteBatchModel | None = None
    child_invites: tuple[InviteCodeModel, ...] = ()


class RedeemInviteUseCase:
    """Validate and redeem an invite code for a given user.

    Returns the redeemed invite plus canonical entitlement context so the
    caller can expose the granted access immediately.
    """

    def __init__(self, session) -> None:
        self._session = session
        self._invite_repo = InviteCodeRepository(session)
        self._growth_codes = GrowthCodeRepository(session)
        self._registry = GrowthCodeRegistryService(session)
        self._plans = SubscriptionPlanRepository(session)
        self._service_identities = CreateServiceIdentityUseCase(session)
        self._entitlements = CreateEntitlementGrantUseCase(session)
        self._activate_entitlement = ActivateEntitlementGrantUseCase(session)
        self._current_entitlements = GetCurrentEntitlementStateUseCase(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        code: str,
        user_id: UUID,
        current_realm: RealmResolution,
        source_surface: str = "web",
    ) -> RedeemedInviteResult:
        """Redeem *code* on behalf of *user_id*.

        Raises:
            InviteCodeNotFoundError: code does not exist or is unavailable.
            InviteCodeAlreadyUsedError: code has already been redeemed.
            InviteCodeExpiredError: code has passed its expiry date.
        """
        started_at = perf_counter()
        code_ref = _safe_invite_code_ref(code)
        invite = await self._invite_repo.get_by_code_for_update(code)

        if invite is None:
            logger.warning("invite_redeem_not_found", extra={**code_ref, "user_id": str(user_id)})
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeNotFoundError(code)

        if not invite.is_used:
            await _pg_advisory_xact_lock(
                self._session,
                f"invite-redeem:{invite.campaign_id or invite.id}:redeemer:{user_id}",
            )
            try:
                await self._validate_invite_status(invite)
                await self._validate_campaign_policy(invite=invite, user_id=user_id, source_surface=source_surface)
            except ValueError as exc:
                await self._record_blocked_redemption(
                    invite=invite,
                    redeemer_user_id=user_id,
                    source_surface=source_surface,
                    reason=str(exc),
                )
                observe_growth_code_redemption_duration(
                    code_type="invite",
                    surface=CUSTOMER_REDEEM_SURFACE,
                    result="failure",
                    duration_seconds=perf_counter() - started_at,
                )
                raise

        if invite.owner_user_id == user_id and _policy_bool(
            invite.redemption_policy,
            "block_self_redemption",
            default=True,
        ):
            await self._record_blocked_redemption(
                invite=invite,
                redeemer_user_id=user_id,
                source_surface=source_surface,
                reason="Invite code cannot be redeemed by the owner",
            )
            logger.warning(
                "invite_redeem_self_redemption_blocked",
                extra={**code_ref, "user_id": str(user_id)},
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Invite code cannot be redeemed by the owner")

        if invite.is_used:
            if invite.used_by_user_id == user_id:
                result = await self._build_idempotent_result(
                    invite=invite,
                    user_id=user_id,
                    current_realm=current_realm,
                    source_surface=source_surface,
                )
                observe_growth_code_redemption_duration(
                    code_type="invite",
                    surface=CUSTOMER_REDEEM_SURFACE,
                    result="success",
                    duration_seconds=perf_counter() - started_at,
                )
                return result
            logger.warning(
                "invite_redeem_already_used",
                extra={**code_ref, "user_id": str(user_id)},
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeAlreadyUsedError(code)

        expires_at = _coerce_utc(invite.expires_at)
        if expires_at is not None and expires_at < datetime.now(UTC):
            await self._record_blocked_redemption(
                invite=invite,
                redeemer_user_id=user_id,
                source_surface=source_surface,
                reason="Invite code expired",
            )
            logger.warning(
                "invite_redeem_expired",
                extra={**code_ref, "expires_at": str(expires_at)},
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeExpiredError(code)

        if _policy_bool(invite.redemption_policy, "require_no_active_access", default=True):
            current_snapshot = await self._current_entitlements.execute(
                customer_account_id=user_id,
                auth_realm_id=UUID(current_realm.realm_id),
            )
            if current_snapshot.get("status") not in {None, "none"}:
                await self._record_blocked_redemption(
                    invite=invite,
                    redeemer_user_id=user_id,
                    source_surface=source_surface,
                    reason="Invite code cannot be redeemed for accounts with active access",
                )
                observe_growth_code_redemption_duration(
                    code_type="invite",
                    surface=CUSTOMER_REDEEM_SURFACE,
                    result="failure",
                    duration_seconds=perf_counter() - started_at,
                )
                raise ValueError("Invite code cannot be redeemed for accounts with active access")

        await evaluate_growth_runtime_risk(
            session=self._session,
            action_context="invite_redeem",
            user_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            storefront_id=None,
            high_risk_context=True,
            features={
                "checkpoint": "invite_redeem",
                "code_prefix": build_growth_code_prefix(code),
                "code_hash": hash_growth_code(code),
                "free_days": invite.free_days,
                "owner_user_id": str(invite.owner_user_id) if invite.owner_user_id else None,
                "source": str(invite.source),
            },
            enforce=True,
        )

        grant_snapshot, access_days = await self._build_grant_snapshot(invite)
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(days=access_days)

        shadow_code = await self._registry.ensure_shadow_invite(invite)
        service_identity = await self._service_identities.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            provider_name="remnawave",
            origin_storefront_id=shadow_code.storefront_id,
        )
        grant = await self._entitlements.execute(
            service_identity_id=service_identity.service_identity.id,
            manual_source_key=f"invite:{invite.id}:redeemer:{user_id}",
            grant_snapshot=grant_snapshot,
            expires_at=access_expires_at,
        )
        activated = await self._activate_entitlement.execute(
            entitlement_grant_id=grant.entitlement_grant.id,
            activated_by_admin_user_id=None,
        )
        used_invite = await self._invite_repo.mark_used(invite.id, user_id)
        if used_invite is None:
            raise InviteCodeAlreadyUsedError(code)
        redemption = await self._ensure_redemption(
            shadow_code_id=shadow_code.id,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            policy_version_id=shadow_code.policy_version_id,
        )
        redeemed_invite = used_invite if used_invite is not None else invite
        invite_redemption = await self._ensure_invite_redemption(
            invite=redeemed_invite,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            source_surface=source_surface,
            grant_snapshot=dict(activated.grant_snapshot or grant_snapshot),
        )
        child_batch, child_invites = await self._ensure_child_invites_after_redemption(
            invite=redeemed_invite,
            redeemer_user_id=user_id,
            invite_redemption=invite_redemption,
            source_surface=source_surface,
        )
        if child_batch is not None:
            invite_redemption.child_batch_id = child_batch.id
            invite_redemption.child_issued_count = len(child_invites)
        await self._ensure_tree_state(invite=redeemed_invite, invite_redemption=invite_redemption)
        shadow_code.status = "redeemed"
        shadow_code.uses_count = 1
        await self._session.flush()
        await self._outbox.append_event(
            event_name="growth_code.redeemed",
            aggregate_type="growth_code",
            aggregate_id=str(shadow_code.id),
            partition_key=str(shadow_code.owner_user_id or shadow_code.id),
            event_payload={
                "growth_code_id": str(shadow_code.id),
                "code_type": shadow_code.code_type,
                "redeemer_user_id": str(user_id),
                "redemption_id": str(redemption.id),
                "invite_redemption_id": str(invite_redemption.id),
                "entitlement_grant_id": str(activated.id),
                "child_batch_id": str(child_batch.id) if child_batch is not None else None,
                "child_invite_count": len(child_invites),
            },
            actor_context=OutboxActorContext(
                principal_type="customer",
                principal_id=str(user_id),
                auth_realm_id=str(current_realm.realm_id),
            ),
            source_context={"source_use_case": "RedeemInviteUseCase.execute"},
        )
        observe_growth_code_redemption(
            code_type="invite",
            surface=CUSTOMER_REDEEM_SURFACE,
            result="success",
        )
        observe_invite_redeemed(
            source_type=str(invite.source),
            surface=CUSTOMER_REDEEM_SURFACE,
            result="success",
        )
        observe_growth_code_redemption_duration(
            code_type="invite",
            surface=CUSTOMER_REDEEM_SURFACE,
            result="success",
            duration_seconds=perf_counter() - started_at,
        )
        log_growth_code_event(
            "growth_code.redeemed",
            surface=CUSTOMER_REDEEM_SURFACE,
            code_type="invite",
            action_context="redeem",
            result="success",
            growth_code_id=str(shadow_code.id),
            invite_code_id=str(invite.id),
            redemption_id=str(redemption.id),
            invite_redemption_id=str(invite_redemption.id),
            entitlement_grant_id=str(activated.id),
            owner_user_id=str(invite.owner_user_id),
            redeemer_user_id=str(user_id),
            child_invite_count=len(child_invites),
        )

        logger.info(
            "invite_redeemed",
            extra={
                **code_ref,
                "invite_id": str(invite.id),
                "user_id": str(user_id),
                "free_days": invite.free_days,
                "grant_plan_id": str(redeemed_invite.grant_plan_id or redeemed_invite.plan_id)
                if redeemed_invite.grant_plan_id or redeemed_invite.plan_id
                else None,
                "child_invite_count": len(child_invites),
            },
        )

        return RedeemedInviteResult(
            invite=redeemed_invite,
            entitlement_grant_id=activated.id,
            entitlement_snapshot=dict(activated.grant_snapshot or {}),
            redemption=redemption,
            invite_redemption=invite_redemption,
            child_batch=child_batch,
            child_invites=tuple(child_invites),
        )

    async def _build_idempotent_result(
        self,
        *,
        invite: InviteCodeModel,
        user_id: UUID,
        current_realm: RealmResolution,
        source_surface: str,
    ) -> RedeemedInviteResult:
        shadow_code = await self._registry.ensure_shadow_invite(invite)
        grant_snapshot, access_days = await self._build_grant_snapshot(invite)
        service_identity = await self._service_identities.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            provider_name="remnawave",
            origin_storefront_id=shadow_code.storefront_id,
        )
        grant = await self._entitlements.execute(
            service_identity_id=service_identity.service_identity.id,
            manual_source_key=f"invite:{invite.id}:redeemer:{user_id}",
            grant_snapshot=grant_snapshot,
            expires_at=(_coerce_utc(invite.used_at) or datetime.now(UTC)) + timedelta(days=access_days),
        )
        activated = await self._activate_entitlement.execute(
            entitlement_grant_id=grant.entitlement_grant.id,
            activated_by_admin_user_id=None,
        )
        redemption = await self._ensure_redemption(
            shadow_code_id=shadow_code.id,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            policy_version_id=shadow_code.policy_version_id,
        )
        invite_redemption = await self._ensure_invite_redemption(
            invite=invite,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            source_surface=source_surface,
            grant_snapshot=dict(activated.grant_snapshot or grant_snapshot),
        )
        child_batch, child_invites = await self._ensure_child_invites_after_redemption(
            invite=invite,
            redeemer_user_id=user_id,
            invite_redemption=invite_redemption,
            source_surface=source_surface,
        )
        if child_batch is not None:
            invite_redemption.child_batch_id = child_batch.id
            invite_redemption.child_issued_count = len(child_invites)
        await self._ensure_tree_state(invite=invite, invite_redemption=invite_redemption)
        shadow_code.status = "redeemed"
        shadow_code.uses_count = 1
        await self._session.flush()
        return RedeemedInviteResult(
            invite=invite,
            entitlement_grant_id=activated.id,
            entitlement_snapshot=dict(activated.grant_snapshot or {}),
            redemption=redemption,
            invite_redemption=invite_redemption,
            child_batch=child_batch,
            child_invites=tuple(child_invites),
        )

    async def _validate_invite_status(self, invite: InviteCodeModel) -> None:
        if invite.revoked_at is not None or invite.status == "revoked":
            raise ValueError("Invite code has been revoked")
        if invite.status not in {"issued", "active"}:
            raise ValueError("Invite code is not redeemable")

    async def _validate_campaign_policy(self, *, invite: InviteCodeModel, user_id: UUID, source_surface: str) -> None:
        version: InviteCampaignVersionModel | None = None
        campaign: InviteCampaignModel | None = None
        if invite.campaign_version_id is not None:
            version = await self._load_campaign_version(invite.campaign_version_id)
        if invite.campaign_id is not None:
            campaign = await self._session.get(InviteCampaignModel, invite.campaign_id)

        if campaign is not None:
            now = datetime.now(UTC)
            starts_at = _coerce_utc(campaign.starts_at)
            expires_at = _coerce_utc(campaign.expires_at)
            if campaign.status != "active":
                raise ValueError("Invite campaign is not active")
            if starts_at is not None and starts_at > now:
                raise ValueError("Invite campaign has not started")
            if expires_at is not None and expires_at <= now:
                raise ValueError("Invite campaign has expired")

        if version is not None:
            if version.status != "published":
                raise ValueError("Invite campaign version is not published")
            invite.redemption_policy = {**dict(version.redemption_policy or {}), **dict(invite.redemption_policy or {})}
            invite.child_policy = {**dict(version.child_policy or {}), **dict(invite.child_policy or {})}
            invite.risk_policy = {**dict(version.risk_policy or {}), **dict(invite.risk_policy or {})}

        allowed_surfaces = set(_string_list(invite.redemption_policy.get("allowed_surfaces")))
        if not allowed_surfaces and version is not None:
            allowed_surfaces = set(_string_list(version.allowed_surfaces))
        if allowed_surfaces and source_surface not in allowed_surfaces:
            raise ValueError("Invite code cannot be redeemed from this surface")

        per_user_redeem_cap = _positive_int(invite.redemption_policy.get("per_user_redeem_cap"), default=1)
        if invite.campaign_id is not None:
            existing = await self._session.execute(
                select(func.count())
                .select_from(InviteRedemptionModel)
                .where(
                    InviteRedemptionModel.invitee_user_id == user_id,
                    InviteRedemptionModel.campaign_id == invite.campaign_id,
                    InviteRedemptionModel.status == "redeemed",
                )
            )
            if int(existing.scalar_one()) >= per_user_redeem_cap:
                raise ValueError("Invite campaign redemption cap exceeded")

    async def _build_grant_snapshot(self, invite: InviteCodeModel) -> tuple[dict, int]:
        mode = str(invite.grant_mode or invite.entitlement_mode or "legacy_invite_access")
        duration_days = _positive_int(invite.grant_duration_days, default=_positive_int(invite.free_days, default=1))
        existing_snapshot = dict(invite.grant_snapshot or {})
        if not existing_snapshot:
            existing_snapshot = dict(invite.entitlement_snapshot or {})

        if mode == "custom_snapshot":
            if not existing_snapshot:
                raise ValueError("Invite custom entitlement snapshot is missing")
            snapshot = _normalize_grant_snapshot(
                grant_snapshot=existing_snapshot,
                expires_at=datetime.now(UTC) + timedelta(days=duration_days),
            )
            snapshot["source_type"] = "invite"
            return snapshot, duration_days

        grant_plan_id = invite.grant_plan_id or invite.plan_id
        if mode == "plan_snapshot":
            if grant_plan_id is None:
                raise ValueError("Invite plan-backed grant is missing a plan")
            plan = await self._plans.get_by_id(grant_plan_id)
            if plan is None:
                raise ValueError("Invite grant plan was not found")
            duration_days = _positive_int(invite.grant_duration_days, default=int(plan.duration_days))
            expires_at = datetime.now(UTC) + timedelta(days=duration_days)
            if existing_snapshot and existing_snapshot.get("plan_code"):
                snapshot = _normalize_grant_snapshot(
                    grant_snapshot=existing_snapshot,
                    expires_at=expires_at,
                )
            else:
                snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=expires_at, status="active")
            snapshot["period_days"] = duration_days
            snapshot["source_type"] = "invite"
            snapshot["entitlement_profile_key"] = invite.entitlement_profile_key or f"{plan.plan_code}_invite_v7"
            return snapshot, duration_days

        return _build_invite_entitlement_snapshot(duration_days), duration_days

    async def _ensure_invite_redemption(
        self,
        *,
        invite: InviteCodeModel,
        redeemer_user_id: UUID,
        entitlement_grant_id: UUID,
        source_surface: str,
        grant_snapshot: dict,
    ) -> InviteRedemptionModel:
        idempotency_key = f"invite:{invite.id}:redeemer:{redeemer_user_id}"
        existing = await self._session.execute(
            select(InviteRedemptionModel).where(InviteRedemptionModel.idempotency_key == idempotency_key)
        )
        item = existing.scalars().first()
        if item is not None:
            if item.entitlement_grant_id is None:
                item.entitlement_grant_id = entitlement_grant_id
            if not item.grant_snapshot:
                item.grant_snapshot = dict(grant_snapshot)
            await self._session.flush()
            return item

        root_invite_code_id = invite.root_invite_code_id or invite.id
        model = InviteRedemptionModel(
            invite_code_id=invite.id,
            campaign_id=invite.campaign_id,
            campaign_version_id=invite.campaign_version_id,
            root_invite_code_id=root_invite_code_id,
            parent_invite_code_id=invite.parent_invite_code_id,
            inviter_user_id=invite.owner_user_id,
            invitee_user_id=redeemer_user_id,
            generation_depth=int(invite.generation_depth or 0),
            source_surface=source_surface,
            entitlement_grant_id=entitlement_grant_id,
            granted_plan_id=invite.grant_plan_id or invite.plan_id,
            granted_plan_code=_string_or_none(grant_snapshot.get("plan_code")),
            granted_duration_days=_positive_int(
                grant_snapshot.get("period_days"),
                default=_positive_int(invite.grant_duration_days, default=invite.free_days),
            ),
            idempotency_key=idempotency_key,
            status="redeemed",
            grant_snapshot=dict(grant_snapshot),
            risk_decision={"decision": "allow", "source": "redeem_invite_use_case"},
            redeemed_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def _ensure_child_invites_after_redemption(
        self,
        *,
        invite: InviteCodeModel,
        redeemer_user_id: UUID,
        invite_redemption: InviteRedemptionModel,
        source_surface: str,
    ) -> tuple[InviteBatchModel | None, list[InviteCodeModel]]:
        policy = await self._resolve_child_policy(invite)
        count = _positive_int(policy.get("count"), default=0)
        max_depth = _positive_int(policy.get("max_generation_depth"), default=0)
        parent_depth = int(invite.generation_depth or 0)
        if count <= 0 or (max_depth > 0 and parent_depth >= max_depth):
            return None, []

        idempotency_key = (
            f"invite-child-batch:{invite.id}:redeemer:{redeemer_user_id}:"
            f"campaign:{invite.campaign_id or 'legacy'}:depth:{parent_depth + 1}"
        )
        existing_batch_result = await self._session.execute(
            select(InviteBatchModel).where(InviteBatchModel.idempotency_key == idempotency_key)
        )
        existing_batch = existing_batch_result.scalars().first()
        if existing_batch is not None:
            existing_codes = await self._session.execute(
                select(InviteCodeModel)
                .where(InviteCodeModel.batch_id == existing_batch.id)
                .order_by(InviteCodeModel.created_at.asc())
            )
            return existing_batch, list(existing_codes.scalars().all())

        expiry_days = _positive_int(policy.get("expiry_days"), default=30)
        expires_at = datetime.now(UTC) + timedelta(days=expiry_days)
        root_invite_code_id = invite.root_invite_code_id or invite.id
        grant_snapshot, access_days, child_plan_id = await self._build_child_grant_snapshot(
            invite=invite,
            policy=policy,
        )

        batch = InviteBatchModel(
            owner_user_id=redeemer_user_id,
            invite_campaign_id=invite.campaign_id,
            invite_campaign_version_id=invite.campaign_version_id,
            root_invite_code_id=root_invite_code_id,
            parent_invite_code_id=invite.id,
            source_redemption_id=invite_redemption.id,
            root_owner_user_id=invite.owner_user_id,
            generation_depth=parent_depth + 1,
            batch_kind="child_after_redemption",
            source_type="child_after_redemption",
            requested_count=count,
            issued_count=count,
            friend_days=access_days,
            expiry_mode="relative",
            expiry_days=expiry_days,
            expires_at=expires_at,
            entitlement_mode=invite.grant_mode or invite.entitlement_mode or "legacy_invite_access",
            entitlement_profile_key=invite.entitlement_profile_key,
            plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
            entitlement_snapshot=dict(grant_snapshot),
            grant_mode=invite.grant_mode or "legacy_invite_access",
            grant_plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
            grant_duration_days=access_days,
            grant_snapshot=dict(grant_snapshot),
            child_grant_plan_id=child_plan_id,
            child_grant_duration_days=access_days,
            child_policy=dict(invite.child_policy or {}),
            risk_policy=dict(invite.risk_policy or {}),
            redemption_policy=dict(invite.redemption_policy or {}),
            issue_policy={"source_surface": source_surface},
            status="issued",
            idempotency_key=idempotency_key,
        )
        self._session.add(batch)
        await self._session.flush()

        children: list[InviteCodeModel] = []
        for _ in range(count):
            raw_code = await self._generate_unique_code()
            children.append(
                InviteCodeModel(
                    code=raw_code,
                    owner_user_id=redeemer_user_id,
                    free_days=access_days,
                    plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
                    batch_id=batch.id,
                    campaign_id=invite.campaign_id,
                    campaign_version_id=invite.campaign_version_id,
                    root_invite_code_id=root_invite_code_id,
                    parent_invite_code_id=invite.id,
                    source_redemption_id=invite_redemption.id,
                    generation_depth=parent_depth + 1,
                    source_growth_code_id=invite.source_growth_code_id,
                    source_benefit_id=invite.source_benefit_id,
                    status="issued",
                    code_hash=hash_growth_code(raw_code),
                    code_prefix=build_growth_code_prefix(raw_code),
                    entitlement_mode=invite.entitlement_mode,
                    entitlement_profile_key=invite.entitlement_profile_key,
                    entitlement_snapshot=dict(grant_snapshot),
                    grant_mode=invite.grant_mode or "legacy_invite_access",
                    grant_plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
                    grant_duration_days=access_days,
                    grant_snapshot=dict(grant_snapshot),
                    child_grant_plan_id=child_plan_id,
                    child_grant_duration_days=access_days,
                    child_policy=dict(invite.child_policy or {}),
                    risk_policy=dict(invite.risk_policy or {}),
                    redemption_policy=dict(invite.redemption_policy or {}),
                    issue_policy={"source_surface": source_surface, "source_redemption_id": str(invite_redemption.id)},
                    source="child_after_redemption",
                    source_payment_id=None,
                    expires_at=expires_at,
                )
            )
        self._session.add_all(children)
        await self._session.flush()
        return batch, children

    async def _build_child_grant_snapshot(
        self,
        *,
        invite: InviteCodeModel,
        policy: dict,
    ) -> tuple[dict, int, UUID | None]:
        child_plan_id = _uuid_or_none(policy.get("grant_plan_id")) or invite.child_grant_plan_id
        duration_days = _positive_int(
            policy.get("grant_duration_days"),
            default=_positive_int(invite.child_grant_duration_days, default=_positive_int(invite.free_days, default=1)),
        )
        existing_snapshot = dict(policy.get("grant_snapshot") or {})
        if child_plan_id is not None:
            plan = await self._plans.get_by_id(child_plan_id)
            if plan is None:
                raise ValueError("Invite child grant plan was not found")
            expires_at = datetime.now(UTC) + timedelta(days=duration_days)
            if existing_snapshot and existing_snapshot.get("plan_code"):
                snapshot = _normalize_grant_snapshot(grant_snapshot=existing_snapshot, expires_at=expires_at)
            else:
                snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=expires_at, status="active")
            snapshot["period_days"] = duration_days
            snapshot["source_type"] = "invite_child"
            return snapshot, duration_days, child_plan_id

        parent_snapshot, parent_duration = await self._build_grant_snapshot(invite)
        return parent_snapshot, duration_days or parent_duration, invite.grant_plan_id or invite.plan_id

    async def _resolve_child_policy(self, invite: InviteCodeModel) -> dict:
        policy = dict(invite.child_policy or {})
        if invite.campaign_version_id is not None:
            version = await self._load_campaign_version(invite.campaign_version_id)
            if version is not None:
                version_policy = dict(version.child_policy or {})
                policy = {**version_policy, **policy}
                policy.setdefault("count", int(version.child_invite_count or 0))
                policy.setdefault("friend_days", int(version.child_invite_free_days or 0))
                policy.setdefault("expiry_days", int(version.child_invite_expiry_days or 0))
                policy.setdefault("max_generation_depth", int(version.max_generation_depth or 0))
        return policy

    async def _load_campaign_version(self, version_id: UUID | None) -> InviteCampaignVersionModel | None:
        if version_id is None:
            return None
        return await self._session.get(InviteCampaignVersionModel, version_id)

    async def _ensure_tree_state(
        self,
        *,
        invite: InviteCodeModel,
        invite_redemption: InviteRedemptionModel,
    ) -> None:
        root_invite_code_id = invite.root_invite_code_id or invite.id
        invite.root_invite_code_id = root_invite_code_id
        existing_edge = await self._session.execute(
            select(InviteTreeEdgeModel).where(InviteTreeEdgeModel.redemption_id == invite_redemption.id)
        )
        if existing_edge.scalars().first() is None:
            self._session.add(
                InviteTreeEdgeModel(
                    root_invite_code_id=root_invite_code_id,
                    parent_invite_code_id=invite.parent_invite_code_id,
                    redeemed_invite_code_id=invite.id,
                    redemption_id=invite_redemption.id,
                    campaign_id=invite.campaign_id,
                    campaign_version_id=invite.campaign_version_id,
                    child_batch_id=invite_redemption.child_batch_id,
                    granted_plan_id=invite_redemption.granted_plan_id,
                    granted_plan_code=invite_redemption.granted_plan_code,
                    inviter_user_id=invite.owner_user_id,
                    invitee_user_id=invite_redemption.invitee_user_id,
                    generation_depth=int(invite.generation_depth or 0),
                    status="active",
                )
            )
        await self._ensure_closure_path(
            root_invite_code_id=root_invite_code_id,
            ancestor_invite_code_id=invite.id,
            descendant_invite_code_id=invite.id,
            depth=0,
        )
        if invite.parent_invite_code_id is not None:
            parent_paths = await self._session.execute(
                select(InviteTreeClosureModel).where(
                    InviteTreeClosureModel.root_invite_code_id == root_invite_code_id,
                    InviteTreeClosureModel.descendant_invite_code_id == invite.parent_invite_code_id,
                )
            )
            paths = list(parent_paths.scalars().all())
            if not paths:
                await self._ensure_closure_path(
                    root_invite_code_id=root_invite_code_id,
                    ancestor_invite_code_id=invite.parent_invite_code_id,
                    descendant_invite_code_id=invite.id,
                    depth=1,
                )
            for path in paths:
                await self._ensure_closure_path(
                    root_invite_code_id=root_invite_code_id,
                    ancestor_invite_code_id=path.ancestor_invite_code_id,
                    descendant_invite_code_id=invite.id,
                    depth=int(path.depth or 0) + 1,
                )
        await self._session.flush()

    async def _ensure_closure_path(
        self,
        *,
        root_invite_code_id: UUID,
        ancestor_invite_code_id: UUID,
        descendant_invite_code_id: UUID,
        depth: int,
    ) -> None:
        existing = await self._session.execute(
            select(InviteTreeClosureModel).where(
                InviteTreeClosureModel.root_invite_code_id == root_invite_code_id,
                InviteTreeClosureModel.ancestor_invite_code_id == ancestor_invite_code_id,
                InviteTreeClosureModel.descendant_invite_code_id == descendant_invite_code_id,
            )
        )
        if existing.scalars().first() is not None:
            return
        self._session.add(
            InviteTreeClosureModel(
                root_invite_code_id=root_invite_code_id,
                ancestor_invite_code_id=ancestor_invite_code_id,
                descendant_invite_code_id=descendant_invite_code_id,
                depth=depth,
            )
        )

    async def _generate_unique_code(self) -> str:
        for _ in range(20):
            raw_code = secrets.token_urlsafe(7)[:10].upper()
            if await self._invite_repo.get_by_code(raw_code) is None:
                return raw_code
        raise ValueError("Unable to generate a unique invite code")

    async def _ensure_redemption(
        self,
        *,
        shadow_code_id: UUID,
        redeemer_user_id: UUID,
        entitlement_grant_id: UUID,
        policy_version_id: UUID | None,
    ) -> GrowthCodeRedemptionModel:
        existing_items = await self._growth_codes.list_redemptions(shadow_code_id)
        for item in existing_items:
            if item.redeemer_user_id == redeemer_user_id:
                return item
        return await self._growth_codes.create_redemption(
            GrowthCodeRedemptionModel(
                growth_code_id=shadow_code_id,
                code_type="invite",
                redeemer_user_id=redeemer_user_id,
                beneficiary_user_id=redeemer_user_id,
                entitlement_grant_id=entitlement_grant_id,
                policy_version_id=policy_version_id,
                status="redeemed",
                redeemed_at=datetime.now(UTC),
            )
        )

    async def _record_blocked_redemption(
        self,
        *,
        invite: InviteCodeModel,
        redeemer_user_id: UUID,
        source_surface: str,
        reason: str,
    ) -> None:
        if invite.is_used:
            return
        reason_hash = hashlib.sha256(reason.encode("utf-8")).hexdigest()[:24]
        idempotency_key = f"invite-blocked:{invite.id}:redeemer:{redeemer_user_id}:{reason_hash}"
        existing = await self._session.execute(
            select(InviteRedemptionModel.id).where(InviteRedemptionModel.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none() is not None:
            return
        root_invite_code_id = invite.root_invite_code_id or invite.id
        self._session.add(
            InviteRedemptionModel(
                invite_code_id=invite.id,
                campaign_id=invite.campaign_id,
                campaign_version_id=invite.campaign_version_id,
                root_invite_code_id=root_invite_code_id,
                parent_invite_code_id=invite.parent_invite_code_id,
                inviter_user_id=invite.owner_user_id,
                invitee_user_id=redeemer_user_id,
                generation_depth=int(invite.generation_depth or 0),
                source_surface=source_surface,
                idempotency_key=idempotency_key,
                status="blocked",
                blocked_reason=reason[:160],
                grant_snapshot=dict(invite.grant_snapshot or invite.entitlement_snapshot or {}),
                service_snapshot={},
                risk_decision={"decision": "block", "reason": reason[:160]},
                metadata_json={"blocked_reason": reason[:160]},
                created_at=datetime.now(UTC),
            )
        )
        await self._session.flush()


def _build_invite_entitlement_snapshot(friend_days: int) -> dict:
    return {
        "status": "active",
        "plan_uuid": None,
        "plan_code": "invite",
        "display_name": "Invite Access",
        "period_days": int(friend_days),
        "expires_at": None,
        "effective_entitlements": {
            "device_limit": 1,
            "traffic_policy": "fair_use",
            "display_traffic_label": "Unlimited",
            "connection_modes": ["standard"],
            "server_pool": ["shared"],
            "support_sla": "standard",
            "dedicated_ip_count": 0,
        },
        "invite_bundle": {"count": 0, "friend_days": 0, "expiry_days": 0},
        "is_trial": False,
        "addons": [],
        "source_type": "invite",
        "entitlement_profile_key": "invite_limited_access_v1",
    }


def _normalize_grant_snapshot(*, grant_snapshot: dict, expires_at: datetime | None) -> dict:
    snapshot = _build_invite_entitlement_snapshot(0)
    provided = dict(grant_snapshot or {})
    effective_entitlements = dict(snapshot["effective_entitlements"])
    effective_entitlements.update(dict(provided.get("effective_entitlements") or {}))
    invite_bundle = dict(snapshot["invite_bundle"])
    invite_bundle.update(dict(provided.get("invite_bundle") or {}))
    snapshot.update(
        {
            key: value
            for key, value in provided.items()
            if key not in {"effective_entitlements", "invite_bundle", "addons", "status", "expires_at"}
        }
    )
    snapshot["effective_entitlements"] = effective_entitlements
    snapshot["invite_bundle"] = invite_bundle
    snapshot["addons"] = list(provided.get("addons") or [])
    snapshot["status"] = "active"
    snapshot["is_trial"] = bool(provided.get("is_trial", False))
    snapshot["expires_at"] = expires_at.isoformat() if expires_at else provided.get("expires_at")
    return snapshot


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _safe_invite_code_ref(code: str) -> dict[str, object]:
    normalized = code.strip()
    return {
        "code_hash": hash_growth_code(normalized),
        "code_prefix": build_growth_code_prefix(normalized),
        "code_length": len(normalized),
    }


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _policy_bool(policy: dict, key: str, *, default: bool) -> bool:
    value = policy.get(key)
    if isinstance(value, bool):
        return value
    return default


def _uuid_or_none(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


async def _pg_advisory_xact_lock(session, scope: str) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    lock_id = int.from_bytes(hashlib.blake2b(scope.encode("utf-8"), digest_size=8).digest(), "big", signed=True)
    await session.execute(select(func.pg_advisory_xact_lock(lock_id)))
