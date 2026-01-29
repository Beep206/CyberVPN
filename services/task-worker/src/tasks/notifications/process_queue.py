"""Process notification queue — picks up pending notifications and sends via Telegram."""

from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select, update

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.models.notification_queue import NotificationQueueModel
from src.services.telegram_client import TelegramAPIError, TelegramClient
from src.utils.constants import STATUS_FAILED, STATUS_PENDING, STATUS_PROCESSING, STATUS_SENT

logger = structlog.get_logger(__name__)


@broker.task(task_name="process_notification_queue", queue="notifications")
async def process_notification_queue() -> dict:
    """Process pending notifications from the queue.

    Fetches pending notifications in batches, marks as processing,
    sends via Telegram, then updates status to sent/failed.
    """
    settings = get_settings()
    batch_size = settings.notification_batch_size
    max_retries = settings.notification_max_retries
    factory = get_session_factory()

    sent_count = 0
    failed_count = 0

    async with factory() as session:
        # Fetch pending notifications
        stmt = (
            select(NotificationQueueModel)
            .where(NotificationQueueModel.status == STATUS_PENDING)
            .where(NotificationQueueModel.attempts < max_retries)
            .where(NotificationQueueModel.scheduled_at <= func.now())
            .order_by(NotificationQueueModel.scheduled_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        notifications = result.scalars().all()

        if not notifications:
            return {"sent": 0, "failed": 0, "message": "No pending notifications"}

        logger.info("processing_notification_batch", count=len(notifications))

        # Mark as processing
        notification_ids = [n.id for n in notifications]
        await session.execute(
            update(NotificationQueueModel)
            .where(NotificationQueueModel.id.in_(notification_ids))
            .values(status=STATUS_PROCESSING)
        )
        await session.commit()

    # Send notifications via Telegram
    async with TelegramClient() as tg:
        for notification in notifications:
            async with factory() as session:
                try:
                    await tg.send_message(
                        chat_id=notification.telegram_id,
                        text=notification.message,
                    )
                    notification.status = STATUS_SENT
                    notification.sent_at = datetime.now(timezone.utc)
                    sent_count += 1
                except TelegramAPIError as e:
                    next_attempts = notification.attempts + 1
                    notification.attempts = next_attempts
                    notification.error_message = str(e)[:500]
                    notification.status = STATUS_FAILED if next_attempts >= max_retries else STATUS_PENDING
                    failed_count += 1
                    logger.warning(
                        "notification_send_failed",
                        notification_id=str(notification.id),
                        attempts=next_attempts,
                        error=str(e),
                    )

                    if next_attempts >= max_retries:
                        alert_text = (
                            "Notification permanently failed\n"
                            f"Notification ID: {notification.id}\n"
                            f"Telegram ID: {notification.telegram_id}\n"
                            f"Error: {notification.error_message}"
                        )
                        try:
                            await tg.send_admin_alert(alert_text, severity="critical")
                        except Exception as alert_error:
                            logger.warning(
                                "notification_failure_alert_failed",
                                notification_id=str(notification.id),
                                error=str(alert_error),
                            )

                session.add(notification)
                await session.commit()

    logger.info("notification_batch_complete", sent=sent_count, failed=failed_count)
    return {"sent": sent_count, "failed": failed_count}
