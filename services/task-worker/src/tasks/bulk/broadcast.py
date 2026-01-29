"""Bulk broadcast via notification_queue table."""

import json
from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.database.session import get_session_factory
from src.models.notification_queue import NotificationQueueModel
from src.services.redis_client import get_redis_client
from src.services.sse_publisher import publish_event
from src.utils.constants import BULK_PROGRESS_KEY, STATUS_PENDING

logger = structlog.get_logger(__name__)


@broker.task(task_name="bulk_broadcast", queue="bulk")
async def bulk_broadcast(
    telegram_ids: list[int], message: str, notification_type: str = "broadcast", job_id: str | None = None
) -> dict:
    """Bulk broadcast via notification_queue table.

    Inserts batch of notifications into notification_queue for deferred processing
    by the notification_queue worker. Tracks progress in Redis.

    Args:
        telegram_ids: List of Telegram chat IDs to send to
        message: HTML-formatted message text
        notification_type: Type of notification (default: "broadcast")
        job_id: Optional job ID for progress tracking

    Returns:
        Dictionary with queued count and job_id
    """
    session_factory = get_session_factory()
    redis = get_redis_client()
    queued = 0

    if not job_id:
        import uuid

        job_id = str(uuid.uuid4())

    try:
        async with session_factory() as session:
            scheduled_at = datetime.now(timezone.utc)

            # Batch insert notifications
            batch_size = 500
            for i in range(0, len(telegram_ids), batch_size):
                batch = telegram_ids[i : i + batch_size]

                notifications = [
                    NotificationQueueModel(
                        telegram_id=tid,
                        message=message,
                        notification_type=notification_type,
                        status=STATUS_PENDING,
                        scheduled_at=scheduled_at,
                    )
                    for tid in batch
                ]

                session.add_all(notifications)
                await session.commit()

                queued += len(batch)

                # Update progress in Redis
                progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
                progress = {
                    "total": len(telegram_ids),
                    "queued": queued,
                    "status": "in_progress" if queued < len(telegram_ids) else "completed",
                }
                await redis.set(progress_key, json.dumps(progress), ex=86400)  # 24h TTL

                try:
                    await publish_event(
                        "bulk.broadcast.progress",
                        {
                            "job_id": job_id,
                            "queued": queued,
                            "total": len(telegram_ids),
                            "status": progress["status"],
                        },
                    )
                except Exception:
                    logger.warning("bulk_broadcast_sse_failed", job_id=job_id)

                logger.debug("broadcast_batch_queued", batch_size=len(batch), total_queued=queued)

        logger.info("bulk_broadcast_queued", queued=queued, job_id=job_id)
        try:
            await publish_event(
                "bulk.broadcast.completed",
                {
                    "job_id": job_id,
                    "queued": queued,
                    "total": len(telegram_ids),
                },
            )
        except Exception:
            logger.warning("bulk_broadcast_sse_failed", job_id=job_id)

    except Exception as e:
        logger.exception("bulk_broadcast_failed", error=str(e), job_id=job_id)
        # Update progress with error
        progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
        progress = {"total": len(telegram_ids), "queued": queued, "status": "failed", "error": str(e)}
        await redis.set(progress_key, json.dumps(progress), ex=86400)
        raise
    finally:
        await redis.aclose()

    return {"queued": queued, "job_id": job_id}
