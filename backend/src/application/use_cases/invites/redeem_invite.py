"""Use case for redeeming an invite code."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
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
from src.infrastructure.database.models.growth_code_model import GrowthCodeRedemptionModel
from src.infrastructure.database.models.invite_code_model import InviteCodeModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
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
    ) -> RedeemedInviteResult:
        """Redeem *code* on behalf of *user_id*.

        Raises:
            InviteCodeNotFoundError: code does not exist or is unavailable.
            InviteCodeAlreadyUsedError: code has already been redeemed.
            InviteCodeExpiredError: code has passed its expiry date.
        """
        started_at = perf_counter()
        invite = await self._invite_repo.get_by_code(code)

        if invite is None:
            logger.warning("invite_redeem_not_found", extra={"code": code, "user_id": str(user_id)})
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeNotFoundError(code)

        if invite.owner_user_id == user_id:
            logger.warning(
                "invite_redeem_self_redemption_blocked",
                extra={"code": code, "user_id": str(user_id)},
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
                extra={"code": code, "user_id": str(user_id)},
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
            logger.warning(
                "invite_redeem_expired",
                extra={"code": code, "expires_at": str(expires_at)},
            )
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise InviteCodeExpiredError(code)

        current_snapshot = await self._current_entitlements.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
        )
        if current_snapshot.get("status") not in {None, "none"}:
            observe_growth_code_redemption_duration(
                code_type="invite",
                surface=CUSTOMER_REDEEM_SURFACE,
                result="failure",
                duration_seconds=perf_counter() - started_at,
            )
            raise ValueError("Invite code cannot be redeemed for accounts with active access")

        shadow_code = await self._registry.ensure_shadow_invite(invite)
        service_identity = await self._service_identities.execute(
            customer_account_id=user_id,
            auth_realm_id=UUID(current_realm.realm_id),
            provider_name="remnawave",
            origin_storefront_id=shadow_code.storefront_id,
        )
        expires_at = datetime.now(UTC) + timedelta(days=int(invite.free_days))
        grant = await self._entitlements.execute(
            service_identity_id=service_identity.service_identity.id,
            manual_source_key=f"invite:{invite.id}:redeemer:{user_id}",
            grant_snapshot=_build_invite_entitlement_snapshot(invite.free_days),
            expires_at=expires_at,
        )
        activated = await self._activate_entitlement.execute(
            entitlement_grant_id=grant.entitlement_grant.id,
            activated_by_admin_user_id=None,
        )
        result = await self._invite_repo.mark_used(invite.id, user_id)
        redemption = await self._ensure_redemption(
            shadow_code_id=shadow_code.id,
            redeemer_user_id=user_id,
            entitlement_grant_id=activated.id,
            policy_version_id=shadow_code.policy_version_id,
        )
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
                "entitlement_grant_id": str(activated.id),
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
            entitlement_grant_id=str(activated.id),
            owner_user_id=str(invite.owner_user_id),
            redeemer_user_id=str(user_id),
        )

        logger.info(
            "invite_redeemed",
            extra={
                "code": code,
                "invite_id": str(invite.id),
                "user_id": str(user_id),
                "free_days": invite.free_days,
            },
        )

        redeemed_invite = result if result is not None else invite
        return RedeemedInviteResult(
            invite=redeemed_invite,
            entitlement_grant_id=activated.id,
            entitlement_snapshot=dict(activated.grant_snapshot or {}),
            redemption=redemption,
        )

    async def _build_idempotent_result(
        self,
        *,
        invite: InviteCodeModel,
        user_id: UUID,
        current_realm: RealmResolution,
    ) -> RedeemedInviteResult:
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
            grant_snapshot=_build_invite_entitlement_snapshot(invite.free_days),
            expires_at=(_coerce_utc(invite.used_at) or datetime.now(UTC)) + timedelta(days=int(invite.free_days)),
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
        shadow_code.status = "redeemed"
        shadow_code.uses_count = 1
        await self._session.flush()
        return RedeemedInviteResult(
            invite=invite,
            entitlement_grant_id=activated.id,
            entitlement_snapshot=dict(activated.grant_snapshot or {}),
            redemption=redemption,
        )

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


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
