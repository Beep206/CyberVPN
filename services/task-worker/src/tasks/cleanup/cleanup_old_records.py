"""Cleanup old database records per retention policy."""

import structlog
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.models.audit_log import AuditLogModel
from src.models.webhook_log import WebhookLogModel

logger = structlog.get_logger(__name__)


@broker.task(task_name="cleanup_old_records", queue="cleanup")
async def cleanup_old_records() -> dict:
    """Delete audit logs and webhook logs older than retention period."""
    settings = get_settings()
    factory = get_session_factory()
    now = datetime.now(timezone.utc)

    audit_cutoff = now - timedelta(days=settings.cleanup_audit_retention_days)
    webhook_cutoff = now - timedelta(days=settings.cleanup_webhook_retention_days)

    async with factory() as session:
        # Delete old audit logs
        audit_stmt = delete(AuditLogModel).where(AuditLogModel.created_at < audit_cutoff)
        audit_result = await session.execute(audit_stmt)
        audit_deleted = audit_result.rowcount

        # Delete old webhook logs
        webhook_stmt = delete(WebhookLogModel).where(WebhookLogModel.created_at < webhook_cutoff)
        webhook_result = await session.execute(webhook_stmt)
        webhook_deleted = webhook_result.rowcount

        await session.commit()

    logger.info("cleanup_complete", audit_deleted=audit_deleted, webhook_deleted=webhook_deleted)
    return {"audit_deleted": audit_deleted, "webhook_deleted": webhook_deleted}
