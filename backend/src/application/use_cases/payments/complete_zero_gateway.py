"""Persist a checkout that is fully covered without a gateway invoice."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository

logger = logging.getLogger(__name__)


class CompleteZeroGatewayUseCase:
    """Create a completed local payment for a zero-gateway checkout."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payment_repo = PaymentRepository(session)
        self._plan_repo = SubscriptionPlanRepository(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None,
        displayed_price: Decimal,
        discount_amount: Decimal,
        wallet_amount: Decimal,
        promo_code_id: UUID | None,
        partner_code_id: UUID | None,
        currency: str = "USD",
        addons_snapshot: list[dict] | None = None,
        entitlements_snapshot: dict | None = None,
        commission_base_amount: Decimal = Decimal("0"),
        metadata_extra: dict | None = None,
        subscription_days_override: int | None = None,
    ) -> PaymentModel:
        plan = None
        if plan_id is not None:
            plan = await self._plan_repo.get_by_id(plan_id)
            if plan is None:
                msg = f"Plan not found: {plan_id}"
                raise ValueError(msg)

        payment = PaymentModel(
            user_uuid=user_id,
            amount=float(displayed_price),
            currency=currency,
            status="completed",
            provider="wallet",
            subscription_days=subscription_days_override or (plan.duration_days if plan is not None else 0),
            plan_id=plan_id,
            promo_code_id=promo_code_id,
            partner_code_id=partner_code_id,
            discount_amount=float(discount_amount),
            wallet_amount_used=float(wallet_amount),
            final_amount=0.0,
            addons_snapshot=addons_snapshot or [],
            entitlements_snapshot=entitlements_snapshot,
            metadata_={
                "commission_base_amount": str(commission_base_amount),
                "checkout_mode": "zero_gateway",
                **(metadata_extra or {}),
            },
        )
        payment = await self._payment_repo.create(payment)

        logger.info(
            "zero_gateway_payment_persisted",
            extra={
                "payment_id": str(payment.id),
                "user_id": str(user_id),
                "plan_id": str(plan_id),
            },
        )
        return payment
