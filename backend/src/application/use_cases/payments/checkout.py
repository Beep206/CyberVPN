"""Unified checkout quote calculation for plans, add-ons, promo, and wallet."""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.services.wallet_service import WalletService
from src.application.use_cases.attribution.qualifying_events.evaluate_order_policy import _evaluate_stacking
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.plan_addon_model import PlanAddonModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.plan_addon_repo import PlanAddonRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckoutAddonInput:
    """Single add-on selection from checkout payload."""

    code: str
    qty: int
    location_code: str | None = None


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
    addons: list[CheckoutAddonLine] = field(default_factory=list)
    entitlements_snapshot: dict = field(default_factory=dict)
    commission_base_amount: Decimal = Decimal("0")


class CheckoutUseCase:
    """Calculate checkout price and entitlement snapshot without persisting payment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._plan_repo = SubscriptionPlanRepository(session)
        self._promo_repo = PromoCodeRepository(session)
        self._partner_repo = PartnerRepository(session)
        self._addon_repo = PlanAddonRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        user_id: UUID,
        plan_id: UUID,
        *,
        promo_code: str | None = None,
        partner_code: str | None = None,
        use_wallet: Decimal = Decimal("0"),
        addons: list[CheckoutAddonInput] | None = None,
        sale_channel: str = "web",
    ) -> CheckoutResult:
        plan = await self._resolve_plan(plan_id, sale_channel=sale_channel)
        addon_lines = await self._resolve_addons(plan=plan, addon_inputs=addons or [], sale_channel=sale_channel)

        base_price = Decimal(str(plan.price_usd))
        addon_amount = sum((line.total_price for line in addon_lines), Decimal("0"))

        partner_markup = Decimal("0")
        partner_code_id = None

        user = await self._session.get(MobileUserModel, user_id)
        normalized_partner_code = partner_code.strip() if partner_code else None
        if normalized_partner_code:
            explicit_code = await self._partner_repo.get_active_code_by_code(normalized_partner_code)
            if explicit_code is None:
                raise ValueError("Partner code not found or inactive")
            partner_markup = base_price * (Decimal(str(explicit_code.markup_pct)) / Decimal("100"))
            partner_code_id = explicit_code.id
        elif user and user.partner_user_id:
            codes = await self._partner_repo.get_codes_by_partner(user.partner_user_id)
            active_code = next((code for code in codes if code.is_active), None)
            if active_code:
                partner_markup = base_price * (Decimal(str(active_code.markup_pct)) / Decimal("100"))
                partner_code_id = active_code.id

        stacking = _evaluate_stacking(
            promo_present=bool(promo_code and promo_code.strip()),
            partner_code_present=partner_code_id is not None,
            wallet_present=use_wallet > 0,
        )
        if not stacking.stacking_valid:
            raise ValueError("Promo codes cannot be combined with partner codes")

        displayed_price = base_price + addon_amount + partner_markup

        discount_amount = Decimal("0")
        promo_code_id = None
        if promo_code:
            promo = await self._promo_repo.get_active_by_code(promo_code)
            if promo:
                promo_code_id = promo.id
                if promo.discount_type == "percent":
                    discount_amount = displayed_price * (Decimal(str(promo.discount_value)) / Decimal("100"))
                else:
                    discount_amount = min(Decimal(str(promo.discount_value)), displayed_price)

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
            addons=addon_lines,
            entitlements_snapshot=entitlements_snapshot,
            commission_base_amount=base_price,
        )

    async def _resolve_plan(self, plan_id: UUID, *, sale_channel: str) -> SubscriptionPlanModel:
        plan = await self._plan_repo.get_by_id(plan_id)
        if plan is None:
            msg = f"Plan not found: {plan_id}"
            raise ValueError(msg)
        if not plan.is_active:
            raise ValueError("Plan is inactive")
        if sale_channel != "admin" and plan.catalog_visibility != "public":
            raise ValueError("Plan is not available on this channel")
        if plan.sale_channels and sale_channel not in plan.sale_channels:
            raise ValueError("Plan is not available on this channel")
        return plan

    async def _resolve_addons(
        self,
        *,
        plan: SubscriptionPlanModel,
        addon_inputs: list[CheckoutAddonInput],
        sale_channel: str,
        existing_quantities_by_code: dict[str, int] | None = None,
    ) -> list[CheckoutAddonLine]:
        if not addon_inputs:
            return []

        catalog = {
            addon.code: addon
            for addon in await self._addon_repo.get_by_codes([addon_input.code for addon_input in addon_inputs])
        }
        totals_by_code: dict[str, int] = dict(existing_quantities_by_code or {})
        lines: list[CheckoutAddonLine] = []

        for addon_input in addon_inputs:
            addon = catalog.get(addon_input.code)
            if addon is None:
                raise ValueError(f"Addon not found: {addon_input.code}")
            self._validate_addon(addon, addon_input, plan=plan, sale_channel=sale_channel)
            totals_by_code[addon.code] = totals_by_code.get(addon.code, 0) + addon_input.qty

            lines.append(
                CheckoutAddonLine(
                    addon_id=addon.id,
                    code=addon.code,
                    display_name=addon.display_name,
                    qty=addon_input.qty,
                    unit_price=Decimal(str(addon.price_usd)),
                    total_price=Decimal(str(addon.price_usd)) * addon_input.qty,
                    location_code=addon_input.location_code,
                    delta_entitlements=addon.delta_entitlements or {},
                )
            )

        plan_code = str(plan.plan_code or "")
        for code, total_qty in totals_by_code.items():
            addon = catalog[code]
            max_qty = int((addon.max_quantity_by_plan or {}).get(plan_code, 0) or 0)
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
        if not plan.is_active:
            raise ValueError("Plan is inactive")
