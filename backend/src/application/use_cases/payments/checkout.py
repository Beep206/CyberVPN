"""Unified checkout quote calculation for plans, add-ons, promo, and wallet."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.services.entitlements_service import EntitlementsService
from src.application.services.stage1_growth_policy import assert_stage1_checkout_codes_enabled
from src.application.services.stage1_plan_policy import (
    assert_stage1_addons_enabled,
    assert_stage1_paid_plan_purchasable,
)
from src.application.services.wallet_service import WalletService
from src.application.use_cases.growth_code_sets.exceptions import CodeSetRejectedError
from src.application.use_cases.growth_code_sets.fx import (
    FxConversionError,
    FxRateSnapshot,
    conversion_mode_from_payload,
    convert_fixed_discount,
    rate_snapshots_from_policy_snapshot,
)
from src.application.use_cases.growth_codes import (
    GrowthCodeResolutionOutcome,
    ResolveGrowthCodeUseCase,
)
from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.application.use_cases.growth_risk.runtime_guard import evaluate_growth_runtime_risk
from src.application.use_cases.partner_attribution.eligibility import (
    EvaluatePartnerCodeEligibilityCommand,
    EvaluatePartnerCodeEligibilityWithContextUseCase,
    PartnerCodeEligibilityResult,
)
from src.application.use_cases.settlement.commission_terms import (
    build_commission_contract_model,
    build_commission_contract_snapshot,
    build_commission_contract_snapshot_for_code,
)
from src.config.settings import settings
from src.domain.enums import (
    CommercialOwnerType,
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
)
from src.infrastructure.database.models.customer_commercial_binding_model import CustomerCommercialBindingModel
from src.infrastructure.database.models.growth_risk_fx_model import FxProviderConfigModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.private_catalog_repo import SqlAlchemyPrivateCatalogRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import observe_growth_fx_conversion_failure

logger = logging.getLogger(__name__)

PARTNER_MARKUP_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}


@dataclass(frozen=True)
class CheckoutAddonInput:
    """Single add-on selection from checkout payload."""

    code: str
    qty: int
    location_code: str | None = None


@dataclass(frozen=True)
class CheckoutCodeBasketInput:
    """Single customer-entered code in a multi-code checkout basket."""

    code: str
    client_slot_id: str | None = None


@dataclass(frozen=True)
class CheckoutAddonLine:
    """Priced add-on line resolved against the add-on catalog."""

    addon_id: UUID
    code: str
    display_name: str
    qty: int
    unit_price: Decimal
    total_price: Decimal
    location_code: str | None
    delta_entitlements: dict


@dataclass(frozen=True)
class CheckoutAppliedDiscount:
    discount_type: str
    code: str
    amount: Decimal
    policy_version_id: UUID | None = None


@dataclass(frozen=True)
class _BasketDiscountCandidate:
    code: str
    code_hash: str
    discount_type: str
    discount_kind: str
    source_amount: Decimal
    strategy: str
    source_currency: str | None = None
    rate_snapshots: list[FxRateSnapshot] = field(default_factory=list)
    policy_version_id: UUID | None = None
    applied_amount: Decimal = Decimal("0")
    fx_conversion: dict | None = None


@dataclass(frozen=True)
class _BasketEvaluation:
    applications: list[dict]
    discount_amount: Decimal
    discounts: list[CheckoutAppliedDiscount]
    promo_code_id: UUID | None
    primary_resolution: GrowthCodeResolutionOutcome | None


@dataclass
class CheckoutResult:
    """Quote result used by both quote and commit endpoints."""

    base_price: Decimal
    addon_amount: Decimal
    displayed_price: Decimal
    discount_amount: Decimal
    wallet_amount: Decimal
    gateway_amount: Decimal
    partner_markup: Decimal
    is_zero_gateway: bool
    plan_id: UUID | None = None
    promo_code_id: UUID | None = None
    partner_code_id: UUID | None = None
    plan_name: str | None = None
    duration_days: int | None = None
    currency_code: str = "USD"
    addons: list[CheckoutAddonLine] = field(default_factory=list)
    entitlements_snapshot: dict = field(default_factory=dict)
    commission_base_amount: Decimal = Decimal("0")
    discounts: list[CheckoutAppliedDiscount] = field(default_factory=list)
    code_input: str | None = None
    code_resolution: GrowthCodeResolutionOutcome | None = None
    reservation_id: UUID | None = None
    partner_commission_contract_snapshot: dict | None = None
    private_catalog_grant_id: UUID | None = None
    private_catalog_snapshot: dict | None = None
    code_set_applications: list[dict] = field(default_factory=list)
    code_set_acceptance_mode: str | None = None
    code_set_id: UUID | None = None
    code_set_hash: str | None = None
    reservation_group_id: UUID | None = None
    code_set_snapshot: dict | None = None
    growth_checkout_snapshot: dict | None = None


class CheckoutUseCase:
    """Calculate checkout price and entitlement snapshot without persisting payment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plan_repo = SubscriptionPlanRepository(session)
        self._promo_repo = PromoCodeRepository(session)
        self._partner_repo = PartnerRepository(session)
        self._bindings = CustomerCommercialBindingRepository(session)
        self._growth_code_repo = GrowthCodeRepository(session)
        self._addon_repo = PlanAddonRepository(session)
        self._private_catalog_repo = SqlAlchemyPrivateCatalogRepository(session)
        self._config = ConfigService(SystemConfigRepository(session))
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)
        self._growth_codes = ResolveGrowthCodeUseCase(session)
        self._partner_eligibility = EvaluatePartnerCodeEligibilityWithContextUseCase(session)

    async def execute(
        self,
        user_id: UUID,
        plan_id: UUID,
        *,
        currency: str = "USD",
        catalog_base_price: Decimal | None = None,
        base_price_override: Decimal | None = None,
        code_input: str | None = None,
        promo_code: str | None = None,
        partner_code: str | None = None,
        use_wallet: Decimal = Decimal("0"),
        addons: list[CheckoutAddonInput] | None = None,
        code_basket: list[CheckoutCodeBasketInput] | None = None,
        sale_channel: str = "web",
        storefront_id: UUID | None = None,
        private_catalog_grant_id: UUID | None = None,
        private_catalog_quote_session_id: UUID | None = None,
        private_catalog_anonymous_session_id: str | None = None,
    ) -> CheckoutResult:
        plan, private_catalog_snapshot = await self._resolve_plan(
            plan_id,
            sale_channel=sale_channel,
            user_id=user_id,
            storefront_id=storefront_id,
            private_catalog_grant_id=private_catalog_grant_id,
            private_catalog_quote_session_id=private_catalog_quote_session_id,
            private_catalog_anonymous_session_id=private_catalog_anonymous_session_id,
        )
        normalized_currency = _normalize_currency(currency)
        addon_lines = await self._resolve_addons(
            plan=plan,
            addon_inputs=addons or [],
            sale_channel=sale_channel,
            currency=normalized_currency,
        )

        base_price = (
            catalog_base_price
            if catalog_base_price is not None
            else base_price_override
            if base_price_override is not None
            else _resolve_plan_price(plan, normalized_currency)
        )
        if base_price < 0:
            raise ValueError("Catalog base price cannot be negative")
        addon_amount = sum((line.total_price for line in addon_lines), Decimal("0"))

        partner_markup = Decimal("0")
        partner_code_id = None
        partner_commission_contract_snapshot: dict | None = None
        code_resolution: GrowthCodeResolutionOutcome | None = None
        normalized_growth_code_input = _normalize_code_input(code_input=code_input, promo_code=promo_code)
        normalized_code_basket = _normalize_code_basket(code_basket or [])
        if normalized_code_basket and (normalized_growth_code_input or partner_code):
            raise ValueError("codes cannot be combined with code_input, promo_code, or partner_code")

        user = await self._session.get(MobileUserModel, user_id)
        normalized_partner_code = partner_code.strip() if partner_code else None
        if normalized_partner_code:
            if not settings.partner_codes_enabled:
                raise ValueError("Partner codes are not enabled for this release")
            explicit_code = await self._partner_repo.get_code_by_code(normalized_partner_code)
            if explicit_code is None:
                raise ValueError("Partner code not found or inactive")
            account = (
                await self._partner_repo.get_account_by_id(explicit_code.partner_account_id)
                if explicit_code.partner_account_id is not None
                else None
            )
            explicit_commission_snapshot = await self._ensure_commission_contract_snapshot(
                explicit_code,
                source="checkout_quote_pricing",
                currency_code=normalized_currency,
            )
            eligibility = await self._partner_eligibility.execute(
                EvaluatePartnerCodeEligibilityCommand(
                    code_model=explicit_code,
                    account=account,
                    sale_channel=sale_channel,
                    storefront_id=storefront_id,
                    commission_contract_snapshot=explicit_commission_snapshot,
                )
            )
            _assert_checkout_partner_eligibility(eligibility)
            if await self._is_self_partner_code(user=user, partner_code=explicit_code):
                raise ValueError("Partner code self-referral is blocked")
            partner_markup = base_price * (Decimal(str(explicit_code.markup_pct)) / Decimal("100"))
            partner_code_id = explicit_code.id
            partner_commission_contract_snapshot = explicit_commission_snapshot
        elif settings.partner_attribution_enabled:
            active_code = await self._resolve_bound_partner_code(
                user=user,
                storefront_id=storefront_id,
                sale_channel=sale_channel,
                currency_code=normalized_currency,
            )
            if active_code is not None:
                partner_commission_contract_snapshot = await self._ensure_commission_contract_snapshot(
                    active_code,
                    source="checkout_bound_partner_code",
                    currency_code=normalized_currency,
                )
                partner_markup = base_price * (Decimal(str(active_code.markup_pct)) / Decimal("100"))
                partner_code_id = active_code.id

        displayed_price = base_price + addon_amount + partner_markup

        discount_amount = Decimal("0")
        promo_code_id = None
        discounts: list[CheckoutAppliedDiscount] = []
        code_set_applications: list[dict] = []
        assert_stage1_checkout_codes_enabled(
            code_input=normalized_growth_code_input
            or (normalized_code_basket[0][1] if normalized_code_basket else None),
            promo_code=None,
            enabled=settings.checkout_code_discounts_enabled,
        )
        if normalized_code_basket:
            basket_evaluation = await self._evaluate_code_basket(
                normalized_codes=normalized_code_basket,
                user_id=user_id,
                plan=plan,
                displayed_price=displayed_price,
                base_price=base_price,
                existing_partner_code_present=partner_code_id is not None,
                storefront_id=storefront_id,
                sale_channel=sale_channel,
                currency=normalized_currency,
            )
            discount_amount = basket_evaluation.discount_amount
            discounts = basket_evaluation.discounts
            promo_code_id = basket_evaluation.promo_code_id
            code_resolution = basket_evaluation.primary_resolution
            code_set_applications = basket_evaluation.applications
        elif normalized_growth_code_input:
            code_resolution = await self._growth_codes.execute(
                code=normalized_growth_code_input,
                action_context=GrowthCodeActionContext.CHECKOUT,
                user_id=user_id,
                plan_id=plan.id,
                amount=displayed_price,
                storefront_id=storefront_id,
                existing_partner_code_present=partner_code_id is not None,
                surface=sale_channel,
            )
            if not code_resolution.accepted:
                raise ValueError(_quote_resolution_error_message(code_resolution))

            if code_resolution.code_type == GrowthCodeType.PARTNER:
                if partner_code_id is not None:
                    raise ValueError("Partner code is already applied")
                if code_resolution.partner_code_id is None:
                    raise ValueError("Partner code is not valid")
                resolved_partner_code = await self._partner_repo.get_code_by_id(code_resolution.partner_code_id)
                if resolved_partner_code is None or not resolved_partner_code.is_active:
                    raise ValueError("Partner code not found or inactive")
                partner_commission_contract_snapshot = await self._ensure_commission_contract_snapshot(
                    resolved_partner_code,
                    source="checkout_growth_partner_code",
                    currency_code=normalized_currency,
                )
                partner_markup = base_price * (Decimal(str(resolved_partner_code.markup_pct)) / Decimal("100"))
                partner_code_id = resolved_partner_code.id
                displayed_price = base_price + addon_amount + partner_markup
            elif code_resolution.code_type == GrowthCodeType.PROMO:
                promo = await self._promo_repo.get_active_by_code(normalized_growth_code_input)
                if promo is None:
                    raise ValueError("Promo code is not valid")
                promo_code_id = promo.id
                if promo.discount_type == "percent":
                    discount_amount = displayed_price * (Decimal(str(promo.discount_value)) / Decimal("100"))
                else:
                    discount_amount = min(Decimal(str(promo.discount_value)), displayed_price)
                discounts.append(
                    CheckoutAppliedDiscount(
                        discount_type=GrowthCodeType.PROMO.value,
                        code=normalized_growth_code_input,
                        amount=discount_amount,
                    )
                )
            elif code_resolution.code_type == GrowthCodeType.REFERRAL:
                if code_resolution.growth_code_id is None:
                    raise ValueError("Referral code is not valid")
                referral_policy = await self._growth_code_repo.get_referral_policy(code_resolution.growth_code_id)
                if referral_policy is None:
                    raise ValueError("Referral code is not configured")
                if referral_policy.eligible_durations and plan.duration_days not in referral_policy.eligible_durations:
                    raise ValueError("Referral code is not eligible for this plan")
                if (
                    referral_policy.eligible_plan_families
                    and plan.plan_code not in referral_policy.eligible_plan_families
                ):
                    raise ValueError("Referral code is not eligible for this plan")

                referral_base = base_price
                if referral_policy.friend_discount_type == "percent":
                    discount_amount = referral_base * (
                        Decimal(str(referral_policy.friend_discount_value)) / Decimal("100")
                    )
                else:
                    discount_amount = min(Decimal(str(referral_policy.friend_discount_value)), referral_base)
                discounts.append(
                    CheckoutAppliedDiscount(
                        discount_type=GrowthCodeType.REFERRAL.value,
                        code=normalized_growth_code_input,
                        amount=discount_amount,
                    )
                )

        after_promo = displayed_price - discount_amount

        wallet_amount = Decimal("0")
        if use_wallet > 0:
            wallet = await self._wallet.get_balance(user_id)
            available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
            wallet_amount = min(use_wallet, available, after_promo)

        gateway_amount = after_promo - wallet_amount
        is_zero_gateway = gateway_amount <= 0
        if gateway_amount < 0:
            gateway_amount = Decimal("0")

        if normalized_code_basket or normalized_growth_code_input or private_catalog_snapshot or is_zero_gateway:
            risk_result = await evaluate_growth_runtime_risk(
                session=self._session,
                action_context="checkout_eval",
                user_id=user_id,
                auth_realm_id=getattr(user, "auth_realm_id", None),
                storefront_id=storefront_id,
                high_risk_context=bool(private_catalog_snapshot) or is_zero_gateway,
                features={
                    "checkpoint": "checkout_eval",
                    "channel": sale_channel,
                    "currency": normalized_currency,
                    "private_catalog": bool(private_catalog_snapshot),
                    "zero_gateway": is_zero_gateway,
                    "stacking_count": len(normalized_code_basket) or (1 if normalized_growth_code_input else 0),
                    "discount_amount": str(discount_amount),
                    "displayed_price": str(displayed_price),
                    "gateway_amount": str(gateway_amount),
                    "plan_id": str(plan.id),
                },
                private_grant_id=private_catalog_grant_id,
                growth_code_id=code_resolution.growth_code_id if code_resolution is not None else None,
                enforce=True,
            )
            if risk_result.decision.decision_id is not None:
                for application in code_set_applications:
                    application.setdefault("risk_decision_id", str(risk_result.decision.decision_id))
                    application.setdefault("risk_subject_id", str(risk_result.decision.risk_subject_id))

        entitlements_snapshot = EntitlementsService.build_snapshot(
            plan=plan,
            addon_lines=[
                {
                    "code": line.code,
                    "qty": line.qty,
                    "location_code": line.location_code,
                    "delta_entitlements": line.delta_entitlements,
                }
                for line in addon_lines
            ],
        )

        logger.info(
            "checkout_calculated",
            extra={
                "user_id": str(user_id),
                "plan_id": str(plan.id),
                "plan_code": plan.plan_code,
                "channel": sale_channel,
                "addons": [line.code for line in addon_lines],
                "base": str(base_price),
                "addon_amount": str(addon_amount),
                "markup": str(partner_markup),
                "discount": str(discount_amount),
                "wallet": str(wallet_amount),
                "gateway": str(gateway_amount),
                "zero_gateway": is_zero_gateway,
            },
        )

        return CheckoutResult(
            base_price=base_price,
            addon_amount=addon_amount,
            displayed_price=displayed_price,
            discount_amount=discount_amount,
            wallet_amount=wallet_amount,
            gateway_amount=gateway_amount,
            partner_markup=partner_markup,
            is_zero_gateway=is_zero_gateway,
            plan_id=plan.id,
            promo_code_id=promo_code_id,
            partner_code_id=partner_code_id,
            plan_name=plan.name,
            duration_days=plan.duration_days,
            currency_code=normalized_currency,
            addons=addon_lines,
            entitlements_snapshot=entitlements_snapshot,
            commission_base_amount=base_price,
            discounts=discounts,
            code_input=normalized_growth_code_input,
            code_resolution=code_resolution,
            partner_commission_contract_snapshot=partner_commission_contract_snapshot,
            private_catalog_grant_id=private_catalog_grant_id if private_catalog_snapshot is not None else None,
            private_catalog_snapshot=private_catalog_snapshot,
            code_set_applications=code_set_applications,
            code_set_acceptance_mode="all_or_nothing" if code_set_applications else None,
        )

    async def _evaluate_code_basket(
        self,
        *,
        normalized_codes: list[tuple[int, str, str | None]],
        user_id: UUID,
        plan: SubscriptionPlanModel,
        displayed_price: Decimal,
        base_price: Decimal,
        existing_partner_code_present: bool,
        storefront_id: UUID | None,
        sale_channel: str,
        currency: str,
    ) -> "_BasketEvaluation":
        applications: list[dict] = []
        discount_candidates: list[_BasketDiscountCandidate] = []
        seen_hashes: set[str] = set()
        primary_resolution: GrowthCodeResolutionOutcome | None = None
        accepted_promo_code_id: UUID | None = None

        for position_entered, normalized_code, client_slot_id in normalized_codes:
            code_ref = _safe_basket_code_ref(normalized_code)
            if code_ref["code_hash"] in seen_hashes:
                applications.append(
                    _basket_reject_application(
                        position_entered=position_entered,
                        code_ref=code_ref,
                        client_slot_id=client_slot_id,
                        status="rejected",
                        reject_reason="duplicate_code",
                        user_message_key="growth_codes.code.duplicate",
                    )
                )
                continue
            seen_hashes.add(code_ref["code_hash"])

            resolution = await self._growth_codes.execute(
                code=normalized_code,
                action_context=GrowthCodeActionContext.CHECKOUT,
                user_id=user_id,
                plan_id=plan.id,
                amount=displayed_price,
                storefront_id=storefront_id,
                existing_partner_code_present=existing_partner_code_present,
                existing_promo_present=bool(discount_candidates),
                surface=sale_channel,
            )
            application = _basket_application_from_resolution(
                position_entered=position_entered,
                code=normalized_code,
                code_ref=code_ref,
                client_slot_id=client_slot_id,
                resolution=resolution,
                currency=currency,
            )

            if not resolution.accepted:
                applications.append(application)
                continue
            if resolution.code_type == GrowthCodeType.PARTNER:
                application["status"] = "rejected"
                application["reject_reason"] = GrowthCodeRejectReason.CODE_WRONG_CONTEXT.value
                application["user_message_key"] = "growth_codes.partner.use_partner_code_field"
                applications.append(application)
                continue
            if resolution.code_type not in {GrowthCodeType.PROMO, GrowthCodeType.REFERRAL}:
                application["status"] = "rejected"
                application["reject_reason"] = GrowthCodeRejectReason.CODE_WRONG_CONTEXT.value
                applications.append(application)
                continue

            discount_candidate = await self._discount_candidate_for_resolution(
                normalized_code=normalized_code,
                resolution=resolution,
                plan=plan,
                displayed_price=displayed_price,
                base_price=base_price,
            )
            application["discount"] = {
                "source_amount": str(discount_candidate.source_amount.quantize(Decimal("0.01"))),
                "source_currency": discount_candidate.source_currency or currency,
                "target_amount": str(discount_candidate.source_amount.quantize(Decimal("0.01"))),
                "target_currency": currency,
                "applied_amount": "0.00",
                "strategy": discount_candidate.strategy,
            }
            applications.append(application)
            discount_candidates.append(discount_candidate)
            if primary_resolution is None:
                primary_resolution = resolution
            if accepted_promo_code_id is None and resolution.promo_code_id is not None:
                accepted_promo_code_id = resolution.promo_code_id

        rejected = [item for item in applications if item.get("status") != "accepted"]
        if rejected:
            raise CodeSetRejectedError(applications=applications)

        discount_amount, selected = _select_basket_discounts(
            candidates=discount_candidates,
            displayed_price=displayed_price,
            currency=currency,
        )
        discounts: list[CheckoutAppliedDiscount] = []
        selected_by_hash = {item.code_hash: item for item in selected}
        for application in applications:
            code_hash = str((application.get("code_ref") or {}).get("code_hash") or "")
            selected_candidate = selected_by_hash.get(code_hash)
            if selected_candidate is None:
                continue
            discount = dict(application.get("discount") or {})
            discount["applied_amount"] = str(selected_candidate.applied_amount.quantize(Decimal("0.01")))
            if selected_candidate.fx_conversion is not None:
                discount["fx_conversion"] = selected_candidate.fx_conversion
                discount["fx_conversion_id"] = None
            application["discount"] = discount
            discounts.append(
                CheckoutAppliedDiscount(
                    discount_type=selected_candidate.discount_type,
                    code=selected_candidate.code,
                    amount=selected_candidate.applied_amount,
                    policy_version_id=selected_candidate.policy_version_id,
                )
            )

        applications.sort(key=lambda item: (int(item.get("canonical_order") or 0), str(item.get("growth_code_id"))))
        return _BasketEvaluation(
            applications=applications,
            discount_amount=discount_amount,
            discounts=discounts,
            promo_code_id=accepted_promo_code_id,
            primary_resolution=primary_resolution,
        )

    async def _discount_candidate_for_resolution(
        self,
        *,
        normalized_code: str,
        resolution: GrowthCodeResolutionOutcome,
        plan: SubscriptionPlanModel,
        displayed_price: Decimal,
        base_price: Decimal,
    ) -> "_BasketDiscountCandidate":
        policy_version_id = _policy_version_id_from_snapshot(resolution.policy_snapshot)
        if resolution.code_type == GrowthCodeType.PROMO:
            promo = await self._promo_repo.get_active_by_code(normalized_code)
            if promo is None:
                raise ValueError("Promo code is not valid")
            if promo.discount_type == "percent":
                amount = displayed_price * (Decimal(str(promo.discount_value)) / Decimal("100"))
                strategy = "primary_percent"
            else:
                amount = Decimal(str(promo.discount_value))
                strategy = "fixed_after_percent"
            promo_policy = (
                await self._growth_code_repo.get_promo_policy(resolution.growth_code_id)
                if resolution.growth_code_id is not None
                else None
            )
            policy_snapshot = _merge_policy_snapshots(
                resolution.policy_snapshot,
                promo_policy.policy_snapshot if promo_policy is not None else None,
            )
            policy_version_id = _policy_version_id_from_snapshot(policy_snapshot) or policy_version_id
            rate_snapshots = await self._enabled_rate_snapshots(rate_snapshots_from_policy_snapshot(policy_snapshot))
            return _BasketDiscountCandidate(
                code=normalized_code,
                code_hash=hash_growth_code(normalized_code),
                discount_type=GrowthCodeType.PROMO.value,
                discount_kind=promo.discount_type,
                source_amount=max(amount, Decimal("0")),
                strategy=strategy,
                source_currency=_fixed_discount_source_currency(
                    policy_snapshot=policy_snapshot,
                    quote_currency=None,
                ),
                rate_snapshots=rate_snapshots,
                policy_version_id=policy_version_id,
            )
        if resolution.code_type == GrowthCodeType.REFERRAL and resolution.growth_code_id is not None:
            referral_policy = await self._growth_code_repo.get_referral_policy(resolution.growth_code_id)
            if referral_policy is None:
                raise ValueError("Referral code is not configured")
            if referral_policy.eligible_durations and plan.duration_days not in referral_policy.eligible_durations:
                raise ValueError("Referral code is not eligible for this plan")
            if referral_policy.eligible_plan_families and plan.plan_code not in referral_policy.eligible_plan_families:
                raise ValueError("Referral code is not eligible for this plan")
            if referral_policy.friend_discount_type == "percent":
                amount = base_price * (Decimal(str(referral_policy.friend_discount_value or 0)) / Decimal("100"))
                strategy = "primary_percent"
                kind = "percent"
            else:
                amount = Decimal(str(referral_policy.friend_discount_value or 0))
                strategy = "fixed_after_percent"
                kind = "fixed"
            policy_snapshot = _merge_policy_snapshots(resolution.policy_snapshot, referral_policy.policy_snapshot)
            policy_version_id = _policy_version_id_from_snapshot(policy_snapshot) or policy_version_id
            rate_snapshots = await self._enabled_rate_snapshots(rate_snapshots_from_policy_snapshot(policy_snapshot))
            return _BasketDiscountCandidate(
                code=normalized_code,
                code_hash=hash_growth_code(normalized_code),
                discount_type=GrowthCodeType.REFERRAL.value,
                discount_kind=kind,
                source_amount=max(amount, Decimal("0")),
                strategy=strategy,
                source_currency=_fixed_discount_source_currency(
                    policy_snapshot=policy_snapshot,
                    quote_currency=None,
                ),
                rate_snapshots=rate_snapshots,
                policy_version_id=policy_version_id,
            )
        raise ValueError("Growth code is not valid")

    async def _enabled_rate_snapshots(self, rates: list[FxRateSnapshot]) -> list[FxRateSnapshot]:
        provider_keys = sorted({rate.provider for rate in rates if rate.source_type == "provider"})
        if not provider_keys:
            return rates

        rows = await self._session.execute(
            select(FxProviderConfigModel.provider_key).where(
                FxProviderConfigModel.provider_key.in_(provider_keys),
                FxProviderConfigModel.enabled.is_(True),
            )
        )
        enabled_provider_keys = set(rows.scalars().all())
        return [rate for rate in rates if rate.source_type != "provider" or rate.provider in enabled_provider_keys]

    async def _ensure_commission_contract_snapshot(
        self,
        code: PartnerCodeModel,
        *,
        source: str,
        currency_code: str,
    ) -> dict:
        get_contract = getattr(self._partner_repo, "get_commission_contract_by_id", None)
        contract = None
        existing_contract_id = getattr(code, "commission_contract_id", None)
        if existing_contract_id is not None and callable(get_contract):
            contract = await get_contract(existing_contract_id)
        if contract is None:
            attach_contract = getattr(self._partner_repo, "attach_commission_contract_to_code", None)
            if not callable(attach_contract) or not hasattr(code, "version"):
                payout_hold_days = 45 if code.owner_type == CommercialOwnerType.PERFORMANCE.value else 30
                return build_commission_contract_snapshot_for_code(
                    code_model=code,
                    commission_pct=Decimal("20"),
                    payout_hold_days=payout_hold_days,
                    snapshot_source=source,
                    currency_code=currency_code,
                )
            commission_pct, payout_hold_days = await self._partner_commission_defaults(code.owner_type)
            contract = build_commission_contract_model(
                code_model=code,
                commission_pct=commission_pct,
                payout_hold_days=payout_hold_days,
                source=source,
            )
            await attach_contract(code, contract)
        return build_commission_contract_snapshot(contract, snapshot_source=source, currency_code=currency_code)

    async def _partner_commission_defaults(self, owner_type: str | None) -> tuple[Decimal, int]:
        try:
            tiers = await self._config.get_partner_tiers()
        except (AttributeError, StopAsyncIteration, TypeError):
            tiers = [{"min_clients": 0, "commission_pct": 20}]
        try:
            payout_hold_days = await self._config.get_partner_payout_hold_days(owner_type=owner_type)
        except (AttributeError, StopAsyncIteration, TypeError):
            payout_hold_days = 45 if owner_type == CommercialOwnerType.PERFORMANCE.value else 30
        return _resolve_base_commission_pct(tiers), payout_hold_days

    async def _resolve_bound_partner_code(
        self,
        *,
        user: MobileUserModel | None,
        storefront_id: UUID | None,
        sale_channel: str | None,
        currency_code: str,
    ) -> PartnerCodeModel | None:
        if user is None:
            return None

        bindings = cast(
            list[CustomerCommercialBindingModel],
            await self._bindings.list_active_for_user(user_id=user.id, storefront_id=storefront_id),
        )
        for binding in bindings:
            if binding.partner_code_id is None or binding.owner_type not in PARTNER_MARKUP_OWNER_TYPES:
                continue
            code = await self._partner_repo.get_code_by_id(binding.partner_code_id)
            if code is not None and await self._is_checkout_partner_code_allowed(
                code,
                sale_channel=sale_channel,
                storefront_id=storefront_id,
                currency_code=currency_code,
            ):
                return code

        if user.partner_user_id is None:
            return None

        codes = await self._partner_repo.get_codes_by_partner(user.partner_user_id)
        for code in codes:
            if await self._is_checkout_partner_code_allowed(
                code,
                sale_channel=sale_channel,
                storefront_id=storefront_id,
                currency_code=currency_code,
            ):
                return code
        return None

    async def _is_checkout_partner_code_allowed(
        self,
        code: PartnerCodeModel,
        *,
        sale_channel: str | None,
        storefront_id: UUID | None,
        currency_code: str,
    ) -> bool:
        account = (
            await self._partner_repo.get_account_by_id(code.partner_account_id)
            if code.partner_account_id is not None
            else None
        )
        commission_snapshot = await self._ensure_commission_contract_snapshot(
            code,
            source="checkout_bound_partner_code_eligibility",
            currency_code=currency_code,
        )
        eligibility = await self._partner_eligibility.execute(
            EvaluatePartnerCodeEligibilityCommand(
                code_model=code,
                account=account,
                sale_channel=sale_channel,
                storefront_id=storefront_id,
                commission_contract_snapshot=commission_snapshot,
            )
        )
        return eligibility.allowed

    async def _is_self_partner_code(
        self,
        *,
        user: MobileUserModel | None,
        partner_code: PartnerCodeModel,
    ) -> bool:
        if user is None:
            return False
        if getattr(partner_code, "partner_user_id", None) == user.id:
            return True
        partner_account_id = getattr(partner_code, "partner_account_id", None)
        if partner_account_id is None:
            return False
        if getattr(user, "partner_account_id", None) == partner_account_id:
            return True
        account = await self._session.get(PartnerAccountModel, partner_account_id)
        return account is not None and account.legacy_owner_user_id == user.id

    async def _resolve_plan(
        self,
        plan_id: UUID,
        *,
        sale_channel: str,
        user_id: UUID,
        storefront_id: UUID | None,
        private_catalog_grant_id: UUID | None,
        private_catalog_quote_session_id: UUID | None,
        private_catalog_anonymous_session_id: str | None,
    ) -> tuple[SubscriptionPlanModel, dict | None]:
        plan = await self._plan_repo.get_by_id(plan_id)
        if plan is None:
            msg = f"Plan not found: {plan_id}"
            raise ValueError(msg)
        if not plan.is_active:
            raise ValueError("Plan is inactive")
        catalog_access_class = str(getattr(plan, "catalog_access_class", "") or "admin_only")
        is_private_code_gated = catalog_access_class == "private_code_gated"
        if sale_channel != "admin" and plan.catalog_visibility != "public" and not is_private_code_gated:
            raise ValueError("Plan is not available on this channel")
        if plan.sale_channels and sale_channel not in plan.sale_channels:
            raise ValueError("Plan is not available on this channel")
        if is_private_code_gated and sale_channel != "admin":
            private_catalog_snapshot = await self._validate_private_catalog_grant(
                grant_id=private_catalog_grant_id,
                plan=plan,
                user_id=user_id,
                storefront_id=storefront_id,
                sale_channel=sale_channel,
                quote_session_id=private_catalog_quote_session_id,
                anonymous_session_id=private_catalog_anonymous_session_id,
            )
            return plan, private_catalog_snapshot
        if private_catalog_grant_id is not None and not is_private_code_gated:
            raise ValueError("PRIVATE_CATALOG_GRANT_NOT_APPLICABLE")
        assert_stage1_paid_plan_purchasable(plan, sale_channel=sale_channel)
        return plan, None

    async def _validate_private_catalog_grant(
        self,
        *,
        grant_id: UUID | None,
        plan: SubscriptionPlanModel,
        user_id: UUID,
        storefront_id: UUID | None,
        sale_channel: str,
        quote_session_id: UUID | None,
        anonymous_session_id: str | None,
    ) -> dict:
        if grant_id is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_REQUIRED")
        if storefront_id is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_CONTEXT_REQUIRED")
        grant = await self._private_catalog_repo.get_access_grant_by_id(grant_id)
        if grant is None:
            raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
        now = datetime.now(UTC)
        expires_at = _normalize_utc(grant.expires_at)
        if grant.status != "issued" or grant.revoked_at is not None or expires_at <= now:
            raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
        if grant.user_id is not None and grant.user_id != user_id:
            raise ValueError("PRIVATE_CATALOG_GRANT_SUBJECT_MISMATCH")
        if grant.user_id is None:
            if not grant.anonymous_session_id:
                raise ValueError("PRIVATE_CATALOG_GRANT_INVALID")
            if not anonymous_session_id or grant.anonymous_session_id != anonymous_session_id:
                raise ValueError("PRIVATE_CATALOG_GRANT_SUBJECT_MISMATCH")
        if grant.storefront_id != storefront_id or grant.sale_channel != sale_channel:
            raise ValueError("PRIVATE_CATALOG_GRANT_SCOPE_MISMATCH")
        allowed_plan_ids = {UUID(str(item)) for item in grant.allowed_plan_ids or ()}
        if allowed_plan_ids and plan.id not in allowed_plan_ids:
            raise ValueError("PRIVATE_OFFER_UNAVAILABLE")
        attached_to_current_quote = quote_session_id is not None and grant.attached_quote_session_id == quote_session_id
        if (
            grant.max_quote_conversions is not None
            and int(grant.quote_conversions_count or 0) >= grant.max_quote_conversions
            and not attached_to_current_quote
        ):
            raise ValueError("PRIVATE_CATALOG_GRANT_EXHAUSTED")
        return {
            "grant_id": str(grant.id),
            "policy_id": str(grant.policy_id),
            "policy_version_id": str(grant.policy_version_id),
            "growth_code_id": str(grant.growth_code_id),
            "code_set_hash": grant.code_set_hash,
            "storefront_id": str(grant.storefront_id),
            "sale_channel": grant.sale_channel,
            "allowed_plan_ids": [str(item) for item in sorted(allowed_plan_ids, key=str)],
            "expires_at": expires_at.isoformat(),
            "status": grant.status,
            "subject_type": "user" if grant.user_id is not None else "anonymous_session",
            "anonymous_session_bound": grant.user_id is None,
        }

    async def _resolve_addons(
        self,
        *,
        plan: SubscriptionPlanModel,
        addon_inputs: list[CheckoutAddonInput],
        sale_channel: str,
        existing_quantities_by_code: dict[str, int] | None = None,
        currency: str = "USD",
    ) -> list[CheckoutAddonLine]:
        if not addon_inputs:
            return []
        assert_stage1_addons_enabled(
            addon_count=len(addon_inputs),
            enabled=settings.stage1_addons_enabled,
        )

        catalog = {
            addon.code: addon
            for addon in await self._addon_repo.get_by_codes([addon_input.code for addon_input in addon_inputs])
        }
        totals_by_code: dict[str, int] = dict(existing_quantities_by_code or {})
        lines: list[CheckoutAddonLine] = []
        normalized_currency = _normalize_currency(currency)

        for addon_input in addon_inputs:
            addon = catalog.get(addon_input.code)
            if addon is None:
                raise ValueError(f"Addon not found: {addon_input.code}")
            self._validate_addon(addon, addon_input, plan=plan, sale_channel=sale_channel)
            totals_by_code[addon.code] = totals_by_code.get(addon.code, 0) + addon_input.qty
            unit_price = _resolve_addon_price(addon, normalized_currency)

            lines.append(
                CheckoutAddonLine(
                    addon_id=addon.id,
                    code=addon.code,
                    display_name=addon.display_name,
                    qty=addon_input.qty,
                    unit_price=unit_price,
                    total_price=unit_price * addon_input.qty,
                    location_code=addon_input.location_code,
                    delta_entitlements=addon.delta_entitlements or {},
                )
            )

        plan_code = str(plan.plan_code or "")
        for code in {line.code for line in lines}:
            total_qty = totals_by_code[code]
            addon = catalog[code]
            plan_limits = addon.max_quantity_by_plan or {}
            if plan_limits:
                max_qty = int(plan_limits.get(plan_code, 0) or 0)
                if max_qty <= 0:
                    raise ValueError(f"Addon {code} is not available for plan {plan_code}")
            else:
                max_qty = 0
            if max_qty > 0 and total_qty > max_qty:
                raise ValueError(f"Addon {code} exceeds limit for plan {plan_code}")

        return lines

    @staticmethod
    def _validate_addon(
        addon: PlanAddonModel,
        addon_input: CheckoutAddonInput,
        *,
        plan: SubscriptionPlanModel,
        sale_channel: str,
    ) -> None:
        if not addon.is_active:
            raise ValueError(f"Addon is inactive: {addon.code}")
        if addon.sale_channels and sale_channel not in addon.sale_channels:
            raise ValueError(f"Addon is not available on this channel: {addon.code}")
        if addon_input.qty <= 0:
            raise ValueError(f"Invalid addon quantity for {addon.code}")
        if addon.quantity_step > 1 and addon_input.qty % addon.quantity_step != 0:
            raise ValueError(f"Addon quantity must be a multiple of {addon.quantity_step} for {addon.code}")
        if not addon.is_stackable and addon_input.qty != 1:
            raise ValueError(f"Addon {addon.code} is not stackable")
        if addon.requires_location and not addon_input.location_code:
            raise ValueError(f"Addon {addon.code} requires location_code")
        if _addon_grants_dedicated_ip(addon) and not _plan_allows_dedicated_ip(plan):
            raise ValueError(f"Addon {addon.code} is not available for plan {plan.plan_code}")
        if not plan.is_active:
            raise ValueError("Plan is inactive")


def _addon_grants_dedicated_ip(addon: PlanAddonModel) -> bool:
    delta = addon.delta_entitlements or {}
    raw_value = delta.get("dedicated_ip_count")
    try:
        return int(raw_value or 0) > 0
    except (TypeError, ValueError):
        return False


def _plan_allows_dedicated_ip(plan: SubscriptionPlanModel) -> bool:
    dedicated_ip = plan.dedicated_ip or {}
    return bool(dedicated_ip.get("eligible"))


def _normalize_currency(currency: str) -> str:
    normalized = currency.upper().strip()
    if normalized not in {"USD", "RUB", "XTR"}:
        raise ValueError(f"Unsupported checkout currency: {currency}")
    return normalized


def _resolve_plan_price(plan: SubscriptionPlanModel, currency: str) -> Decimal:
    if currency in {"USD", "XTR"}:
        return Decimal(str(plan.price_usd))
    if currency == "RUB" and plan.price_rub is not None:
        return Decimal(str(plan.price_rub))
    raise ValueError(f"Missing {currency} price for plan {plan.plan_code or plan.id}")


def _resolve_addon_price(addon: PlanAddonModel, currency: str) -> Decimal:
    if currency == "USD":
        return Decimal(str(addon.price_usd))
    if currency == "RUB" and addon.price_rub is not None:
        return Decimal(str(addon.price_rub))
    raise ValueError(f"Missing {currency} price for addon {addon.code}")


def _resolve_base_commission_pct(tiers: list[dict]) -> Decimal:
    commission = Decimal("0")
    for tier in sorted(tiers or [], key=lambda item: int(item.get("min_clients", 0) or 0)):
        if int(tier.get("min_clients", 0) or 0) <= 0:
            commission = Decimal(str(tier.get("commission_pct", 0) or 0))
    return commission


def _quote_resolution_error_message(resolution) -> str:
    if resolution.result == GrowthCodeResolutionStatus.CONFLICTED:
        if resolution.reject_reason == GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE:
            if resolution.code_type == GrowthCodeType.REFERRAL:
                return "Referral codes cannot be combined with partner codes"
            return "Promo codes cannot be combined with partner codes"
        if resolution.reject_reason == GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING:
            if resolution.code_type == GrowthCodeType.REFERRAL:
                return "Referral codes cannot be combined with active partner bindings"
            return "Promo codes cannot be combined with active partner bindings"

    if resolution.reject_reason == GrowthCodeRejectReason.CODE_NOT_ACTIVE:
        if resolution.code_type == GrowthCodeType.PARTNER:
            return "Partner code is inactive"
        return "Promo code is inactive"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_EXPIRED:
        if resolution.code_type == GrowthCodeType.INVITE:
            return "Invite code expired"
        return "Promo code expired"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_EXHAUSTED:
        return "Promo code usage limit reached"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_ALREADY_REDEEMED:
        if resolution.code_type == GrowthCodeType.INVITE:
            return "Invite code already used"
        return "Promo code already used"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SKU:
        if resolution.code_type == GrowthCodeType.REFERRAL:
            return "Referral code is not eligible for this plan"
        return "Promo code is not eligible for this plan"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_NOT_ELIGIBLE_FOR_SURFACE:
        if resolution.code_type == GrowthCodeType.PARTNER:
            return "Partner code is not eligible for this checkout surface"
        return "Code is not eligible for this checkout surface"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_WRONG_CONTEXT:
        if resolution.code_type == GrowthCodeType.INVITE:
            return "Invite code must be redeemed outside checkout"
        if resolution.code_type == GrowthCodeType.PARTNER:
            return "Partner code can only be applied in checkout"
        return "Promo code can only be applied in checkout"
    if resolution.reject_reason == GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK:
        if resolution.code_type == GrowthCodeType.REFERRAL:
            return "Referral code is blocked by risk policy"
        if resolution.code_type == GrowthCodeType.PARTNER:
            return "Partner code self-referral is blocked"
    return "Growth code is not valid"


def _assert_checkout_partner_eligibility(eligibility: PartnerCodeEligibilityResult) -> None:
    if eligibility.allowed:
        return
    reason_codes = set(eligibility.reason_codes)
    if reason_codes.intersection({"sale_channel_not_allowed", "storefront_not_allowed", "geography_not_allowed"}):
        raise ValueError("Partner code is not eligible for this checkout surface")
    raise ValueError("Partner code not found or inactive")


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_code_input(*, code_input: str | None, promo_code: str | None) -> str | None:
    normalized_code_input = code_input.strip() if code_input else None
    normalized_promo_code = promo_code.strip() if promo_code else None
    if normalized_code_input and normalized_promo_code and normalized_code_input != normalized_promo_code:
        raise ValueError("code_input and promo_code must match when both are provided")
    return normalized_code_input or normalized_promo_code


def _normalize_code_basket(
    code_basket: list[CheckoutCodeBasketInput],
) -> list[tuple[int, str, str | None]]:
    if not code_basket:
        return []
    if len(code_basket) > 5:
        raise ValueError("codes supports at most 5 entries")
    normalized: list[tuple[int, str, str | None]] = []
    for index, item in enumerate(code_basket):
        code = item.code.strip()
        if not code:
            raise ValueError("codes entries cannot be empty")
        if len(code) > 64:
            raise ValueError("codes entries cannot exceed 64 characters")
        normalized.append((index, code, item.client_slot_id))
    return normalized


def _safe_basket_code_ref(code: str) -> dict:
    normalized = code.strip()
    return {
        "redacted": True,
        "code_hash": hash_growth_code(normalized),
        "code_prefix": normalized[:3].upper() if len(normalized) > 4 else "***",
        "code_length": len(normalized),
    }


def _basket_reject_application(
    *,
    position_entered: int,
    code_ref: dict,
    client_slot_id: str | None,
    status: str,
    reject_reason: str,
    user_message_key: str,
) -> dict:
    return {
        "position_entered": position_entered,
        "canonical_order": position_entered,
        "growth_code_id": None,
        "masked_code": _masked_code_from_ref(code_ref),
        "roles": [],
        "status": status,
        "reject_reason": reject_reason,
        "user_message_key": user_message_key,
        "discount": _empty_discount(),
        "benefits": [],
        "reservation_id": None,
        "code_ref": code_ref,
        "client_slot_id": client_slot_id,
        "evaluation_trace": {
            "source": "checkout_code_basket",
            "schema_version": "checkout_code_set.v6",
        },
    }


def _basket_application_from_resolution(
    *,
    position_entered: int,
    code: str,
    code_ref: dict,
    client_slot_id: str | None,
    resolution: GrowthCodeResolutionOutcome,
    currency: str,
) -> dict:
    policy_snapshot = dict(resolution.policy_snapshot or {})
    code_type = resolution.code_type.value if resolution.code_type else "unknown"
    return {
        "position_entered": position_entered,
        "canonical_order": position_entered,
        "growth_code_id": str(resolution.growth_code_id) if resolution.growth_code_id else None,
        "masked_code": _masked_code_from_ref(code_ref),
        "roles": _roles_for_resolution(resolution),
        "status": "accepted" if resolution.accepted else resolution.result.value,
        "reject_reason": resolution.reject_reason.value if resolution.reject_reason else None,
        "conflict_code": resolution.conflict_code,
        "wrong_context_target": resolution.wrong_context_target.value if resolution.wrong_context_target else None,
        "user_message_key": resolution.user_message_key,
        "policy_version_id": _string_or_none(policy_snapshot.get("policy_version_id")),
        "rule_checksum": policy_snapshot.get("rule_checksum"),
        "discount": {
            **_empty_discount(currency=currency),
            "strategy": "not_selected",
        },
        "benefits": list(policy_snapshot.get("benefits") or []),
        "reservation_id": None,
        "risk_decision_id": _string_or_none(policy_snapshot.get("risk_decision_id")),
        "fx_conversion_id": None,
        "code_ref": code_ref,
        "legacy_code_type": code_type,
        "legacy_code_id": _string_or_none(resolution.promo_code_id or resolution.partner_code_id),
        "client_slot_id": client_slot_id,
        "evaluation_trace": {
            "source": "checkout_code_basket",
            "schema_version": "checkout_code_set.v6",
            "message_key": resolution.user_message_key,
            "code_type": code_type,
            "code_hash": hash_growth_code(code),
        },
    }


def _roles_for_resolution(resolution: GrowthCodeResolutionOutcome) -> list[str]:
    if resolution.code_type == GrowthCodeType.PROMO:
        roles = ["discount"]
        if (resolution.policy_snapshot or {}).get("benefits"):
            roles.append("benefit")
        return roles
    if resolution.code_type == GrowthCodeType.REFERRAL:
        return ["attribution", "discount"]
    if resolution.code_type == GrowthCodeType.PARTNER:
        return ["attribution"]
    if resolution.code_type in {GrowthCodeType.INVITE, GrowthCodeType.GIFT}:
        return ["benefit"]
    return []


def _select_basket_discounts(
    *,
    candidates: list[_BasketDiscountCandidate],
    displayed_price: Decimal,
    currency: str,
) -> tuple[Decimal, list[_BasketDiscountCandidate]]:
    percent_candidates = [item for item in candidates if item.discount_kind == "percent"]
    fixed_candidates = [item for item in candidates if item.discount_kind != "percent"]
    selected: list[_BasketDiscountCandidate] = []
    remaining = displayed_price
    if percent_candidates:
        primary = max(percent_candidates, key=lambda item: (item.source_amount, item.code_hash))
        applied = min(primary.source_amount, remaining)
        selected.append(
            _BasketDiscountCandidate(
                code=primary.code,
                code_hash=primary.code_hash,
                discount_type=primary.discount_type,
                discount_kind=primary.discount_kind,
                source_amount=primary.source_amount,
                strategy=primary.strategy,
                source_currency=primary.source_currency,
                rate_snapshots=primary.rate_snapshots,
                policy_version_id=primary.policy_version_id,
                applied_amount=applied,
                fx_conversion=None,
            )
        )
        remaining -= applied
    for fixed in sorted(fixed_candidates, key=lambda item: (-item.source_amount, item.code_hash)):
        if remaining <= 0:
            break
        try:
            conversion = convert_fixed_discount(
                source_amount=fixed.source_amount,
                source_currency=fixed.source_currency or currency,
                quote_currency=currency,
                discountable_amount=remaining,
                rate_snapshots=fixed.rate_snapshots,
            )
        except FxConversionError as exc:
            observe_growth_fx_conversion_failure(reason=exc.code)
            raise
        applied = conversion.applied_amount
        conversion_payload = conversion.to_payload()
        selected.append(
            _BasketDiscountCandidate(
                code=fixed.code,
                code_hash=fixed.code_hash,
                discount_type=fixed.discount_type,
                discount_kind=fixed.discount_kind,
                source_amount=fixed.source_amount,
                strategy=fixed.strategy,
                source_currency=fixed.source_currency or currency,
                rate_snapshots=fixed.rate_snapshots,
                policy_version_id=fixed.policy_version_id,
                applied_amount=applied,
                fx_conversion={
                    **conversion_payload,
                    "conversion_mode": conversion_mode_from_payload(conversion_payload.get("rate_snapshot")),
                    "rounding_mode": "ROUND_HALF_UP",
                    "no_rerate": True,
                },
            )
        )
        remaining -= applied
    discount_amount = displayed_price - max(remaining, Decimal("0"))
    return max(discount_amount, Decimal("0")), selected


def _empty_discount(*, currency: str = "USD") -> dict:
    return {
        "source_amount": "0.00",
        "source_currency": currency,
        "target_amount": "0.00",
        "target_currency": currency,
        "applied_amount": "0.00",
    }


def _policy_version_id_from_snapshot(snapshot: dict | None) -> UUID | None:
    raw_value = (snapshot or {}).get("policy_version_id")
    if raw_value in (None, ""):
        return None
    return UUID(str(raw_value))


def _merge_policy_snapshots(*snapshots: dict | None) -> dict:
    merged: dict = {}
    for snapshot in snapshots:
        if isinstance(snapshot, dict):
            merged.update(snapshot)
    return merged


def _fixed_discount_source_currency(*, policy_snapshot: dict, quote_currency: str | None) -> str | None:
    for key in ("fixed_discount_currency", "discount_currency", "source_currency", "currency_code"):
        value = policy_snapshot.get(key)
        if value not in (None, ""):
            return str(value)
    fx_payload = policy_snapshot.get("fx")
    if isinstance(fx_payload, dict):
        for key in ("fixed_discount_currency", "discount_currency", "source_currency"):
            value = fx_payload.get(key)
            if value not in (None, ""):
                return str(value)
    return quote_currency


def _string_or_none(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _masked_code_from_ref(code_ref: dict) -> str:
    prefix = str(code_ref.get("code_prefix") or "***")[:12]
    code_hash = str(code_ref.get("code_hash") or "")
    suffix = code_hash[:12] if code_hash else "unknown"
    return f"{prefix}...{suffix}"[:32]
