"""Retry failed/unprocessed valid webhooks."""

from datetime import datetime, timedelta, timezone
import re

import structlog
from sqlalchemy import select

from src.broker import broker
from src.database.session import get_session_factory
from src.models.webhook_log import WebhookLogModel
from src.tasks.payments.process_completion import process_payment_completion

logger = structlog.get_logger(__name__)

MAX_ATTEMPTS = 3


def _parse_attempts(error_message: str | None) -> int:
    if not error_message:
        return 0
    match = re.search(r"attempt=(\d+)", error_message)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except (ValueError, TypeError):
        return 0


def _format_error(attempts: int, reason: str) -> str:
    return f"attempt={attempts}; {reason}"[:500]


@broker.task(task_name="retry_failed_webhooks", queue="payments")
async def retry_failed_webhooks() -> dict:
    """Reprocess valid but unprocessed webhook entries."""
    factory = get_session_factory()
    retried = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    async with factory() as session:
        stmt = (
            select(WebhookLogModel)
            .where(WebhookLogModel.is_valid == True)  # noqa: E712
            .where(WebhookLogModel.processed_at.is_(None))
            .where(WebhookLogModel.created_at >= cutoff)
            .limit(50)
        )
        result = await session.execute(stmt)
        webhooks = result.scalars().all()

        for webhook in webhooks:
            payload = webhook.payload or {}
            payment_id = payload.get("payment_id")
            attempts = _parse_attempts(webhook.error_message)

            if attempts >= MAX_ATTEMPTS:
                webhook.processed_at = datetime.now(timezone.utc)
                webhook.error_message = _format_error(attempts, "max_attempts_reached")
                session.add(webhook)
                await session.commit()
                continue

            if not payment_id:
                attempts += 1
                webhook.error_message = _format_error(attempts, "missing_payment_id")
                if attempts >= MAX_ATTEMPTS:
                    webhook.processed_at = datetime.now(timezone.utc)
                session.add(webhook)
                await session.commit()
                continue

            try:
                await process_payment_completion.kiq(payment_id=payment_id)
                retried += 1
                webhook.processed_at = datetime.now(timezone.utc)
                webhook.error_message = None
                session.add(webhook)
                await session.commit()
            except Exception as exc:
                attempts += 1
                webhook.error_message = _format_error(attempts, str(exc))
                if attempts >= MAX_ATTEMPTS:
                    webhook.processed_at = datetime.now(timezone.utc)
                session.add(webhook)
                await session.commit()

    logger.info("webhooks_retried", count=retried)
    return {"retried": retried}
