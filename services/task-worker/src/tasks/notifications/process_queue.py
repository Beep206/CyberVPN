"""Process notification queue - picks up pending notifications and sends via Telegram."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.models.customer_growth_notification_delivery import (
    CustomerGrowthNotificationDeliveryModel,
)
from src.models.customer_growth_notification_delivery_event import (
    CustomerGrowthNotificationDeliveryEventModel,
)
from src.models.notification_queue import NotificationQueueModel
from src.services.telegram_client import TelegramAPIError, TelegramClient
from src.utils.constants import STATUS_FAILED, STATUS_PENDING, STATUS_PROCESSING, STATUS_SENT

logger = structlog.get_logger(__name__)

_AUTO_RENEW_NOTIFICATION_PREFIX = "auto_renew:"
_UNBOUND_AUTO_RENEW_NOTIFICATION_TYPES = frozenset({"subscription:auto_renew_invoice"})
_CANONICAL_RECIPIENT_MISMATCH = "canonical_recipient_mismatch"
_CANONICAL_RECIPIENT_VALIDATION_UNAVAILABLE = "canonical_recipient_validation_unavailable"


def _auto_renew_customer_id(notification_type: object) -> UUID | None:
    """Return the local subject bound to an auto-renew notification."""

    if notification_type in _UNBOUND_AUTO_RENEW_NOTIFICATION_TYPES:
        raise ValueError("unbound auto-renew notification subject")
    if not isinstance(notification_type, str) or not notification_type.startswith(_AUTO_RENEW_NOTIFICATION_PREFIX):
        return None
    value = notification_type.removeprefix(_AUTO_RENEW_NOTIFICATION_PREFIX)
    try:
        return UUID(value)
    except ValueError as exc:
        # Never treat a malformed auto-renew record as an unbound legacy
        # notification; that would bypass the canonical recipient check.
        raise ValueError("invalid auto-renew notification subject") from exc


async def _is_current_canonical_recipient(
    session: AsyncSession,
    *,
    notification_type: object,
    telegram_id: object,
) -> bool:
    """Fail closed unless the queued chat is still owned by the active customer."""

    customer_id = _auto_renew_customer_id(notification_type)
    if customer_id is None:
        return True
    if isinstance(telegram_id, bool) or not isinstance(telegram_id, int) or telegram_id <= 0:
        return False
    result = await session.execute(
        text(
            """
            SELECT telegram_id, is_active
            FROM mobile_users
            WHERE id = :customer_id
            """
        ),
        {"customer_id": customer_id},
    )
    current = result.mappings().one_or_none()
    return (
        current is not None
        and bool(current["is_active"])
        and not isinstance(current["telegram_id"], bool)
        and isinstance(current["telegram_id"], int)
        and current["telegram_id"] == telegram_id
    )


def _record_delivery_event(
    session,
    *,
    delivery_id,
    notification_queue_id,
    delivery_status: str,
    event_type: str,
    reason_code: str | None = None,
    event_payload: dict | None = None,
) -> None:
    session.add(
        CustomerGrowthNotificationDeliveryEventModel(
            delivery_id=delivery_id,
            event_type=event_type,
            delivery_status=delivery_status,
            reason_code=reason_code,
            event_payload=dict(event_payload or {}),
            notification_queue_id=notification_queue_id,
            occurred_at=datetime.now(UTC),
        )
    )


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
                delivery = None
                try:
                    recipient_is_current = await _is_current_canonical_recipient(
                        session,
                        notification_type=notification.notification_type,
                        telegram_id=notification.telegram_id,
                    )
                except (KeyError, TypeError, ValueError):
                    recipient_is_current = False
                except Exception as exc:
                    await session.rollback()
                    next_attempts = notification.attempts + 1
                    notification.attempts = next_attempts
                    notification.status = STATUS_FAILED if next_attempts >= max_retries else STATUS_PENDING
                    notification.error_message = _CANONICAL_RECIPIENT_VALIDATION_UNAVAILABLE
                    session.add(notification)
                    await session.commit()
                    failed_count += 1
                    logger.warning(
                        "canonical_recipient_validation_unavailable",
                        notification_id=str(notification.id),
                        error_type=type(exc).__name__,
                    )
                    continue

                if not recipient_is_current:
                    notification.attempts = max_retries
                    notification.status = STATUS_FAILED
                    notification.error_message = _CANONICAL_RECIPIENT_MISMATCH
                    session.add(notification)
                    await session.commit()
                    failed_count += 1
                    logger.warning(
                        "canonical_recipient_mismatch",
                        notification_id=str(notification.id),
                    )
                    continue

                try:
                    delivery_result = await session.execute(
                        select(CustomerGrowthNotificationDeliveryModel).where(
                            CustomerGrowthNotificationDeliveryModel.notification_queue_id == notification.id
                        )
                    )
                    delivery = delivery_result.scalars().first()
                    if delivery is not None:
                        _record_delivery_event(
                            session,
                            delivery_id=delivery.id,
                            notification_queue_id=notification.id,
                            delivery_status="processing",
                            event_type="telegram_processing_started",
                            event_payload={"channel": "telegram"},
                        )
                    await tg.send_message(
                        chat_id=notification.telegram_id,
                        text=notification.message,
                    )
                    notification.status = STATUS_SENT
                    notification.sent_at = datetime.now(UTC)
                    if delivery is not None:
                        delivery.delivery_status = "delivered"
                        delivery.delivered_at = notification.sent_at
                        delivery.status_reason = None
                        _record_delivery_event(
                            session,
                            delivery_id=delivery.id,
                            notification_queue_id=notification.id,
                            delivery_status="delivered",
                            event_type="telegram_delivered",
                            event_payload={"channel": "telegram"},
                        )
                    else:
                        await session.execute(
                            update(CustomerGrowthNotificationDeliveryModel)
                            .where(CustomerGrowthNotificationDeliveryModel.notification_queue_id == notification.id)
                            .values(
                                delivery_status="delivered",
                                delivered_at=notification.sent_at,
                                status_reason=None,
                            )
                        )
                    sent_count += 1
                except TelegramAPIError as e:
                    next_attempts = notification.attempts + 1
                    notification.attempts = next_attempts
                    notification.error_message = "telegram_delivery_failed"
                    notification.status = STATUS_FAILED if next_attempts >= max_retries else STATUS_PENDING
                    delivery_status = "failed" if next_attempts >= max_retries else "queued"
                    delivery_reason = (
                        "telegram_delivery_failed" if next_attempts >= max_retries else "telegram_retry_pending"
                    )
                    if delivery is None:
                        delivery_result = await session.execute(
                            select(CustomerGrowthNotificationDeliveryModel).where(
                                CustomerGrowthNotificationDeliveryModel.notification_queue_id == notification.id
                            )
                        )
                        delivery = delivery_result.scalars().first()
                    if delivery is not None:
                        delivery.delivery_status = delivery_status
                        delivery.delivered_at = None
                        delivery.status_reason = delivery_reason
                        _record_delivery_event(
                            session,
                            delivery_id=delivery.id,
                            notification_queue_id=notification.id,
                            delivery_status=delivery_status,
                            event_type=(
                                "telegram_failed" if next_attempts >= max_retries else "telegram_retry_scheduled"
                            ),
                            reason_code=delivery_reason,
                            event_payload={
                                "channel": "telegram",
                                "attempts": next_attempts,
                                "queue_error_message": notification.error_message,
                            },
                        )
                    else:
                        await session.execute(
                            update(CustomerGrowthNotificationDeliveryModel)
                            .where(CustomerGrowthNotificationDeliveryModel.notification_queue_id == notification.id)
                            .values(
                                delivery_status=delivery_status,
                                delivered_at=None,
                                status_reason=delivery_reason,
                            )
                        )
                    failed_count += 1
                    logger.warning(
                        "notification_send_failed",
                        notification_id=str(notification.id),
                        attempts=next_attempts,
                        error_type=type(e).__name__,
                    )

                    if next_attempts >= max_retries:
                        alert_text = (
                            "Notification permanently failed\n"
                            f"Notification ID: {notification.id}\n"
                            "Reason: telegram_delivery_failed"
                        )
                        try:
                            await tg.send_admin_alert(alert_text, severity="critical")
                        except Exception as alert_error:
                            logger.warning(
                                "notification_failure_alert_failed",
                                notification_id=str(notification.id),
                                error_type=type(alert_error).__name__,
                            )

                session.add(notification)
                await session.commit()

    logger.info("notification_batch_complete", sent=sent_count, failed=failed_count)
    return {"sent": sent_count, "failed": failed_count}
