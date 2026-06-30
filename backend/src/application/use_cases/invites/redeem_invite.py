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
from src.application.use_cases.invites.campaigns import validate_invite_campaign_issue_caps
from src.application.use_cases.invites.lifetime_policy import (
    INVITE_DURATION_LIFETIME,
    INVITE_EXPIRY_RELATIVE,
    apply_invite_entitlement_overrides,
    display_days_for_duration,
    is_lifetime_duration,
    normalize_invite_duration_mode,
    normalize_invite_expiry_mode,
    positive_int_or_none,
    resolve_invite_expiry,
)
from src.application.use_cases.service_access.entitlements import (
    ActivateEntitlementGrantUseCase,
    CreateEntitlementGrantUseCase,
    GetCurrentEntitlementStateUseCase,
)
from src.application.use_cases.service_access.service_identities import CreateServiceIdentityUseCase
from src.domain.exceptions import (
    InviteCodeAlreadyRedeemedByUserError,
    InviteCodeAlreadyUsedError,
    InviteCodeExhaustedError,
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
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_REDEEM_SURFACE,
    log_growth_code_event,
    observe_growth_code_redemption,
    observe_growth_code_redemption_duration,
    observe_invite_device_override_used,
    observe_invite_redeemed,
    observe_lifetime_child_invites_issued,
    observe_lifetime_invite_redemption,
)
from src.presentation.dependencies.auth_realms import RealmResolution

logger = logging.getLogger(__name__)

INVITE_USAGE_SINGLE = "single_use"
INVITE_USAGE_MULTI = "multi_use"


@dataclass(frozen=True)
class RedeemedInviteResult:
    invite: InviteCodeModel
    entitlement_grant_id: UUID
    entitlement_snapshot: dict
    redemption: GrowthCodeRedemptionModel
    invite_redemption: InviteRedemptionModel | None = None
    child_batch: InviteBatchModel | None = None
    child_invites: tuple[InviteCodeModel, ...] = ()


@dataclass(frozen=True)
class InviteRedemptionRuntimeContext:
    client_ip_hash: str | None = None
    device_key_hash: str | None = None


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
        runtime_context: InviteRedemptionRuntimeContext | None = None,
    ) -> RedeemedInviteResult:
        """Redeem *code* on behalf of *user_id*.

        Raises:
            InviteCodeNotFoundError: code does not exist or is unavailable.
            InviteCodeAlreadyRedeemedByUserError: code has already been redeemed by the same user.
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

        await _pg_advisory_xact_lock(self._session, f"invite-redeem-code:{invite.id}")
        await _pg_advisory_xact_lock(
            self._session,
            f"invite-redeem:{invite.campaign_id or invite.id}:redeemer:{user_id}",
        )
        usage_mode = _invite_usage_mode(invite)

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

        existing_redemption = await self._get_invite_redemption_by_redeemer(invite_id=invite.id, user_id=user_id)
        if existing_redemption is not None:
            await self._record_blocked_redemption(
                invite=invite,
                redeemer_user_id=user_id,
                source_surface=source_surface,
                reason="Invite code already redeemed by this user",
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeAlreadyRedeemedByUserError()

        if usage_mode == INVITE_USAGE_SINGLE and invite.is_used:
            if invite.used_by_user_id == user_id:
                await self._record_blocked_redemption(
                    invite=invite,
                    redeemer_user_id=user_id,
                    source_surface=source_surface,
                    reason="Invite code already redeemed by this user",
                )
                observe_growth_code_redemption_duration(
                    code_type="invite",
                    surface=CUSTOMER_REDEEM_SURFACE,
                    result="failure",
                    duration_seconds=perf_counter() - started_at,
                )
                raise InviteCodeAlreadyRedeemedByUserError()
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

        if _invite_is_exhausted(invite):
            await self._record_blocked_redemption(
                invite=invite,
                redeemer_user_id=user_id,
                source_surface=source_surface,
                reason="Invite code exhausted",
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeExhaustedError()

        try:
            await self._validate_invite_status(invite)
            await self._validate_campaign_policy(
                invite=invite,
                user_id=user_id,
                auth_realm_id=UUID(current_realm.realm_id),
                source_surface=source_surface,
                runtime_context=runtime_context,
            )
            self._ensure_invite_capacity_available(invite)
        except InviteCodeExhaustedError:
            await self._record_blocked_redemption(
                invite=invite,
                redeemer_user_id=user_id,
                source_surface=source_surface,
                reason="Invite code exhausted",
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise
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
        try:
            await self._preflight_child_issue_caps(invite=invite, redeemer_user_id=user_id)
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

        grant_snapshot, access_expires_at, access_days = await self._build_grant_snapshot(invite)
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
        redeemed_at = datetime.now(UTC)
        redeemed_invite = await self._finalize_invite_redemption_state(
            invite=invite,
            redeemer_user_id=user_id,
            redeemed_at=redeemed_at,
        )
        redemption = await self._ensure_redemption(
            shadow_code_id=shadow_code.id,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            policy_version_id=shadow_code.policy_version_id,
        )
        invite_redemption = await self._ensure_invite_redemption(
            invite=redeemed_invite,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            source_surface=source_surface,
            grant_snapshot=dict(activated.grant_snapshot or grant_snapshot),
            runtime_context=runtime_context,
            redeemed_at=redeemed_at,
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
        shadow_code.uses_count = max(int(shadow_code.uses_count or 0), int(redeemed_invite.redeemed_count or 1))
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
        if grant_snapshot.get("duration_mode") == INVITE_DURATION_LIFETIME or grant_snapshot.get("lifetime") is True:
            observe_lifetime_invite_redemption(
                plan_code=_string_or_none(grant_snapshot.get("plan_code")),
                source_type=str(invite.source),
                surface=CUSTOMER_REDEEM_SURFACE,
                result="success",
            )
        if grant_snapshot.get("device_limit_override") is not None:
            observe_invite_device_override_used(
                plan_code=_string_or_none(grant_snapshot.get("plan_code")),
                duration_mode=_string_or_none(grant_snapshot.get("duration_mode")),
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
        runtime_context: InviteRedemptionRuntimeContext | None,
    ) -> RedeemedInviteResult:
        shadow_code = await self._registry.ensure_shadow_invite(invite)
        grant_snapshot, access_expires_at, _access_days = await self._build_grant_snapshot(
            invite,
            granted_at=_coerce_utc(invite.used_at) or datetime.now(UTC),
        )
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
            runtime_context=runtime_context,
            redeemed_at=_coerce_utc(invite.used_at) or datetime.now(UTC),
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
        shadow_code.uses_count = max(int(shadow_code.uses_count or 0), int(invite.redeemed_count or 1))
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

    async def _validate_campaign_policy(
        self,
        *,
        invite: InviteCodeModel,
        user_id: UUID,
        auth_realm_id: UUID,
        source_surface: str,
        runtime_context: InviteRedemptionRuntimeContext | None,
    ) -> None:
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

        per_user_redeem_cap = _positive_int(
            invite.per_user_redemption_cap,
            default=_positive_int(invite.redemption_policy.get("per_user_redeem_cap"), default=1),
        )
        existing = await self._session.execute(
            select(func.count())
            .select_from(InviteRedemptionModel)
            .where(
                InviteRedemptionModel.invitee_user_id == user_id,
                InviteRedemptionModel.invite_code_id == invite.id,
                InviteRedemptionModel.status == "redeemed",
            )
        )
        if int(existing.scalar_one()) >= per_user_redeem_cap:
            raise InviteCodeAlreadyRedeemedByUserError()
        await self._validate_invite_abuse_controls(
            invite=invite,
            user_id=user_id,
            auth_realm_id=auth_realm_id,
            runtime_context=runtime_context,
        )

    async def _validate_invite_abuse_controls(
        self,
        *,
        invite: InviteCodeModel,
        user_id: UUID,
        auth_realm_id: UUID,
        runtime_context: InviteRedemptionRuntimeContext | None,
    ) -> None:
        if invite.campaign_id is None:
            return
        risk_policy = dict(invite.risk_policy or {})
        usage_mode = _invite_usage_mode(invite)
        root_lifetime = is_lifetime_duration(invite.grant_duration_mode) or bool(
            (invite.grant_snapshot or {}).get("lifetime")
        )
        child_lifetime = is_lifetime_duration(invite.child_grant_duration_mode)
        no_expiry = invite.expires_at is None or invite.child_invite_expiry_mode == "none"
        lifetime_like = root_lifetime or child_lifetime or no_expiry
        if not lifetime_like and usage_mode != INVITE_USAGE_MULTI:
            return

        if lifetime_like and not _policy_bool(invite.redemption_policy, "require_no_active_access", default=True):
            raise ValueError("Lifetime invite campaigns require no-active-access redemption policy")
        if lifetime_like and not _policy_bool(invite.redemption_policy, "block_self_redemption", default=True):
            raise ValueError("Lifetime invite campaigns require self-redemption blocking")
        if lifetime_like and _positive_int(invite.redemption_policy.get("per_user_redeem_cap"), default=0) != 1:
            raise ValueError("Lifetime invite campaigns require per-user redemption cap of 1")

        max_redemptions_per_device = _optional_positive_int(risk_policy.get("max_redemptions_per_device"))
        max_redemptions_per_ip_window = _optional_positive_int(risk_policy.get("max_redemptions_per_ip_window"))
        velocity_window_hours = _optional_positive_int(risk_policy.get("velocity_window_hours"))
        if max_redemptions_per_device is None or max_redemptions_per_device > 1:
            raise ValueError("Invite campaigns require device redemption cap")
        if max_redemptions_per_ip_window is None or max_redemptions_per_ip_window > 3:
            raise ValueError("Invite campaigns require IP window redemption cap")
        if velocity_window_hours is None or velocity_window_hours > 24:
            raise ValueError("Invite campaigns require velocity window <= 24 hours")
        if risk_policy.get("deny_disposable_email") is not True:
            raise ValueError("Invite campaigns require disposable email deny policy")
        if risk_policy.get("deny_known_abuse_subject") is not True:
            raise ValueError("Invite campaigns require known-abuse subject deny policy")

        user = await self._session.get(MobileUserModel, user_id)
        if user is not None and _is_disposable_email_domain(user.email):
            raise ValueError("Invite code cannot be redeemed by disposable email accounts")

        risk_subject = await self._session.execute(
            select(RiskSubjectModel).where(
                RiskSubjectModel.principal_class == "customer",
                RiskSubjectModel.principal_subject == str(user_id),
                RiskSubjectModel.auth_realm_id == auth_realm_id,
            )
        )
        subject = risk_subject.scalars().first()
        if subject is not None and (
            subject.status in {"blocked", "denied", "suspended"} or subject.risk_level in {"high", "critical"}
        ):
            raise ValueError("Invite code cannot be redeemed by known-abuse subjects")

        if runtime_context is None or not runtime_context.device_key_hash:
            raise ValueError("Invite redemption requires device context")
        device_redeemed = await self._session.execute(
            select(func.count())
            .select_from(InviteRedemptionModel)
            .where(
                InviteRedemptionModel.campaign_id == invite.campaign_id,
                InviteRedemptionModel.status == "redeemed",
                InviteRedemptionModel.risk_decision["device_key_hash"].as_string() == runtime_context.device_key_hash,
            )
        )
        if int(device_redeemed.scalar_one()) >= max_redemptions_per_device:
            raise ValueError("Invite campaign device redemption cap exceeded")

        if not runtime_context.client_ip_hash:
            raise ValueError("Invite redemption requires client IP context")
        window_start = datetime.now(UTC) - timedelta(hours=velocity_window_hours)
        ip_redeemed = await self._session.execute(
            select(func.count())
            .select_from(InviteRedemptionModel)
            .where(
                InviteRedemptionModel.campaign_id == invite.campaign_id,
                InviteRedemptionModel.status == "redeemed",
                InviteRedemptionModel.created_at >= window_start,
                InviteRedemptionModel.risk_decision["client_ip_hash"].as_string() == runtime_context.client_ip_hash,
            )
        )
        if int(ip_redeemed.scalar_one()) >= max_redemptions_per_ip_window:
            raise ValueError("Invite campaign IP window redemption cap exceeded")

    async def _get_invite_redemption_by_redeemer(
        self,
        *,
        invite_id: UUID,
        user_id: UUID,
    ) -> InviteRedemptionModel | None:
        result = await self._session.execute(
            select(InviteRedemptionModel)
            .where(
                InviteRedemptionModel.invite_code_id == invite_id,
                InviteRedemptionModel.invitee_user_id == user_id,
                InviteRedemptionModel.status.in_(("redeemed", "reversed")),
            )
            .order_by(InviteRedemptionModel.created_at.desc())
        )
        return result.scalars().first()

    def _ensure_invite_capacity_available(self, invite: InviteCodeModel) -> None:
        if _invite_usage_mode(invite) == INVITE_USAGE_SINGLE:
            return
        max_redemptions = _optional_positive_int(invite.max_redemptions)
        if max_redemptions is not None and int(invite.active_redemptions_count or 0) >= max_redemptions:
            raise InviteCodeExhaustedError()

    async def _finalize_invite_redemption_state(
        self,
        *,
        invite: InviteCodeModel,
        redeemer_user_id: UUID,
        redeemed_at: datetime,
    ) -> InviteCodeModel:
        usage_mode = _invite_usage_mode(invite)
        if usage_mode == INVITE_USAGE_SINGLE:
            invite.is_used = True
            invite.used_by_user_id = redeemer_user_id
            invite.used_at = redeemed_at
            invite.status = "redeemed"
            invite.max_redemptions = invite.max_redemptions or 1
            invite.redeemed_count = max(int(invite.redeemed_count or 0), 1)
            invite.active_redemptions_count = max(int(invite.active_redemptions_count or 0), 1)
            invite.first_redeemed_at = invite.first_redeemed_at or redeemed_at
            invite.last_redeemed_at = redeemed_at
            invite.exhausted_at = invite.exhausted_at or redeemed_at
            invite.per_user_redemption_cap = max(int(invite.per_user_redemption_cap or 1), 1)
            await self._session.flush()
            return invite

        max_redemptions = _optional_positive_int(invite.max_redemptions)
        active_count = int(invite.active_redemptions_count or 0)
        if max_redemptions is not None and active_count >= max_redemptions:
            invite.is_used = True
            invite.status = "exhausted"
            invite.exhausted_at = invite.exhausted_at or redeemed_at
            await self._session.flush()
            raise InviteCodeExhaustedError()

        invite.used_by_user_id = redeemer_user_id
        invite.used_at = redeemed_at
        invite.redeemed_count = int(invite.redeemed_count or 0) + 1
        invite.active_redemptions_count = active_count + 1
        invite.first_redeemed_at = invite.first_redeemed_at or redeemed_at
        invite.last_redeemed_at = redeemed_at
        invite.per_user_redemption_cap = max(int(invite.per_user_redemption_cap or 1), 1)
        if max_redemptions is not None and invite.active_redemptions_count >= max_redemptions:
            invite.is_used = True
            invite.status = "exhausted"
            invite.exhausted_at = invite.exhausted_at or redeemed_at
        else:
            invite.is_used = False
            invite.status = "active"
            invite.exhausted_at = None
        await self._session.flush()
        return invite

    async def _build_grant_snapshot(
        self,
        invite: InviteCodeModel,
        *,
        granted_at: datetime | None = None,
    ) -> tuple[dict, datetime | None, int]:
        mode = str(invite.grant_mode or invite.entitlement_mode or "legacy_invite_access")
        duration_mode = normalize_invite_duration_mode(invite.grant_duration_mode)
        duration_days = display_days_for_duration(
            duration_mode,
            invite.grant_duration_days if invite.grant_duration_days is not None else invite.free_days,
        )
        access_expires_at = (
            None
            if duration_mode == INVITE_DURATION_LIFETIME
            else (granted_at or datetime.now(UTC)) + timedelta(days=duration_days)
        )
        existing_snapshot = dict(invite.grant_snapshot or {})
        if not existing_snapshot:
            existing_snapshot = dict(invite.entitlement_snapshot or {})

        if mode == "custom_snapshot":
            if not existing_snapshot:
                raise ValueError("Invite custom entitlement snapshot is missing")
            snapshot = _normalize_grant_snapshot(
                grant_snapshot=existing_snapshot,
                expires_at=access_expires_at,
            )
            snapshot["source_type"] = "invite"
            snapshot = apply_invite_entitlement_overrides(
                snapshot=snapshot,
                duration_mode=duration_mode,
                duration_days=None if duration_mode == INVITE_DURATION_LIFETIME else duration_days,
                expires_at=access_expires_at,
                device_limit_override=invite.grant_device_limit_override,
            )
            return snapshot, access_expires_at, duration_days

        grant_plan_id = invite.grant_plan_id or invite.plan_id
        if mode == "plan_snapshot":
            if grant_plan_id is None:
                raise ValueError("Invite plan-backed grant is missing a plan")
            plan = await self._plans.get_by_id(grant_plan_id)
            if plan is None:
                raise ValueError("Invite grant plan was not found")
            if not is_lifetime_duration(duration_mode):
                duration_days = _positive_int(invite.grant_duration_days, default=int(plan.duration_days))
                access_expires_at = (granted_at or datetime.now(UTC)) + timedelta(days=duration_days)
            if existing_snapshot and existing_snapshot.get("plan_code"):
                snapshot = _normalize_grant_snapshot(
                    grant_snapshot=existing_snapshot,
                    expires_at=access_expires_at,
                )
            else:
                snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=access_expires_at, status="active")
            snapshot = apply_invite_entitlement_overrides(
                snapshot=snapshot,
                duration_mode=duration_mode,
                duration_days=None if duration_mode == INVITE_DURATION_LIFETIME else duration_days,
                expires_at=access_expires_at,
                device_limit_override=invite.grant_device_limit_override,
            )
            snapshot["source_type"] = "invite"
            snapshot["entitlement_profile_key"] = invite.entitlement_profile_key or f"{plan.plan_code}_invite_v7"
            return snapshot, access_expires_at, duration_days

        snapshot = apply_invite_entitlement_overrides(
            snapshot=_build_invite_entitlement_snapshot(duration_days),
            duration_mode=duration_mode,
            duration_days=None if duration_mode == INVITE_DURATION_LIFETIME else duration_days,
            expires_at=access_expires_at,
            device_limit_override=invite.grant_device_limit_override,
        )
        return snapshot, access_expires_at, duration_days

    async def _ensure_invite_redemption(
        self,
        *,
        invite: InviteCodeModel,
        redeemer_user_id: UUID,
        entitlement_grant_id: UUID,
        source_surface: str,
        grant_snapshot: dict,
        runtime_context: InviteRedemptionRuntimeContext | None,
        redeemed_at: datetime,
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
            if runtime_context is not None:
                item.risk_decision = {
                    **dict(item.risk_decision or {}),
                    **_runtime_context_payload(runtime_context),
                }
                item.device_key_hash = item.device_key_hash or runtime_context.device_key_hash
                item.client_ip_hash = item.client_ip_hash or runtime_context.client_ip_hash
            item.usage_mode_snapshot = item.usage_mode_snapshot or _invite_usage_mode(invite)
            item.redemption_sequence = item.redemption_sequence or int(invite.redeemed_count or 1)
            item.code_redemptions_count_after = item.code_redemptions_count_after or int(invite.redeemed_count or 1)
            await self._session.flush()
            return item

        root_invite_code_id = invite.root_invite_code_id or invite.id
        redemptions_after = int(invite.redeemed_count or 1)
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
            granted_duration_days=None
            if grant_snapshot.get("duration_mode") == INVITE_DURATION_LIFETIME
            else _positive_int(
                grant_snapshot.get("period_days"),
                default=_positive_int(invite.grant_duration_days, default=invite.free_days),
            ),
            usage_mode_snapshot=_invite_usage_mode(invite),
            redemption_sequence=redemptions_after,
            code_redemptions_count_after=redemptions_after,
            device_key_hash=runtime_context.device_key_hash if runtime_context is not None else None,
            client_ip_hash=runtime_context.client_ip_hash if runtime_context is not None else None,
            user_agent_hash=None,
            idempotency_key=idempotency_key,
            status="redeemed",
            grant_snapshot=dict(grant_snapshot),
            risk_decision={
                "decision": "allow",
                "source": "redeem_invite_use_case",
                **_runtime_context_payload(runtime_context),
            },
            redeemed_at=redeemed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def _preflight_child_issue_caps(self, *, invite: InviteCodeModel, redeemer_user_id: UUID) -> None:
        policy = await self._resolve_child_policy(invite)
        count = _positive_int(policy.get("count"), default=0)
        max_depth = _positive_int(policy.get("max_generation_depth"), default=0)
        parent_depth = int(invite.generation_depth or 0)
        if count <= 0 or (max_depth > 0 and parent_depth >= max_depth) or invite.campaign_id is None:
            return

        idempotency_key = (
            f"invite-child-batch:{invite.id}:redeemer:{redeemer_user_id}:"
            f"campaign:{invite.campaign_id or 'legacy'}:depth:{parent_depth + 1}"
        )
        existing_batch_result = await self._session.execute(
            select(InviteBatchModel.id).where(InviteBatchModel.idempotency_key == idempotency_key)
        )
        if existing_batch_result.scalar_one_or_none() is not None:
            return

        campaign = await self._session.get(InviteCampaignModel, invite.campaign_id)
        if campaign is None:
            return
        await _pg_advisory_xact_lock(self._session, f"invite-campaign-issue:{campaign.id}:global")
        await _pg_advisory_xact_lock(self._session, f"invite-campaign-issue:{campaign.id}:{redeemer_user_id}")
        await validate_invite_campaign_issue_caps(
            self._session,
            campaign=campaign,
            owner_user_id=redeemer_user_id,
            requested_count=count,
        )

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

        expiry_mode = normalize_invite_expiry_mode(
            str(policy.get("expiry_mode") or invite.child_invite_expiry_mode or INVITE_EXPIRY_RELATIVE)
        )
        expiry = resolve_invite_expiry(
            expiry_mode=expiry_mode,
            expiry_days=policy.get("expiry_days"),
            expires_at=_parse_datetime(policy.get("expires_at")),
            now=datetime.now(UTC),
        )
        child_usage_mode = _normalize_invite_usage_mode(policy.get("usage_mode") or policy.get("child_usage_mode"))
        child_max_redemptions = _optional_positive_int(
            policy.get("max_redemptions") or policy.get("child_max_redemptions")
        )
        if child_usage_mode == INVITE_USAGE_SINGLE:
            child_max_redemptions = 1
        child_per_user_cap = _positive_int(
            policy.get("per_user_redemption_cap") or policy.get("child_per_user_redemption_cap"),
            default=1,
        )
        root_invite_code_id = invite.root_invite_code_id or invite.id
        (
            grant_snapshot,
            _access_expires_at,
            access_days,
            child_plan_id,
            child_duration_mode,
            child_device_limit_override,
        ) = await self._build_child_grant_snapshot(
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
            expiry_mode=expiry.expiry_mode,
            expiry_days=expiry.expiry_days,
            expires_at=expiry.expires_at,
            usage_mode=child_usage_mode,
            max_redemptions_per_code=child_max_redemptions,
            per_user_redemption_cap=child_per_user_cap,
            multi_use_policy=dict(policy.get("multi_use_policy") or invite.multi_use_policy or {}),
            entitlement_mode=invite.grant_mode or invite.entitlement_mode or "legacy_invite_access",
            entitlement_profile_key=invite.entitlement_profile_key,
            plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
            entitlement_snapshot=dict(grant_snapshot),
            grant_mode=invite.grant_mode or "legacy_invite_access",
            grant_plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
            grant_duration_mode=child_duration_mode,
            grant_duration_days=None if child_duration_mode == INVITE_DURATION_LIFETIME else access_days,
            grant_device_limit_override=child_device_limit_override,
            grant_snapshot=dict(grant_snapshot),
            child_grant_plan_id=child_plan_id,
            child_grant_duration_mode=child_duration_mode,
            child_grant_duration_days=None if child_duration_mode == INVITE_DURATION_LIFETIME else access_days,
            child_grant_device_limit_override=child_device_limit_override,
            child_invite_expiry_mode=expiry.expiry_mode,
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
                    usage_mode=child_usage_mode,
                    max_redemptions=child_max_redemptions,
                    per_user_redemption_cap=child_per_user_cap,
                    multi_use_policy=dict(policy.get("multi_use_policy") or invite.multi_use_policy or {}),
                    code_hash=hash_growth_code(raw_code),
                    code_prefix=build_growth_code_prefix(raw_code),
                    entitlement_mode=invite.entitlement_mode,
                    entitlement_profile_key=invite.entitlement_profile_key,
                    entitlement_snapshot=dict(grant_snapshot),
                    grant_mode=invite.grant_mode or "legacy_invite_access",
                    grant_plan_id=child_plan_id or invite.grant_plan_id or invite.plan_id,
                    grant_duration_mode=child_duration_mode,
                    grant_duration_days=None if child_duration_mode == INVITE_DURATION_LIFETIME else access_days,
                    grant_device_limit_override=child_device_limit_override,
                    grant_snapshot=dict(grant_snapshot),
                    child_grant_plan_id=child_plan_id,
                    child_grant_duration_mode=child_duration_mode,
                    child_grant_duration_days=None if child_duration_mode == INVITE_DURATION_LIFETIME else access_days,
                    child_grant_device_limit_override=child_device_limit_override,
                    child_invite_expiry_mode=expiry.expiry_mode,
                    child_policy=dict(invite.child_policy or {}),
                    risk_policy=dict(invite.risk_policy or {}),
                    redemption_policy=dict(invite.redemption_policy or {}),
                    issue_policy={"source_surface": source_surface, "source_redemption_id": str(invite_redemption.id)},
                    source="child_after_redemption",
                    source_payment_id=None,
                    expires_at=expiry.expires_at,
                )
            )
        self._session.add_all(children)
        await self._session.flush()
        if child_duration_mode == INVITE_DURATION_LIFETIME:
            observe_lifetime_child_invites_issued(
                plan_code=_string_or_none(grant_snapshot.get("plan_code")),
                expiry_mode=expiry.expiry_mode,
                result="success",
            )
        return batch, children

    async def _build_child_grant_snapshot(
        self,
        *,
        invite: InviteCodeModel,
        policy: dict,
    ) -> tuple[dict, datetime | None, int, UUID | None, str, int | None]:
        child_plan_id = _uuid_or_none(policy.get("grant_plan_id")) or invite.child_grant_plan_id
        duration_mode = normalize_invite_duration_mode(
            str(policy.get("grant_duration_mode") or invite.child_grant_duration_mode or invite.grant_duration_mode)
        )
        duration_days = display_days_for_duration(
            duration_mode,
            policy.get("grant_duration_days")
            if policy.get("grant_duration_days") is not None
            else invite.child_grant_duration_days,
        )
        device_limit_override = positive_int_or_none(policy.get("grant_device_limit_override"))
        if device_limit_override is None:
            device_limit_override = invite.child_grant_device_limit_override or invite.grant_device_limit_override
        granted_at = datetime.now(UTC)
        expires_at = None if duration_mode == INVITE_DURATION_LIFETIME else granted_at + timedelta(days=duration_days)
        existing_snapshot = dict(policy.get("grant_snapshot") or {})
        if child_plan_id is not None:
            plan = await self._plans.get_by_id(child_plan_id)
            if plan is None:
                raise ValueError("Invite child grant plan was not found")
            if existing_snapshot and existing_snapshot.get("plan_code"):
                snapshot = _normalize_grant_snapshot(grant_snapshot=existing_snapshot, expires_at=expires_at)
            else:
                snapshot = EntitlementsService.build_snapshot(plan=plan, expires_at=expires_at, status="active")
            snapshot = apply_invite_entitlement_overrides(
                snapshot=snapshot,
                duration_mode=duration_mode,
                duration_days=None if duration_mode == INVITE_DURATION_LIFETIME else duration_days,
                expires_at=expires_at,
                device_limit_override=device_limit_override,
            )
            snapshot["source_type"] = "invite_child"
            return snapshot, expires_at, duration_days, child_plan_id, duration_mode, device_limit_override

        parent_snapshot, parent_expires_at, parent_duration = await self._build_grant_snapshot(invite)
        return (
            parent_snapshot,
            parent_expires_at,
            duration_days or parent_duration,
            invite.grant_plan_id or invite.plan_id,
            duration_mode,
            device_limit_override,
        )

    async def _resolve_child_policy(self, invite: InviteCodeModel) -> dict:
        policy = dict(invite.child_policy or {})
        if invite.campaign_version_id is not None:
            version = await self._load_campaign_version(invite.campaign_version_id)
            if version is not None:
                version_policy = dict(version.child_policy or {})
                policy = {**version_policy, **policy}
                policy.setdefault("count", int(version.child_invite_count or 0))
                policy.setdefault("friend_days", int(version.child_invite_free_days or 0))
                policy.setdefault("grant_duration_mode", version.child_grant_duration_mode)
                policy.setdefault("grant_device_limit_override", version.child_grant_device_limit_override)
                policy.setdefault("expiry_mode", version.child_invite_expiry_mode)
                policy.setdefault("expiry_days", int(version.child_invite_expiry_days or 0))
                policy.setdefault("usage_mode", version.child_usage_mode)
                policy.setdefault("max_redemptions", version.child_max_redemptions)
                policy.setdefault("per_user_redemption_cap", version.child_per_user_redemption_cap)
                policy.setdefault("multi_use_policy", dict(version.multi_use_policy or {}))
                if version.child_invite_expires_at is not None:
                    policy.setdefault("expires_at", version.child_invite_expires_at.isoformat())
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
                usage_mode_snapshot=_invite_usage_mode(invite),
                redemption_sequence=None,
                code_redemptions_count_after=int(invite.redeemed_count or 0),
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


def _parse_datetime(value: object) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return _coerce_utc(value)
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00") if raw.endswith("Z") else raw)
    except ValueError:
        return None
    return _coerce_utc(parsed)


def _safe_invite_code_ref(code: str) -> dict[str, object]:
    normalized = code.strip()
    return {
        "code_hash": hash_growth_code(normalized),
        "code_prefix": build_growth_code_prefix(normalized),
        "code_length": len(normalized),
    }


def _positive_int(value: object, *, default: int) -> int:
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return default
    else:
        return default
    return parsed if parsed > 0 else default


def _optional_positive_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed > 0 else None


def _normalize_invite_usage_mode(value: object) -> str:
    normalized = str(value or INVITE_USAGE_SINGLE).strip().lower()
    return INVITE_USAGE_MULTI if normalized == INVITE_USAGE_MULTI else INVITE_USAGE_SINGLE


def _invite_usage_mode(invite: InviteCodeModel) -> str:
    return _normalize_invite_usage_mode(getattr(invite, "usage_mode", INVITE_USAGE_SINGLE))


def _invite_is_exhausted(invite: InviteCodeModel) -> bool:
    if invite.revoked_at is not None or invite.status in {"revoked", "expired"}:
        return False
    if invite.status == "exhausted" or invite.exhausted_at is not None:
        return True
    usage_mode = _invite_usage_mode(invite)
    if usage_mode == INVITE_USAGE_SINGLE:
        return bool(invite.is_used and invite.used_by_user_id is not None)
    max_redemptions = _optional_positive_int(getattr(invite, "max_redemptions", None))
    return max_redemptions is not None and int(getattr(invite, "active_redemptions_count", 0) or 0) >= max_redemptions


def _runtime_context_payload(runtime_context: InviteRedemptionRuntimeContext | None) -> dict[str, str]:
    if runtime_context is None:
        return {}
    payload: dict[str, str] = {}
    if runtime_context.client_ip_hash:
        payload["client_ip_hash"] = runtime_context.client_ip_hash
    if runtime_context.device_key_hash:
        payload["device_key_hash"] = runtime_context.device_key_hash
    return payload


def _is_disposable_email_domain(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in {
        "10minutemail.com",
        "20minutemail.com",
        "guerrillamail.com",
        "mailinator.com",
        "sharklasers.com",
        "temp-mail.org",
        "tempmail.com",
        "throwawaymail.com",
        "yopmail.com",
    }


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
