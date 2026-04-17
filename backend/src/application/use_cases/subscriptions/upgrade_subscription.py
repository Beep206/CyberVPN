"""Quote subscription upgrades against the current active plan."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.entitlements_service import EntitlementsService
from src.application.use_cases.payments.checkout import CheckoutResult, CheckoutUseCase
from src.infrastructure.database.repositories.payment_repo import PaymentRepository


class UpgradeSubscriptionUseCase:
    """Quote an upgrade to a new plan for the current subscriber."""

    def __init__(self, session: AsyncSession) -> None:
        self._payments = PaymentRepository(session)
        self._checkout = CheckoutUseCase(session)
        self._entitlements = EntitlementsService(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        target_plan_id: UUID,
        promo_code: str | None = None,
        use_wallet: Decimal = Decimal("0"),
        sale_channel: str = "web",
    ) -> CheckoutResult:
        active_payment = await self._payments.get_latest_active_plan_payment(user_id)
        if active_payment is None or active_payment.plan_id is None:
            raise ValueError("No active subscription to upgrade")
        if active_payment.plan_id == target_plan_id:
            raise ValueError("Target plan matches the current subscription")

        quote = await self._checkout.execute(
            user_id=user_id,
            plan_id=target_plan_id,
            promo_code=promo_code,
            use_wallet=use_wallet,
            sale_channel=sale_channel,
        )
        active_addon_lines = await self._entitlements.list_active_addon_lines(user_id)
        if active_addon_lines:
            plan = await self._checkout._plan_repo.get_by_id(target_plan_id)
            if plan is not None:
                quote.entitlements_snapshot = EntitlementsService.build_snapshot(
                    plan=plan,
                    addon_lines=active_addon_lines,
                )
        return quote
