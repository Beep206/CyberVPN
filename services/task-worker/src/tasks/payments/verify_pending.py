"""Verify pending payment statuses via CryptoBot API."""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.models.payment import PaymentModel
from src.services.cryptobot_client import CryptoBotClient
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.services.telegram_client import TelegramClient
from src.tasks.payments.process_completion import process_payment_completion
from src.utils.formatting import payment_failed

logger = structlog.get_logger(__name__)


@broker.task(task_name="verify_pending_payments", queue="payments")
async def verify_pending_payments() -> dict:
    """Check status of all pending payments via CryptoBot API."""
    factory = get_session_factory()
    settings = get_settings()
    checked = 0
    completed = 0
    expired = 0

    async with factory() as session:
        stmt = select(PaymentModel).where(PaymentModel.status == "pending").where(PaymentModel.provider == "cryptobot")
        result = await session.execute(stmt)
        pending = result.scalars().all()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_pending = []
    stale_pending = []

    for payment in pending:
        if payment.created_at and payment.created_at < cutoff:
            stale_pending.append(payment)
        else:
            recent_pending.append(payment)

    external_ids = [int(p.external_id) for p in recent_pending if p.external_id and p.external_id.isdigit()]

    invoices = []
    if external_ids:
        async with CryptoBotClient(settings.cryptobot_token) as cb:
            invoices = await cb.get_invoices(invoice_ids=external_ids)

    invoice_map = {str(inv.get("invoice_id")): inv for inv in invoices}

    async with RemnawaveClient() as rw, TelegramClient() as tg:
        for payment in recent_pending:
            checked += 1
            if not payment.external_id:
                continue
            invoice = invoice_map.get(payment.external_id)
            if not invoice:
                continue

            invoice_status = invoice.get("status", "")
            if invoice_status == "paid":
                await process_payment_completion.kiq(payment_id=str(payment.id))
                completed += 1
            elif invoice_status in ("expired", "cancelled"):
                async with factory() as session:
                    payment.status = invoice_status
                    session.add(payment)
                    await session.commit()

                expired += 1
                await _notify_payment_failed(payment, invoice_status, rw, tg)

        for payment in stale_pending:
            checked += 1
            async with factory() as session:
                payment.status = "failed"
                session.add(payment)
                await session.commit()

            expired += 1
            await _notify_payment_failed(payment, "expired", rw, tg)

    redis = get_redis_client()
    failure_rate = 0.0
    try:
        async with factory() as session:
            total_stmt = select(func.count()).select_from(PaymentModel).where(PaymentModel.created_at >= cutoff)
            failed_stmt = (
                select(func.count())
                .select_from(PaymentModel)
                .where(
                    PaymentModel.created_at >= cutoff,
                    PaymentModel.status.in_(["failed", "expired", "cancelled"]),
                )
            )
            total_count = (await session.execute(total_stmt)).scalar() or 0
            failed_count = (await session.execute(failed_stmt)).scalar() or 0

        failure_rate = (failed_count / total_count * 100) if total_count else 0.0
        await redis.set("cybervpn:metrics:payment_failure_rate", f"{failure_rate:.4f}", ex=900)
    finally:
        await redis.aclose()

    logger.info(
        "pending_payments_verified",
        checked=checked,
        completed=completed,
        expired=expired,
        failure_rate=f"{failure_rate:.2f}",
    )
    return {"checked": checked, "completed": completed, "expired": expired}


async def _notify_payment_failed(
    payment: PaymentModel,
    reason: str,
    rw: RemnawaveClient,
    tg: TelegramClient,
) -> None:
    try:
        user = await rw.get_user(str(payment.user_uuid))
    except Exception as e:
        logger.warning("payment_user_lookup_failed", payment_id=str(payment.id), error=str(e))
        return

    telegram_id = user.get("telegramId") if user else None
    if not telegram_id:
        return

    msg = payment_failed(
        username=user.get("username", "unknown"),
        amount=float(payment.amount),
        currency=payment.currency,
        reason=reason,
    )
    try:
        await tg.send_message(chat_id=int(telegram_id), text=msg)
    except Exception as e:
        logger.warning("payment_failed_notification_error", payment_id=str(payment.id), error=str(e))
