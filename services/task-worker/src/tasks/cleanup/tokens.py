"""Cleanup expired and revoked refresh tokens from database."""

from datetime import datetime, timezone

import structlog
from sqlalchemy import delete, or_, select

from src.broker import broker
from src.database.session import get_session_factory
from src.models.refresh_token import RefreshTokenModel

logger = structlog.get_logger(__name__)


@broker.task(task_name="cleanup_expired_tokens", queue="cleanup")
async def cleanup_expired_tokens() -> dict:
    """Delete expired and revoked refresh tokens from PostgreSQL in batches.

    This task removes:
    - Tokens where expires_at < now()
    - Tokens where revoked_at IS NOT NULL

    Processes deletions in batches of 1000 to avoid long-running transactions.
    """
    factory = get_session_factory()
    now = datetime.now(timezone.utc)
    total_deleted = 0
    batch_size = 1000

    async with factory() as session:
        while True:
            # Delete in batches using a subquery for IDs
            ids_subquery = (
                select(RefreshTokenModel.id)
                .where(
                    or_(
                        RefreshTokenModel.expires_at < now,
                        RefreshTokenModel.revoked_at.is_not(None),
                    )
                )
                .limit(batch_size)
            )

            stmt = delete(RefreshTokenModel).where(RefreshTokenModel.id.in_(ids_subquery))

            result = await session.execute(stmt)
            deleted_count = result.rowcount
            await session.commit()

            total_deleted += deleted_count

            # Stop when no more rows to delete
            if deleted_count == 0 or deleted_count < batch_size:
                break

    logger.info("tokens_cleanup_complete", deleted=total_deleted)
    return {"deleted": total_deleted}
