"""Bulk user management operations."""

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.cache_service import CacheService
from src.services.redis_client import get_redis_client
from src.services.remnawave_client import RemnawaveClient
from src.services.sse_publisher import publish_event
from src.services.telegram_client import TelegramClient
from src.utils.constants import BULK_PROGRESS_KEY
from src.utils.formatting import bulk_operation_complete

logger = structlog.get_logger(__name__)


@broker.task(task_name="bulk_disable_users", queue="bulk")
async def bulk_disable_users(user_uuids: list[str], initiated_by: str = "system") -> dict:
    """Disable multiple users in batches with progress tracking."""
    settings = get_settings()
    batch_size = settings.bulk_batch_size
    redis = get_redis_client()
    cache = CacheService(redis)
    total = len(user_uuids)
    processed = 0
    failed = 0
    job_id = f"disable_{initiated_by}_{total}"

    try:
        async with RemnawaveClient() as rw:
            for i in range(0, total, batch_size):
                batch = user_uuids[i : i + batch_size]
                for uuid in batch:
                    try:
                        await rw.disable_user(uuid)
                        processed += 1
                    except Exception as e:
                        failed += 1
                        logger.warning("bulk_disable_failed", user_uuid=uuid, error=str(e))

                # Update progress in Redis
                progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
                await cache.set(progress_key, {"processed": processed, "failed": failed, "total": total}, ttl=3600)

                try:
                    await publish_event(
                        "bulk.progress",
                        {
                            "job_id": job_id,
                            "operation": "bulk_disable_users",
                            "processed": processed,
                            "failed": failed,
                            "total": total,
                        },
                    )
                except Exception:
                    logger.warning("bulk_progress_sse_failed", job_id=job_id)

        # Send completion notification
        alert = bulk_operation_complete("bulk_disable_users", total, processed, failed, initiated_by)
        async with TelegramClient() as tg:
            await tg.send_admin_alert(alert, severity="info" if failed == 0 else "warning")
        try:
            await publish_event(
                "bulk.completed",
                {
                    "job_id": job_id,
                    "operation": "bulk_disable_users",
                    "processed": processed,
                    "failed": failed,
                    "total": total,
                },
            )
        except Exception:
            logger.warning("bulk_complete_sse_failed", job_id=job_id)
    finally:
        await redis.aclose()

    logger.info("bulk_disable_complete", total=total, processed=processed, failed=failed)
    return {"total": total, "processed": processed, "failed": failed}


@broker.task(task_name="bulk_enable_users", queue="bulk")
async def bulk_enable_users(user_uuids: list[str], initiated_by: str = "system") -> dict:
    """Enable multiple users in batches with progress tracking."""
    settings = get_settings()
    batch_size = settings.bulk_batch_size
    redis = get_redis_client()
    cache = CacheService(redis)
    total = len(user_uuids)
    processed = 0
    failed = 0
    job_id = f"enable_{initiated_by}_{total}"

    try:
        async with RemnawaveClient() as rw:
            for i in range(0, total, batch_size):
                batch = user_uuids[i : i + batch_size]
                for uuid in batch:
                    try:
                        await rw.enable_user(uuid)
                        processed += 1
                    except Exception as e:
                        failed += 1
                        logger.warning("bulk_enable_failed", user_uuid=uuid, error=str(e))

                progress_key = BULK_PROGRESS_KEY.format(job_id=job_id)
                await cache.set(progress_key, {"processed": processed, "failed": failed, "total": total}, ttl=3600)

                try:
                    await publish_event(
                        "bulk.progress",
                        {
                            "job_id": job_id,
                            "operation": "bulk_enable_users",
                            "processed": processed,
                            "failed": failed,
                            "total": total,
                        },
                    )
                except Exception:
                    logger.warning("bulk_progress_sse_failed", job_id=job_id)

        alert = bulk_operation_complete("bulk_enable_users", total, processed, failed, initiated_by)
        async with TelegramClient() as tg:
            await tg.send_admin_alert(alert, severity="info" if failed == 0 else "warning")
        try:
            await publish_event(
                "bulk.completed",
                {
                    "job_id": job_id,
                    "operation": "bulk_enable_users",
                    "processed": processed,
                    "failed": failed,
                    "total": total,
                },
            )
        except Exception:
            logger.warning("bulk_complete_sse_failed", job_id=job_id)
    finally:
        await redis.aclose()

    logger.info("bulk_enable_complete", total=total, processed=processed, failed=failed)
    return {"total": total, "processed": processed, "failed": failed}
