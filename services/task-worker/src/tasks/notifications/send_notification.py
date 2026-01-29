"""Send a single notification on-demand via Telegram."""

from typing import Any, cast

import structlog

from src.broker import broker
from src.services.telegram_client import TelegramClient

logger = structlog.get_logger(__name__)


@broker.task(task_name="send_notification", queue="notifications")
async def send_notification(
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    notification_type: str | None = None,
) -> dict:
    """Send a single Telegram notification on-demand."""
    logger.info(
        "sending_notification",
        chat_id=chat_id,
        notification_type=notification_type,
        text_length=len(text),
    )
    async with TelegramClient() as tg:
        result = await tg.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    logger.info("notification_sent", chat_id=chat_id, message_id=result.get("message_id"))
    return result


send_notification = cast(Any, send_notification).with_labels(retry_policy="notifications_on_demand")
