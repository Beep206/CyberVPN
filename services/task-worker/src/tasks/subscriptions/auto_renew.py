"""Create tracked auto-renew invoices through the CyberVPN billing boundary."""

from datetime import UTC, datetime, timedelta

import structlog

from src.broker import broker
from src.services.backend_api_client import (
    BackendAPIAutoRenewPermanentError,
    BackendAPIAutoRenewTransientError,
    BackendAPIClient,
)
from src.services.remnawave_client import RemnawaveClient

logger = structlog.get_logger(__name__)
AUTO_RENEW_ELIGIBILITY_BATCH_SIZE = 1000
AUTO_RENEW_PAST_WINDOW = timedelta(hours=2)


@broker.task(task_name="auto_renew_subscriptions", queue="subscriptions")
async def auto_renew_subscriptions() -> dict:
    """Create invoices for backend-authorized users expiring within one hour.

    Remnawave remains authoritative for the numeric user identity and current
    expiry. CyberVPN backend remains authoritative for customer mapping,
    billing plan, price, invoice persistence, and provider reconciliation.

    Returns:
        Dictionary with invoices_created count
    """
    invoices_created = 0
    invoices_reused = 0
    notifications_queued = 0
    failures = 0
    users_checked = 0

    try:
        async with RemnawaveClient() as rw:
            users = await rw.get_users()

        now = datetime.now(UTC)
        renewal_threshold = now + timedelta(hours=1)
        oldest_eligible_expiry = now - AUTO_RENEW_PAST_WINDOW
        candidates: dict[int, tuple[datetime, str]] = {}
        for user in users:
            users_checked += 1
            expire_at = user.get("expire_at")
            if not isinstance(expire_at, str) or not expire_at:
                continue
            user_id = user.get("id")
            if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
                logger.warning("invalid_auto_renew_user_id")
                continue
            try:
                exp_dt = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                if exp_dt.tzinfo is None or exp_dt.utcoffset() is None:
                    raise ValueError("expiration timestamp must include a timezone")
                exp_dt = exp_dt.astimezone(UTC)
            except (ValueError, TypeError):
                logger.warning("invalid_auto_renew_expire_date", remnawave_user_id=user_id)
                continue
            if exp_dt < oldest_eligible_expiry or exp_dt > renewal_threshold:
                continue
            if user_id in candidates:
                logger.warning("duplicate_auto_renew_user_id", remnawave_user_id=user_id)
                continue
            candidates[user_id] = (exp_dt, expire_at)

        async with BackendAPIClient() as backend:
            candidate_ids = list(candidates)
            eligible_user_ids: set[int] = set()
            for offset in range(0, len(candidate_ids), AUTO_RENEW_ELIGIBILITY_BATCH_SIZE):
                batch = candidate_ids[offset : offset + AUTO_RENEW_ELIGIBILITY_BATCH_SIZE]
                eligible_user_ids.update(await backend.filter_remnawave_auto_renew_eligible(batch))

            for user_id, (exp_dt, expire_at) in candidates.items():
                if user_id not in eligible_user_ids:
                    continue

                try:
                    invoice = await backend.create_remnawave_auto_renew_invoice(
                        remnawave_user_id=user_id,
                        expected_expire_at=exp_dt,
                    )
                    if invoice.notification_status == "queued":
                        notifications_queued += 1
                    if invoice.reused:
                        invoices_reused += 1
                    else:
                        invoices_created += 1

                    logger.info(
                        "auto_renew_invoice_created",
                        remnawave_user_id=user_id,
                        payment_id=invoice.payment_id,
                        reused=invoice.reused,
                        expires_at=expire_at,
                    )
                except BackendAPIAutoRenewPermanentError as exc:
                    failures += 1
                    logger.warning(
                        "auto_renew_permanently_rejected",
                        remnawave_user_id=user_id,
                        error_type=type(exc).__name__,
                    )
                except BackendAPIAutoRenewTransientError as exc:
                    failures += 1
                    logger.warning(
                        "auto_renew_transient_failure",
                        remnawave_user_id=user_id,
                        error_type=type(exc).__name__,
                    )
                except Exception as exc:
                    failures += 1
                    logger.exception(
                        "auto_renew_failed",
                        remnawave_user_id=user_id,
                        error_type=type(exc).__name__,
                    )

    except Exception as exc:
        logger.exception("auto_renew_task_failed", error_type=type(exc).__name__)
        raise

    logger.info(
        "auto_renew_complete",
        users_checked=users_checked,
        invoices_created=invoices_created,
        invoices_reused=invoices_reused,
        notifications_queued=notifications_queued,
        failures=failures,
    )
    return {
        "users_checked": users_checked,
        "invoices_created": invoices_created,
        "invoices_reused": invoices_reused,
        "notifications_queued": notifications_queued,
        "failures": failures,
    }
