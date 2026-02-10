"""Unfreeze expired wallet holds for pending payments that timed out."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, text

from src.broker import broker
from src.database.session import get_session_factory

logger = structlog.get_logger(__name__)

# Timeout for pending payment wallet freeze (30 minutes)
FREEZE_TIMEOUT_MINUTES = 30


@broker.task(task_name="unfreeze_expired_wallets", queue="wallet")
async def unfreeze_expired_wallets() -> dict:
    """Unfreeze wallet amounts for payments that expired without completion.

    Finds pending payments older than 30 minutes that still have frozen
    wallet amounts, and returns those amounts to the user's available balance.
    """
    factory = get_session_factory()
    unfrozen_count = 0
    total_unfrozen = Decimal("0")
    cutoff = datetime.now(UTC) - timedelta(minutes=FREEZE_TIMEOUT_MINUTES)

    async with factory() as session:
        from src.models.payment import PaymentModel

        # Find expired pending payments with frozen wallet amounts
        stmt = select(PaymentModel).where(
            PaymentModel.status == "pending",
            PaymentModel.wallet_amount_used > 0,
            PaymentModel.created_at < cutoff,
        )
        result = await session.execute(stmt)
        expired_payments = result.scalars().all()

        if not expired_payments:
            logger.info("unfreeze_expired_wallets_none_found")
            return {"unfrozen": 0, "total_amount": "0"}

        for payment in expired_payments:
            wallet_amount = Decimal(str(payment.wallet_amount_used))
            user_uuid = payment.user_uuid

            try:
                # Decrease frozen amount on wallet (GREATEST prevents going below 0)
                await session.execute(
                    text("""
                        UPDATE wallets
                        SET frozen = GREATEST(frozen - :amount, 0),
                            updated_at = NOW()
                        WHERE user_id = :user_id
                    """),
                    {"amount": float(wallet_amount), "user_id": str(user_uuid)},
                )

                # Clear wallet_amount_used on payment to prevent double-unfreeze
                payment.wallet_amount_used = 0
                session.add(payment)

                unfrozen_count += 1
                total_unfrozen += wallet_amount

                logger.info(
                    "wallet_unfrozen_for_expired_payment",
                    payment_id=str(payment.id),
                    user_uuid=str(user_uuid),
                    amount=str(wallet_amount),
                )
            except Exception:
                logger.exception(
                    "wallet_unfreeze_failed",
                    payment_id=str(payment.id),
                    user_uuid=str(user_uuid),
                )

        await session.commit()

    logger.info(
        "unfreeze_expired_wallets_completed",
        unfrozen_count=unfrozen_count,
        total_amount=str(total_unfrozen),
    )
    return {"unfrozen": unfrozen_count, "total_amount": str(total_unfrozen)}
