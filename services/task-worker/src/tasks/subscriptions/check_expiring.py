"""Check for expiring subscriptions and send reminders."""

from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.database.session import get_session_factory
from src.models.notification_queue import NotificationQueueModel
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.utils.constants import NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING, STATUS_PENDING, SUB_REMINDER_KEY
from src.utils.formatting import subscription_expiring

logger = structlog.get_logger(__name__)
REMINDER_BRACKETS = [
    ("6h", 6 * 60 * 60),
    ("24h", 24 * 60 * 60),
    ("3d", 3 * 24 * 60 * 60),
    ("7d", 7 * 24 * 60 * 60),
]


@broker.task(task_name="check_expiring_subscriptions", queue="subscriptions")
async def check_expiring_subscriptions() -> dict:
    """Find users with expiring subscriptions and send one-time reminders."""
    redis = get_redis_client()
    cache = CacheService(redis)
    session_factory = get_session_factory()
    reminders_sent = 0
    pending_notifications: list[NotificationQueueModel] = []
    reminder_keys: list[tuple[str, int]] = []

    try:
        async with RemnawaveClient() as rw:
            users = await rw.get_users()

        now = datetime.now(timezone.utc)

        for user in users:
            if user.get("status") != "active":
                continue

            expire_at = user.get("expiresAt")
            if not expire_at:
                continue

            try:
                exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            time_left = (exp_dt - now).total_seconds()
            if time_left <= 0:
                continue

            user_uuid = user.get("uuid", "")
            username = user.get("username", "unknown")
            telegram_id = user.get("telegramId")

            if not telegram_id or not user_uuid:
                continue

            selected_bracket = None
            for bracket_label, bracket_seconds in REMINDER_BRACKETS:
                if time_left <= bracket_seconds:
                    selected_bracket = (bracket_label, bracket_seconds)
                    break

            if not selected_bracket:
                continue

            bracket_label, bracket_seconds = selected_bracket
            reminder_key = SUB_REMINDER_KEY.format(user_uuid=user_uuid, bracket=bracket_label)
            if await cache.exists(reminder_key):
                continue

            days_left = max(1, int(time_left // 86400))
            msg = subscription_expiring(username, days_left, expire_at)
            pending_notifications.append(
                NotificationQueueModel(
                    telegram_id=int(telegram_id),
                    message=msg,
                    notification_type=NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRING,
                    status=STATUS_PENDING,
                    scheduled_at=now,
                )
            )
            reminder_keys.append((reminder_key, int(bracket_seconds)))

        if pending_notifications:
            async with session_factory() as session:
                session.add_all(pending_notifications)
                await session.commit()
            for reminder_key, ttl_seconds in reminder_keys:
                await cache.set(reminder_key, {"sent": True}, ttl=ttl_seconds)
            reminders_sent = len(pending_notifications)
    finally:
        await redis.aclose()

    logger.info("expiring_subscriptions_checked", reminders_sent=reminders_sent)
    return {"reminders_sent": reminders_sent}
