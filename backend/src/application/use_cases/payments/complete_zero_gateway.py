"""Complete a zero-gateway payment (fully covered by promo + wallet)."""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.wallet_service import WalletService
from src.domain.enums import WalletTxReason
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.payment_repo import PaymentRepository
from src.infrastructure.database.repositories.subscription_plan_repo import SubscriptionPlanRepository
from src.infrastructure.database.repositories.wallet_repo import WalletRepository

logger = logging.getLogger(__name__)


class CompleteZeroGatewayUseCase:
    """Complete payment immediately when promo+wallet cover the full amount."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._payment_repo = PaymentRepository(session)
        self._plan_repo = SubscriptionPlanRepository(session)
        wallet_repo = WalletRepository(session)
        self._wallet = WalletService(wallet_repo)

    async def execute(
        self,
        user_id: UUID,
        plan_id: UUID,
        base_price: Decimal,
        displayed_price: Decimal,
        discount_amount: Decimal,
        wallet_amount: Decimal,
        promo_code_id: UUID | None,
        partner_code_id: UUID | None,
        currency: str = "USD",
    ) -> PaymentModel:
        # Get plan for subscription_days
        plan = await self._plan_repo.get_by_id(plan_id)
        if plan is None:
            msg = f"Plan not found: {plan_id}"
            raise ValueError(msg)

        # Create payment record
        payment = PaymentModel(
            user_uuid=user_id,
            amount=float(base_price),
            currency=currency,
            status="completed",
            provider="wallet",
            subscription_days=plan.duration_days,
            plan_id=plan_id,
            promo_code_id=promo_code_id,
            partner_code_id=partner_code_id,
            discount_amount=float(discount_amount),
            wallet_amount_used=float(wallet_amount),
            final_amount=0.0,
        )
        payment = await self._payment_repo.create(payment)

        # Debit wallet if any wallet amount was used
        if wallet_amount > 0:
            await self._wallet.debit(
                user_id=user_id,
                amount=wallet_amount,
                reason=WalletTxReason.SUBSCRIPTION_PAYMENT,
                description=f"Zero-gateway payment for plan {plan.name}",
                reference_type="payment",
                reference_id=payment.id,
            )

        await self._session.commit()

        logger.info(
            "Zero-gateway payment completed",
            extra={
                "payment_id": str(payment.id),
                "user_id": str(user_id),
                "plan_id": str(plan_id),
                "wallet_debited": str(wallet_amount),
            },
        )
        return payment
