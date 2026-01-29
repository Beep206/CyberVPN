"""Delete old webhook logs older than retention period."""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.models.webhook_log import WebhookLogModel

logger = structlog.get_logger(__name__)


@broker.task(task_name="cleanup_webhook_logs", queue="cleanup")
async def cleanup_webhook_logs() -> dict:
    """Delete webhook logs older than 30 days in batches.

    Removes webhook log entries where created_at is older than the configured
    retention period (default 30 days). Processes in batches of 1000 to
    avoid long-running transactions.
    """
    settings = get_settings()
    factory = get_session_factory()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.cleanup_webhook_retention_days)
    total_deleted = 0
    batch_size = 1000

    async with factory() as session:
        while True:
            # Delete in batches
            stmt = (
                delete(WebhookLogModel)
                .where(WebhookLogModel.created_at < cutoff)
                .execution_options(synchronize_session=False)
            )

            result = await session.execute(stmt)
            deleted_count = result.rowcount
            await session.commit()

            total_deleted += deleted_count

            # Stop when no more rows to delete
            if deleted_count == 0 or deleted_count < batch_size:
                break

    logger.info(
        "webhook_logs_cleanup_complete",
        deleted=total_deleted,
        retention_days=settings.cleanup_webhook_retention_days,
    )
    return {"deleted": total_deleted, "retention_days": settings.cleanup_webhook_retention_days}
