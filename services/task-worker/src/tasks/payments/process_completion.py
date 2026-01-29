"""Process completed payment — enable user and extend subscription."""

from typing import Any, cast

import structlog
from datetime import datetime, timezone
from sqlalchemy import select

from src.broker import broker
from src.database.session import get_session_factory
from src.models.payment import PaymentModel
from src.services.remnawave_client import RemnawaveClient
from src.services.sse_publisher import publish_event
from src.services.telegram_client import TelegramClient
from src.utils.formatting import payment_received

logger = structlog.get_logger(__name__)


@broker.task(task_name="process_payment_completion", queue="payments")
async def process_payment_completion(payment_id: str) -> dict:
    """Process a completed payment: update DB, enable user, send notification."""
    factory = get_session_factory()

    async with factory() as session:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            logger.error("payment_not_found", payment_id=payment_id)
            return {"error": "payment_not_found"}

        if payment.status == "completed":
            return {"already_processed": True}

        # Update payment status
        payment.status = "completed"
        payment.updated_at = datetime.now(timezone.utc)
        session.add(payment)
        await session.commit()

    # Enable user via Remnawave and extend subscription
    user_uuid = str(payment.user_uuid)
    subscription_extended = False
    try:
        async with RemnawaveClient() as rw:
            user = await rw.get_user(user_uuid)
            extend_days = int(payment.subscription_days or 0)
            if extend_days > 0:
                await rw.bulk_extend_expiration_date([user_uuid], extend_days)
                subscription_extended = True
            await rw.enable_user(user_uuid)
    except Exception as e:
        logger.error(
            "enable_user_failed",
            user_uuid=user_uuid,
            subscription_extended=subscription_extended,
            error=str(e),
        )
        return {
            "payment_updated": True,
            "user_enabled": False,
            "subscription_extended": subscription_extended,
            "error": str(e),
        }

    # Send notification
    username = user.get("username", "unknown")
    telegram_id = user.get("telegramId")
    plan_name = ""
    if payment.metadata_ and isinstance(payment.metadata_, dict):
        plan_name = payment.metadata_.get("plan_name") or payment.metadata_.get("planName") or ""
    if telegram_id:
        msg = payment_received(username, float(payment.amount), payment.currency, plan_name, payment.subscription_days)
        try:
            async with TelegramClient() as tg:
                await tg.send_message(chat_id=int(telegram_id), text=msg)
        except Exception:
            pass

    try:
        await publish_event(
            "payment.completed",
            {
                "payment_id": str(payment.id),
                "user_uuid": user_uuid,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "subscription_days": payment.subscription_days,
                "subscription_extended": subscription_extended,
            },
        )
    except Exception:
        logger.warning("payment_sse_publish_failed", payment_id=payment_id)

    logger.info(
        "payment_processed",
        payment_id=payment_id,
        user_uuid=user_uuid,
        subscription_extended=subscription_extended,
    )
    return {
        "payment_updated": True,
        "user_enabled": True,
        "subscription_extended": subscription_extended,
    }


process_payment_completion = cast(Any, process_payment_completion).with_labels(retry_policy="payments_webhook")
