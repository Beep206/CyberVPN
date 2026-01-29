"""Broadcast message to multiple Telegram users."""

import json
from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.database.session import get_session_factory
from src.models.notification_queue import NotificationQueueModel
from src.services.redis_client import get_redis_client
from src.utils.constants import BULK_PROGRESS_KEY, STATUS_PENDING

logger = structlog.get_logger(__name__)


@broker.task(task_name="broadcast_message", queue="notifications")
async def broadcast_message(
    telegram_ids: list[int],
    text: str,
    notification_type: str = "broadcast",
    job_id: str | None = None,
) -> dict:
    """Queue broadcast notifications for deferred delivery.

    Inserts notification records into the notification_queue table for processing
    by the queue worker. Tracks progress in Redis using BULK_PROGRESS_KEY.
    """
    if not telegram_ids:
        return {"queued": 0, "job_id": job_id}

    if not job_id:
        import uuid

        job_id = str(uuid.uuid4())

    session_factory = get_session_factory()
    redis = get_redis_client()
    queued = 0

    logger.info("broadcast_queue_started", recipient_count=len(telegram_ids), job_id=job_id)

    try:
        async with session_factory() as session:
            scheduled_at = datetime.now(timezone.utc)
            batch_size = 500

            for i in range(0, len(telegram_ids), batch_size):
                batch = telegram_ids[i : i + batch_size]
                notifications = [
                    NotificationQueueModel(
                        telegram_id=telegram_id,
                        message=text,
                        notification_type=notification_type,
                        status=STATUS_PENDING,
                        scheduled_at=scheduled_at,
                    )
                    for telegram_id in batch
                ]

                session.add_all(notifications)
                await session.commit()

                queued += len(batch)
                progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
                progress = {
                    "total": len(telegram_ids),
                    "queued": queued,
                    "status": "in_progress" if queued < len(telegram_ids) else "completed",
                }
                await redis.set(progress_key, json.dumps(progress), ex=86400)

    except Exception as e:
        logger.exception("broadcast_queue_failed", error=str(e), job_id=job_id)
        progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
        progress = {
            "total": len(telegram_ids),
            "queued": queued,
            "status": "failed",
            "error": str(e),
        }
        await redis.set(progress_key, json.dumps(progress), ex=86400)
        raise
    finally:
        await redis.aclose()

    logger.info("broadcast_queue_complete", queued=queued, job_id=job_id)
    return {"queued": queued, "job_id": job_id}
