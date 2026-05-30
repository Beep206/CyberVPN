"""Queue support ticket Telegram notifications."""

from datetime import datetime

import structlog

from src.broker import broker
from src.database.session import get_session_factory
from src.services.redis_client import get_redis_client
from src.tasks.notifications.support_ticket_contract import (
    SUPPORT_TICKET_IDEMPOTENCY_TTL_SECONDS,
    SupportTicketNotificationEventType,
    build_support_ticket_telegram_notification,
)

logger = structlog.get_logger(__name__)


@broker.task(
    task_name="queue_support_ticket_notification",
    queue="notifications",
    retry_policy="notifications",
)
async def queue_support_ticket_notification(
    *,
    telegram_id: int | None,
    ticket_event_id: str,
    ticket_public_id: str,
    event_type: SupportTicketNotificationEventType,
    status: str,
    category: str,
    support_url: str = "",
    enabled: bool = True,
    scheduled_at: datetime | None = None,
) -> dict[str, object]:
    """Queue a safe Telegram notification for a support ticket event."""
    notification = build_support_ticket_telegram_notification(
        telegram_id=telegram_id,
        ticket_event_id=ticket_event_id,
        ticket_public_id=ticket_public_id,
        event_type=event_type,
        status=status,
        category=category,
        support_url=support_url,
        enabled=enabled,
        scheduled_at=scheduled_at,
    )
    if notification is None:
        logger.info(
            "support_ticket_notification_not_queued",
            reason="disabled_or_unlinked_telegram",
            event_type=event_type,
        )
        return {"queued": 0, "skipped": True, "reason": "disabled_or_unlinked_telegram"}

    redis = get_redis_client()
    acquired = False
    try:
        acquired = bool(
            await redis.set(
                notification.idempotency_key,
                "1",
                nx=True,
                ex=SUPPORT_TICKET_IDEMPOTENCY_TTL_SECONDS,
            )
        )
        if not acquired:
            logger.info(
                "support_ticket_notification_duplicate_skipped",
                ticket_public_id=notification.ticket_public_id,
                event_type=notification.event_type,
                key_suffix=notification.idempotency_key[-12:],
            )
            return {"queued": 0, "skipped": True, "reason": "idempotent_duplicate"}

        factory = get_session_factory()
        async with factory() as session:
            session.add(notification.to_queue_model())
            await session.commit()

        logger.info(
            "support_ticket_notification_queued",
            ticket_public_id=notification.ticket_public_id,
            event_type=notification.event_type,
            status=notification.status,
        )
        return {
            "queued": 1,
            "skipped": False,
            "notification_type": "support_ticket_update",
            "ticket_public_id": notification.ticket_public_id,
            "event_type": notification.event_type,
        }
    except Exception:
        if acquired:
            await redis.delete(notification.idempotency_key)
        logger.exception(
            "support_ticket_notification_queue_failed",
            ticket_public_id=notification.ticket_public_id,
            event_type=notification.event_type,
        )
        raise
    finally:
        await redis.aclose()
