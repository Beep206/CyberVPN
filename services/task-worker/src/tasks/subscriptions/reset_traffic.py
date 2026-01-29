"""Monthly traffic counter reset."""

import structlog

from src.broker import broker
from src.services.remnawave_client import RemnawaveClient
from src.services.telegram_client import TelegramClient
from src.utils.formatting import traffic_reset

logger = structlog.get_logger(__name__)


@broker.task(task_name="reset_monthly_traffic", queue="subscriptions")
async def reset_monthly_traffic() -> dict:
    """Reset traffic counters for all active users."""
    reset_count = 0

    async with RemnawaveClient() as rw:
        users = await rw.get_users()
        active_users = [u for u in users if u.get("status") == "active"]

    async with RemnawaveClient() as rw, TelegramClient() as tg:
        batch_size = 100
        for i in range(0, len(active_users), batch_size):
            batch = active_users[i : i + batch_size]
            for user in batch:
                user_uuid = user.get("uuid", "")
                username = user.get("username", "unknown")
                try:
                    await rw.reset_user_traffic(user_uuid)
                    reset_count += 1

                    telegram_id = user.get("telegramId")
                    if telegram_id:
                        msg = traffic_reset(username, user.get("planName", ""))
                        try:
                            await tg.send_message(chat_id=int(telegram_id), text=msg)
                        except Exception:
                            pass
                except Exception as e:
                    logger.error("traffic_reset_failed", user=username, error=str(e))

    logger.info("monthly_traffic_reset", count=reset_count)
    return {"reset": reset_count}
