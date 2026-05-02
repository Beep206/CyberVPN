from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.application.use_cases.growth_codes.registry import GrowthCodeRegistryService
from src.domain.enums import (
    CommercialOwnerType,
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
    InviteSource,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    CUSTOMER_COMMERCE_SURFACE,
    observe_growth_code_resolution_duration,
)

PARTNER_FLOW_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}


@dataclass(frozen=True)
class GrowthCodeResolutionOutcome:
    accepted: bool
    code_type: GrowthCodeType | None
    action_context: GrowthCodeActionContext
    result: GrowthCodeResolutionStatus
    user_message_key: str
    reject_reason: GrowthCodeRejectReason | None = None
    conflict_code: str | None = None
    wrong_context_target: GrowthCodeWrongContextTarget | None = None
    issuer_type: str | None = None
    owner_type: str | None = None
    resolved_code_id: UUID | None = None
    growth_code_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None


class ResolveGrowthCodeUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._invites = InviteCodeRepository(session)
        self._promos = PromoCodeRepository(session)
        self._partners = PartnerRepository(session)
        self._bindings = CustomerCommercialBindingRepository(session)
        self._growth_codes = GrowthCodeRepository(session)
        self._registry = GrowthCodeRegistryService(session)

    async def execute(
        self,
        *,
        code: str,
        action_context: GrowthCodeActionContext,
        user_id: UUID | None,
        plan_id: UUID | None = None,
        amount: Decimal | None = None,
        storefront_id: UUID | None = None,
        existing_partner_code_present: bool = False,
        existing_promo_present: bool = False,
        surface: str | None = None,
    ) -> GrowthCodeResolutionOutcome:
        started_at = perf_counter()
        normalized_code = code.strip()
        if not normalized_code:
            outcome = self._not_found(action_context)
            self._observe_resolution_duration(
                code_type=None,
                action_context=action_context.value,
                surface=surface or CUSTOMER_COMMERCE_SURFACE,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        registry_code = None
        invite = await self._invites.get_by_code(normalized_code)
        if invite is not None:
            registry_code = await self._registry.ensure_shadow_invite(invite)
            outcome = self._resolve_invite(
                invite=invite,
                action_context=action_context,
                user_id=user_id,
            )
            outcome = self._with_growth_code_id(outcome, registry_code.id)
            await self._registry.record_resolution_event(
                growth_code_id=registry_code.id,
                raw_code=normalized_code,
                code_type=GrowthCodeType.INVITE.value,
                user_id=user_id,
                surface=surface or action_context.value,
                action_context=action_context.value,
                result=outcome.result.value,
                reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
                conflict_code=outcome.conflict_code,
                policy_version_id=registry_code.policy_version_id,
            )
            self._observe_resolution_duration(
                code_type=GrowthCodeType.INVITE.value,
                action_context=action_context.value,
                surface=surface or action_context.value,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        promo = await self._promos.get_by_code(normalized_code)
        if promo is not None:
            registry_code = await self._registry.ensure_shadow_promo(promo)
            outcome = await self._resolve_promo(
                promo=promo,
                action_context=action_context,
                user_id=user_id,
                plan_id=plan_id,
                amount=amount,
                storefront_id=storefront_id,
                existing_partner_code_present=existing_partner_code_present,
            )
            outcome = self._with_growth_code_id(outcome, registry_code.id)
            await self._registry.record_resolution_event(
                growth_code_id=registry_code.id,
                raw_code=normalized_code,
                code_type=GrowthCodeType.PROMO.value,
                user_id=user_id,
                surface=surface or action_context.value,
                action_context=action_context.value,
                result=outcome.result.value,
                reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
                conflict_code=outcome.conflict_code,
                policy_version_id=registry_code.policy_version_id,
            )
            self._observe_resolution_duration(
                code_type=GrowthCodeType.PROMO.value,
                action_context=action_context.value,
                surface=surface or action_context.value,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        gift_code = await self._growth_codes.get_code_by_hash(hash_growth_code(normalized_code), code_type="gift")
        if gift_code is not None:
            outcome = await self._resolve_gift(
                growth_code=gift_code,
                action_context=action_context,
                user_id=user_id,
            )
            await self._registry.record_resolution_event(
                growth_code_id=gift_code.id,
                raw_code=normalized_code,
                code_type=GrowthCodeType.GIFT.value,
                user_id=user_id,
                surface=surface or action_context.value,
                action_context=action_context.value,
                result=outcome.result.value,
                reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
                conflict_code=outcome.conflict_code,
                policy_version_id=gift_code.policy_version_id,
            )
            outcome = self._with_growth_code_id(outcome, gift_code.id)
            self._observe_resolution_duration(
                code_type=GrowthCodeType.GIFT.value,
                action_context=action_context.value,
                surface=surface or action_context.value,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        referral_owner = await self._resolve_referral_owner(normalized_code)
        if referral_owner is not None:
            registry_code = await self._registry.ensure_shadow_referral(referral_owner)
            outcome = await self._resolve_referral(
                referral_owner=referral_owner,
                action_context=action_context,
                user_id=user_id,
                storefront_id=storefront_id,
                existing_partner_code_present=existing_partner_code_present,
            )
            outcome = self._with_growth_code_id(outcome, registry_code.id)
            await self._registry.record_resolution_event(
                growth_code_id=registry_code.id,
                raw_code=normalized_code,
                code_type=GrowthCodeType.REFERRAL.value,
                user_id=user_id,
                surface=surface or action_context.value,
                action_context=action_context.value,
                result=outcome.result.value,
                reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
                conflict_code=outcome.conflict_code,
                policy_version_id=registry_code.policy_version_id,
            )
            self._observe_resolution_duration(
                code_type=GrowthCodeType.REFERRAL.value,
                action_context=action_context.value,
                surface=surface or action_context.value,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        partner_code = await self._partners.get_code_by_code(normalized_code)
        if partner_code is not None:
            outcome = self._resolve_partner_code(
                partner_code=partner_code,
                action_context=action_context,
                existing_promo_present=existing_promo_present,
            )
            await self._registry.record_resolution_event(
                growth_code_id=None,
                raw_code=normalized_code,
                code_type=GrowthCodeType.PARTNER.value,
                user_id=user_id,
                surface=surface or action_context.value,
                action_context=action_context.value,
                result=outcome.result.value,
                reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
                conflict_code=outcome.conflict_code,
                policy_version_id=None,
            )
            self._observe_resolution_duration(
                code_type=GrowthCodeType.PARTNER.value,
                action_context=action_context.value,
                surface=surface or action_context.value,
                result=outcome.result.value,
                started_at=started_at,
            )
            return outcome

        outcome = self._not_found(action_context)
        await self._registry.record_resolution_event(
            growth_code_id=None,
            raw_code=normalized_code,
            code_type=None,
            user_id=user_id,
            surface=surface or action_context.value,
            action_context=action_context.value,
            result=outcome.result.value,
            reject_reason=outcome.reject_reason.value if outcome.reject_reason else None,
            conflict_code=outcome.conflict_code,
            policy_version_id=None,
        )
        self._observe_resolution_duration(
            code_type=None,
            action_context=action_context.value,
            surface=surface or action_context.value,
            result=outcome.result.value,
            started_at=started_at,
        )
        return outcome

    @staticmethod
    def _observe_resolution_duration(
        *,
        code_type: str | None,
        action_context: str,
        surface: str,
        result: str,
        started_at: float,
    ) -> None:
        observe_growth_code_resolution_duration(
            code_type=code_type,
            action_context=action_context,
            surface=surface,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )

    def _resolve_invite(
        self,
        *,
        invite,
        action_context: GrowthCodeActionContext,
        user_id: UUID | None,
    ) -> GrowthCodeResolutionOutcome:
        if action_context == GrowthCodeActionContext.CHECKOUT:
            return self._wrong_context(
                code_type=GrowthCodeType.INVITE,
                action_context=action_context,
                issuer_type=self._invite_issuer_type(invite.source),
                owner_type="customer",
                resolved_code_id=invite.id,
                target=GrowthCodeWrongContextTarget.REDEEM,
                message_key="growth_codes.invite.redeem_required",
            )

        if user_id is not None and invite.owner_user_id == user_id:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.INVITE,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.INVITE_SELF_REDEMPTION_BLOCKED,
                user_message_key="growth_codes.invite.self_redemption_blocked",
                issuer_type=self._invite_issuer_type(invite.source),
                owner_type="customer",
                resolved_code_id=invite.id,
            )

        if invite.is_used:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.INVITE,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
                user_message_key="growth_codes.invite.already_redeemed",
                issuer_type=self._invite_issuer_type(invite.source),
                owner_type="customer",
                resolved_code_id=invite.id,
            )

        if invite.expires_at is not None and invite.expires_at <= datetime.now(UTC):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.INVITE,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_EXPIRED,
                user_message_key="growth_codes.invite.expired",
                issuer_type=self._invite_issuer_type(invite.source),
                owner_type="customer",
                resolved_code_id=invite.id,
            )

        return GrowthCodeResolutionOutcome(
            accepted=True,
            code_type=GrowthCodeType.INVITE,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.invite.accepted",
            issuer_type=self._invite_issuer_type(invite.source),
            owner_type="customer",
            resolved_code_id=invite.id,
        )

    async def _resolve_promo(
        self,
        *,
        promo,
        action_context: GrowthCodeActionContext,
        user_id: UUID,
        plan_id: UUID | None,
        amount: Decimal | None,
        storefront_id: UUID | None,
        existing_partner_code_present: bool,
    ) -> GrowthCodeResolutionOutcome:
        if action_context != GrowthCodeActionContext.CHECKOUT:
            return self._wrong_context(
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                target=GrowthCodeWrongContextTarget.CHECKOUT,
                message_key="growth_codes.promo.checkout_required",
            )

        if existing_partner_code_present:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.CONFLICTED,
                reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE,
                conflict_code="partner_code_present",
                user_message_key="growth_codes.promo.partner_code_conflict",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if await self._has_partner_flow(user_id=user_id, storefront_id=storefront_id):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.CONFLICTED,
                reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
                conflict_code="partner_binding_present",
                user_message_key="growth_codes.promo.partner_binding_conflict",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if not promo.is_active:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_ACTIVE,
                user_message_key="growth_codes.promo.inactive",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if promo.expires_at is not None and promo.expires_at <= datetime.now(UTC):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_EXPIRED,
                user_message_key="growth_codes.promo.expired",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_EXHAUSTED,
                user_message_key="growth_codes.promo.exhausted",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if promo.is_single_use and await self._promos.has_user_used(promo.id, user_id):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
                user_message_key="growth_codes.promo.already_used",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if promo.plan_ids is not None and plan_id is not None and plan_id not in promo.plan_ids:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SKU,
                user_message_key="growth_codes.promo.plan_ineligible",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        if promo.min_amount is not None and amount is not None and amount < Decimal(str(promo.min_amount)):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PROMO,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SKU,
                user_message_key="growth_codes.promo.amount_ineligible",
                issuer_type="admin",
                owner_type="admin_campaign",
                resolved_code_id=promo.id,
                promo_code_id=promo.id,
            )

        return GrowthCodeResolutionOutcome(
            accepted=True,
            code_type=GrowthCodeType.PROMO,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.promo.accepted",
            issuer_type="admin",
            owner_type="admin_campaign",
            resolved_code_id=promo.id,
            promo_code_id=promo.id,
        )

    async def _resolve_gift(
        self,
        *,
        growth_code,
        action_context: GrowthCodeActionContext,
        user_id: UUID | None,
    ) -> GrowthCodeResolutionOutcome:
        if action_context == GrowthCodeActionContext.CHECKOUT:
            return self._wrong_context(
                code_type=GrowthCodeType.GIFT,
                action_context=action_context,
                issuer_type=growth_code.issuer_type,
                owner_type="customer",
                resolved_code_id=growth_code.id,
                target=GrowthCodeWrongContextTarget.REDEEM,
                message_key="growth_codes.gift.redeem_required",
            )

        if user_id is None:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.GIFT,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_REQUIRES_AUTH,
                user_message_key="growth_codes.gift.auth_required",
                issuer_type=growth_code.issuer_type,
                owner_type="customer",
                resolved_code_id=growth_code.id,
            )

        if growth_code.status == "redeemed" or int(growth_code.uses_count or 0) >= int(growth_code.max_uses or 1):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.GIFT,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.GIFT_ALREADY_REDEEMED,
                user_message_key="growth_codes.gift.already_redeemed",
                issuer_type=growth_code.issuer_type,
                owner_type="customer",
                resolved_code_id=growth_code.id,
            )

        expires_at = growth_code.expires_at
        if expires_at is not None and expires_at <= datetime.now(UTC):
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.GIFT,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_EXPIRED,
                user_message_key="growth_codes.gift.expired",
                issuer_type=growth_code.issuer_type,
                owner_type="customer",
                resolved_code_id=growth_code.id,
            )

        if growth_code.status != "active":
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.GIFT,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_ACTIVE,
                user_message_key="growth_codes.gift.inactive",
                issuer_type=growth_code.issuer_type,
                owner_type="customer",
                resolved_code_id=growth_code.id,
            )

        return GrowthCodeResolutionOutcome(
            accepted=True,
            code_type=GrowthCodeType.GIFT,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.gift.accepted",
            issuer_type=growth_code.issuer_type,
            owner_type="customer",
            resolved_code_id=growth_code.id,
        )

    async def _resolve_referral(
        self,
        *,
        referral_owner: MobileUserModel,
        action_context: GrowthCodeActionContext,
        user_id: UUID | None,
        storefront_id: UUID | None,
        existing_partner_code_present: bool,
    ) -> GrowthCodeResolutionOutcome:
        if action_context == GrowthCodeActionContext.REDEEM:
            return self._wrong_context(
                code_type=GrowthCodeType.REFERRAL,
                action_context=action_context,
                issuer_type="user",
                owner_type="customer",
                resolved_code_id=referral_owner.id,
                target=GrowthCodeWrongContextTarget.CHECKOUT,
                message_key="growth_codes.referral.checkout_required",
            )

        if user_id is not None and referral_owner.id == user_id:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.REFERRAL,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.BLOCKED_BY_RISK,
                reject_reason=GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK,
                user_message_key="growth_codes.referral.self_referral_blocked",
                issuer_type="user",
                owner_type="customer",
                resolved_code_id=referral_owner.id,
            )

        if action_context == GrowthCodeActionContext.CHECKOUT:
            if existing_partner_code_present:
                return GrowthCodeResolutionOutcome(
                    accepted=False,
                    code_type=GrowthCodeType.REFERRAL,
                    action_context=action_context,
                    result=GrowthCodeResolutionStatus.CONFLICTED,
                    reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE,
                    conflict_code="partner_code_present",
                    user_message_key="growth_codes.referral.partner_code_conflict",
                    issuer_type="user",
                    owner_type="customer",
                    resolved_code_id=referral_owner.id,
                )
            if await self._has_partner_flow(user_id=user_id, storefront_id=storefront_id):
                return GrowthCodeResolutionOutcome(
                    accepted=False,
                    code_type=GrowthCodeType.REFERRAL,
                    action_context=action_context,
                    result=GrowthCodeResolutionStatus.CONFLICTED,
                    reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
                    conflict_code="partner_binding_present",
                    user_message_key="growth_codes.referral.partner_binding_conflict",
                    issuer_type="user",
                    owner_type="customer",
                    resolved_code_id=referral_owner.id,
                )

        return GrowthCodeResolutionOutcome(
            accepted=True,
            code_type=GrowthCodeType.REFERRAL,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.referral.accepted",
            issuer_type="user",
            owner_type="customer",
            resolved_code_id=referral_owner.id,
        )

    def _resolve_partner_code(
        self,
        *,
        partner_code,
        action_context: GrowthCodeActionContext,
        existing_promo_present: bool,
    ) -> GrowthCodeResolutionOutcome:
        owner_type = "reseller" if partner_code.partner_account_id is not None else "affiliate"
        if action_context != GrowthCodeActionContext.CHECKOUT:
            return self._wrong_context(
                code_type=GrowthCodeType.PARTNER,
                action_context=action_context,
                issuer_type="partner",
                owner_type=owner_type,
                resolved_code_id=partner_code.id,
                target=GrowthCodeWrongContextTarget.CHECKOUT,
                message_key="growth_codes.partner.checkout_required",
            )

        if existing_promo_present:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PARTNER,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.CONFLICTED,
                reject_reason=GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PROMO,
                conflict_code="promo_present",
                user_message_key="growth_codes.partner.promo_conflict",
                issuer_type="partner",
                owner_type=owner_type,
                resolved_code_id=partner_code.id,
                partner_code_id=partner_code.id,
            )

        if not partner_code.is_active:
            return GrowthCodeResolutionOutcome(
                accepted=False,
                code_type=GrowthCodeType.PARTNER,
                action_context=action_context,
                result=GrowthCodeResolutionStatus.REJECTED,
                reject_reason=GrowthCodeRejectReason.CODE_NOT_ACTIVE,
                user_message_key="growth_codes.partner.inactive",
                issuer_type="partner",
                owner_type=owner_type,
                resolved_code_id=partner_code.id,
                partner_code_id=partner_code.id,
            )

        return GrowthCodeResolutionOutcome(
            accepted=True,
            code_type=GrowthCodeType.PARTNER,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.partner.accepted",
            issuer_type="partner",
            owner_type=owner_type,
            resolved_code_id=partner_code.id,
            partner_code_id=partner_code.id,
        )

    @staticmethod
    def _with_growth_code_id(
        outcome: GrowthCodeResolutionOutcome,
        growth_code_id: UUID,
    ) -> GrowthCodeResolutionOutcome:
        return GrowthCodeResolutionOutcome(
            accepted=outcome.accepted,
            code_type=outcome.code_type,
            action_context=outcome.action_context,
            result=outcome.result,
            user_message_key=outcome.user_message_key,
            reject_reason=outcome.reject_reason,
            conflict_code=outcome.conflict_code,
            wrong_context_target=outcome.wrong_context_target,
            issuer_type=outcome.issuer_type,
            owner_type=outcome.owner_type,
            resolved_code_id=outcome.resolved_code_id,
            growth_code_id=growth_code_id,
            promo_code_id=outcome.promo_code_id,
            partner_code_id=outcome.partner_code_id,
        )

    async def _resolve_referral_owner(self, referral_code: str) -> MobileUserModel | None:
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.referral_code == referral_code).limit(1)
        )
        return result.scalar_one_or_none()

    async def _has_partner_flow(self, *, user_id: UUID | None, storefront_id: UUID | None) -> bool:
        if user_id is None:
            return False
        user = await self._session.get(MobileUserModel, user_id)
        if user is not None and (user.partner_user_id is not None or user.partner_account_id is not None):
            return True

        bindings = await self._bindings.list_active_for_user(user_id=user_id, storefront_id=storefront_id)
        return any(binding.owner_type in PARTNER_FLOW_OWNER_TYPES for binding in bindings)

    @staticmethod
    def _not_found(action_context: GrowthCodeActionContext) -> GrowthCodeResolutionOutcome:
        return GrowthCodeResolutionOutcome(
            accepted=False,
            code_type=None,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.REJECTED,
            reject_reason=GrowthCodeRejectReason.CODE_NOT_FOUND,
            user_message_key="growth_codes.code.not_found",
        )

    @staticmethod
    def _wrong_context(
        *,
        code_type: GrowthCodeType,
        action_context: GrowthCodeActionContext,
        issuer_type: str,
        owner_type: str,
        resolved_code_id: UUID,
        target: GrowthCodeWrongContextTarget,
        message_key: str,
    ) -> GrowthCodeResolutionOutcome:
        return GrowthCodeResolutionOutcome(
            accepted=False,
            code_type=code_type,
            action_context=action_context,
            result=GrowthCodeResolutionStatus.REJECTED,
            reject_reason=GrowthCodeRejectReason.CODE_WRONG_CONTEXT,
            wrong_context_target=target,
            user_message_key=message_key,
            issuer_type=issuer_type,
            owner_type=owner_type,
            resolved_code_id=resolved_code_id,
        )

    @staticmethod
    def _invite_issuer_type(source: str) -> str:
        return "purchase" if source == InviteSource.PURCHASE.value else "admin"
