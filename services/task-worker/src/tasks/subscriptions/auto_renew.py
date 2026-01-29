"""Auto-renew subscriptions for users with auto_renew enabled."""

from datetime import datetime, timedelta, timezone

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cryptobot_client import CryptoBotClient
from src.services.remnawave_client import RemnawaveClient
from src.services.telegram_client import TelegramClient
from src.utils.formatting import auto_renew_invoice

logger = structlog.get_logger(__name__)


@broker.task(task_name="auto_renew_subscriptions", queue="subscriptions")
async def auto_renew_subscriptions() -> dict:
    """Auto-renew subscriptions for users with auto_renew=true and expire_at < now() + 1 hour.

    Queries users from Remnawave API, filters those with auto_renew enabled
    and expiring within 1 hour, creates CryptoBot invoices, and sends
    Telegram notifications with payment links.

    Returns:
        Dictionary with invoices_created count
    """
    settings = get_settings()
    invoices_created = 0
    users_checked = 0

    try:
        async with RemnawaveClient() as rw:
            users = await rw.get_users()

        renewal_threshold = datetime.now(timezone.utc) + timedelta(hours=1)

        async with CryptoBotClient(settings.cryptobot_token) as cb, TelegramClient() as tg:
            for user in users:
                users_checked += 1

                # Check auto_renew flag
                auto_renew = user.get("autoRenew", False)
                if not auto_renew:
                    continue

                # Parse expiration date
                expire_at = user.get("expiresAt")
                if not expire_at:
                    continue

                try:
                    exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    logger.warning("invalid_expire_date", user=user.get("username"), expire_at=expire_at)
                    continue

                # Only process if expiring within 1 hour
                if exp_dt > renewal_threshold:
                    continue

                username = user.get("username", "unknown")
                telegram_id = user.get("telegramId")
                user_uuid = user.get("uuid")

                if not telegram_id or not user_uuid:
                    logger.warning("missing_user_data", username=username)
                    continue

                # Get subscription plan details
                plan_name = user.get("subscriptionPlan", "Standard")
                amount = user.get("planPrice", 10.0)
                currency = user.get("planCurrency", "USD")

                try:
                    # Create invoice via CryptoBot
                    invoice = await cb.create_invoice(
                        amount=amount,
                        currency=currency,
                        description=f"Auto-renewal: {plan_name}",
                        payload=str(user_uuid),
                    )
                    pay_url = invoice.get("pay_url", "")

                    if not pay_url:
                        logger.error("no_pay_url_in_invoice", username=username, invoice=invoice)
                        continue

                    # Send notification with payment link
                    msg = auto_renew_invoice(username, amount, currency, pay_url)
                    await tg.send_message(chat_id=int(telegram_id), text=msg)
                    invoices_created += 1

                    logger.info(
                        "auto_renew_invoice_created",
                        username=username,
                        amount=amount,
                        currency=currency,
                        expires_at=expire_at,
                    )
                except Exception as e:
                    logger.exception("auto_renew_failed", username=username, error=str(e))

    except Exception as e:
        logger.exception("auto_renew_task_failed", error=str(e))
        raise

    logger.info("auto_renew_complete", users_checked=users_checked, invoices_created=invoices_created)
    return {"users_checked": users_checked, "invoices_created": invoices_created}
