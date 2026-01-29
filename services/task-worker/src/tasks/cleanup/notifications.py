"""Cleanup sent and failed notifications older than 7 days."""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete

from src.broker import broker
from src.database.session import get_session_factory
from src.models.notification_queue import NotificationQueueModel

logger = structlog.get_logger(__name__)


@broker.task(task_name="cleanup_notifications", queue="cleanup")
async def cleanup_notifications() -> dict:
    """Delete sent and failed notifications older than 7 days in batches.

    Removes notification queue entries where:
    - status is 'sent' OR 'failed'
    - created_at is older than 7 days

    Processes in batches of 1000 to avoid long-running transactions.
    """
    factory = get_session_factory()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    total_deleted = 0
    batch_size = 1000

    async with factory() as session:
        while True:
            # Delete in batches
            stmt = (
                delete(NotificationQueueModel)
                .where(
                    NotificationQueueModel.status.in_(["sent", "failed"]),
                    NotificationQueueModel.created_at < cutoff,
                )
                .execution_options(synchronize_session=False)
            )

            result = await session.execute(stmt)
            deleted_count = result.rowcount
            await session.commit()

            total_deleted += deleted_count

            # Stop when no more rows to delete
            if deleted_count == 0 or deleted_count < batch_size:
                break

    logger.info("notifications_cleanup_complete", deleted=total_deleted)
    return {"deleted": total_deleted}
