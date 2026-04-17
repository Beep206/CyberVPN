"""Quote add-on purchases against the current active subscription."""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.services.wallet_service import WalletService
from src.application.use_cases.payments.checkout import (
    CheckoutAddonInput,
    CheckoutResult,
    CheckoutUseCase,
)
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.promo_code_repo import PromoCodeRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository


class PurchaseAddonsUseCase:
    """Create an add-on quote for the current subscription window."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payments = PaymentRepository(session)
        self._plans = SubscriptionPlanRepository(session)
        self._promo_repo = PromoCodeRepository(session)
        self._entitlements = EntitlementsService(session)
        self._checkout = CheckoutUseCase(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        *,
        user_id: UUID,
        addons: list[CheckoutAddonInput],
        promo_code: str | None = None,
        use_wallet: Decimal = Decimal("0"),
        sale_channel: str = "web",
    ) -> CheckoutResult:
        payment = await self._payments.get_latest_active_plan_payment(user_id)
        if payment is None or payment.plan_id is None:
            raise ValueError("No active subscription to attach add-ons to")

        plan = await self._plans.get_by_id(payment.plan_id)
        if plan is None:
            raise ValueError("Active plan not found")

        active_addon_lines = await self._entitlements.list_active_addon_lines(user_id)
        existing_quantities = {
            str(line["code"]): int(line.get("qty", 1))
            for line in active_addon_lines
        }
        addon_lines = await self._checkout._resolve_addons(
            plan=plan,
            addon_inputs=addons,
            sale_channel=sale_channel,
            existing_quantities_by_code=existing_quantities,
        )

        addon_amount = sum((line.total_price for line in addon_lines), Decimal("0"))
        discount_amount = Decimal("0")
        promo_code_id = None
        if promo_code:
            promo = await self._promo_repo.get_active_by_code(promo_code)
            if promo:
                promo_code_id = promo.id
                if promo.discount_type == "percent":
                    discount_amount = addon_amount * (Decimal(str(promo.discount_value)) / Decimal("100"))
                else:
                    discount_amount = min(Decimal(str(promo.discount_value)), addon_amount)

        after_promo = addon_amount - discount_amount
        wallet_amount = Decimal("0")
        if use_wallet > 0:
            wallet = await self._wallet.get_balance(user_id)
            available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
            wallet_amount = min(use_wallet, available, after_promo)

        gateway_amount = after_promo - wallet_amount
        if gateway_amount < 0:
            gateway_amount = Decimal("0")

        expires_at = self._resolve_expires_at(payment)
        remaining_days = self._resolve_remaining_days(expires_at)
        entitlements_snapshot = EntitlementsService.build_snapshot(
            plan=plan,
            addon_lines=active_addon_lines
            + [
                {
                    "code": line.code,
                    "qty": line.qty,
                    "location_code": line.location_code,
                    "delta_entitlements": line.delta_entitlements,
                }
                for line in addon_lines
            ],
            expires_at=expires_at,
        )

        return CheckoutResult(
            base_price=Decimal("0"),
            addon_amount=addon_amount,
            displayed_price=addon_amount,
            discount_amount=discount_amount,
            wallet_amount=wallet_amount,
            gateway_amount=gateway_amount,
            partner_markup=Decimal("0"),
            is_zero_gateway=gateway_amount <= 0,
            plan_id=plan.id,
            promo_code_id=promo_code_id,
            partner_code_id=None,
            plan_name=plan.name,
            duration_days=remaining_days,
            addons=addon_lines,
            entitlements_snapshot=entitlements_snapshot,
            commission_base_amount=Decimal("0"),
        )

    @staticmethod
    def _resolve_expires_at(payment) -> datetime | None:
        if payment.subscription_days <= 0:
            return None
        return payment.created_at + timedelta(days=payment.subscription_days)

    @staticmethod
    def _resolve_remaining_days(expires_at: datetime | None) -> int:
        if expires_at is None:
            return 0
        seconds = max(0.0, (expires_at - datetime.now(UTC)).total_seconds())
        return max(1, math.ceil(seconds / 86400))
