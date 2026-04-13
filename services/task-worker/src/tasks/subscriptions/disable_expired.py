"""Disable expired user subscriptions."""

from contextlib import suppress
from datetime import UTC, datetime

import structlog

from src.broker import broker
from src.services.remnawave_client import RemnawaveClient
from src.services.telegram_client import TelegramClient
from src.utils.formatting import subscription_expired

logger = structlog.get_logger(__name__)


@broker.task(task_name="disable_expired_users", queue="subscriptions")
async def disable_expired_users() -> dict:
    """Find and disable users whose subscriptions have expired."""
    disabled_count = 0

    async with RemnawaveClient() as rw:
        users = await rw.get_users()

    expired_users = []
    for user in users:
        expire_at = user.get("expire_at")
        if not expire_at:
            continue
        try:
            exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
            if exp_dt < datetime.now(UTC) and user.get("status") != "disabled":
                expired_users.append(user)
        except (ValueError, TypeError):
            continue

    if not expired_users:
        return {"disabled": 0}

    async with RemnawaveClient() as rw, TelegramClient() as tg:
        for user in expired_users:
            user_uuid = user.get("uuid", "")
            username = user.get("username", "unknown")
            try:
                await rw.disable_user(user_uuid)
                disabled_count += 1

                telegram_id = user.get("telegram_id")
                if telegram_id:
                    msg = subscription_expired(username, user.get("expire_at", ""))
                    with suppress(Exception):
                        await tg.send_message(chat_id=int(telegram_id), text=msg)
            except Exception as e:
                logger.error("disable_user_failed", user=username, error=str(e))

    logger.info("expired_users_disabled", count=disabled_count)
    return {"disabled": disabled_count}
