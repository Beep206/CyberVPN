"""Process planned customer growth email deliveries."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

import structlog
from sqlalchemy import func, select

from src.broker import broker
from src.config import get_settings
from src.database.session import get_session_factory
from src.metrics import (
    EMAIL_SEND_CONTEXT_DURATION,
    EMAIL_SEND_CONTEXT_TOTAL,
    EMAIL_SEND_DURATION,
    EMAIL_SEND_ERRORS,
    EMAIL_SEND_TOTAL,
)
from src.models.customer_growth_notification_delivery import (
    CustomerGrowthNotificationDeliveryModel,
)
from src.models.customer_growth_notification_delivery_event import (
    CustomerGrowthNotificationDeliveryEventModel,
)
from src.services.email import BrevoClient, ResendClient, SmtpClient

logger = structlog.get_logger(__name__)


def _classify_email_error(exc: Exception) -> str:
    error_name = type(exc).__name__.lower()
    if "timeout" in error_name:
        return "timeout"
    if "email_unavailable" in str(exc):
        return "email_unavailable"
    if any(keyword in error_name for keyword in ("connect", "socket", "network")):
        return "network_error"
    if any(keyword in error_name for keyword in ("http", "api", "smtp", "response", "status")):
        return "api_error"
    if "provider_unavailable" in str(exc):
        return "provider_unavailable"
    return "unknown"


def _normalize_locale(locale: str | None) -> str:
    if not locale:
        return "unknown"
    normalized = locale.strip()
    return normalized or "unknown"


def _build_cta_url(base_url: str, route_slug: str) -> str:
    normalized_route = route_slug.strip()
    if not normalized_route:
        return base_url
    if normalized_route.startswith("http://") or normalized_route.startswith("https://"):
        return normalized_route
    if not normalized_route.startswith("/"):
        normalized_route = f"/{normalized_route}"
    return f"{base_url}{normalized_route}"


def _record_delivery_event(
    session,
    *,
    delivery: CustomerGrowthNotificationDeliveryModel,
    event_type: str,
    reason_code: str | None = None,
    event_payload: dict | None = None,
) -> None:
    session.add(
        CustomerGrowthNotificationDeliveryEventModel(
            delivery_id=delivery.id,
            event_type=event_type,
            delivery_status=delivery.delivery_status,
            reason_code=reason_code if reason_code is not None else delivery.status_reason,
            event_payload=dict(event_payload or {}),
            notification_queue_id=delivery.notification_queue_id,
            occurred_at=datetime.now(UTC),
        )
    )


def _select_email_client():
    settings = get_settings()
    if settings.email_dev_mode:
        return SmtpClient, "smtp"

    resend_key = settings.resend_api_key.get_secret_value().strip() if settings.resend_api_key else ""
    if resend_key:
        return ResendClient, "resend"

    brevo_key = settings.brevo_api_key.get_secret_value().strip() if settings.brevo_api_key else ""
    if brevo_key:
        return BrevoClient, "brevo"

    raise RuntimeError("provider_unavailable")


@broker.task(
    task_name="process_growth_notification_deliveries",
    queue="email",
)
async def process_growth_notification_deliveries() -> dict:
    """Send planned growth email deliveries and persist final status."""
    settings = get_settings()
    batch_size = settings.notification_batch_size
    base_url = settings.magic_link_base_url.rstrip("/")
    factory = get_session_factory()
    sent_count = 0
    failed_count = 0

    async with factory() as session:
        stmt = (
            select(CustomerGrowthNotificationDeliveryModel)
            .where(CustomerGrowthNotificationDeliveryModel.delivery_channel == "email")
            .where(CustomerGrowthNotificationDeliveryModel.delivery_status == "planned")
            .where(CustomerGrowthNotificationDeliveryModel.planned_at <= func.now())
            .order_by(
                CustomerGrowthNotificationDeliveryModel.planned_at,
                CustomerGrowthNotificationDeliveryModel.created_at,
            )
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        deliveries = list(result.scalars().all())
        if not deliveries:
            return {"sent": 0, "failed": 0, "message": "No planned growth notification emails"}

        for delivery in deliveries:
            delivery.delivery_status = "processing"
            delivery.status_reason = None
            _record_delivery_event(
                session,
                delivery=delivery,
                event_type="email_processing_started",
                event_payload={"channel": "email"},
            )
        await session.commit()

        try:
            client_cls, provider = _select_email_client()
        except RuntimeError as exc:
            error_type = _classify_email_error(exc)
            for delivery in deliveries:
                locale = _normalize_locale(str((delivery.delivery_payload or {}).get("locale") or "en-EN"))
                delivery.delivery_status = "failed"
                delivery.status_reason = error_type
                delivery.delivered_at = None
                _record_delivery_event(
                    session,
                    delivery=delivery,
                    event_type="email_failed",
                    reason_code=error_type,
                    event_payload={"channel": "email", "provider": "unknown"},
                )
                EMAIL_SEND_TOTAL.labels(provider="unknown", email_type="notification", status="failed").inc()
                EMAIL_SEND_CONTEXT_TOTAL.labels(
                    channel="growth",
                    provider="unknown",
                    email_type="notification",
                    locale=locale,
                    status="failed",
                ).inc()
                EMAIL_SEND_ERRORS.labels(provider="unknown", error_type=error_type).inc()
                EMAIL_SEND_DURATION.labels(provider="unknown", email_type="notification").observe(0)
                EMAIL_SEND_CONTEXT_DURATION.labels(
                    channel="growth",
                    provider="unknown",
                    email_type="notification",
                    locale=locale,
                ).observe(0)
            await session.commit()
            failed_count = len(deliveries)
            logger.error("growth_notification_email_provider_unavailable")
            return {"sent": 0, "failed": len(deliveries), "message": "No email provider configured"}

        async with client_cls() as client:
            for delivery in deliveries:
                payload = dict(delivery.delivery_payload or {})
                recipient_email = str(payload.get("recipient_email") or "").strip()
                locale = _normalize_locale(str(payload.get("locale") or "en-EN"))
                route_slug = str(payload.get("route_slug") or "/referral")
                notes = [str(item) for item in list(payload.get("notes") or []) if str(item).strip()]
                started_at = perf_counter()
                cta_url = _build_cta_url(base_url, route_slug)

                try:
                    if not recipient_email:
                        raise RuntimeError("email_unavailable")

                    result = await client.send_growth_notification(
                        email=recipient_email,
                        title=delivery.title,
                        message=delivery.message,
                        locale=locale,
                        cta_url=cta_url,
                        notes=notes,
                    )
                    if str(result.get("status") or "").lower() == "skipped":
                        raise RuntimeError("provider_unavailable")

                    delivery.delivery_status = "delivered"
                    delivery.delivered_at = datetime.now(UTC)
                    delivery.status_reason = None
                    _record_delivery_event(
                        session,
                        delivery=delivery,
                        event_type="email_delivered",
                        event_payload={"channel": "email", "provider": provider},
                    )
                    sent_count += 1
                    EMAIL_SEND_TOTAL.labels(provider=provider, email_type="notification", status="success").inc()
                    EMAIL_SEND_CONTEXT_TOTAL.labels(
                        channel="growth",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                        status="success",
                    ).inc()
                except Exception as exc:
                    error_type = _classify_email_error(exc)
                    delivery.delivery_status = "failed"
                    delivery.delivered_at = None
                    delivery.status_reason = error_type
                    _record_delivery_event(
                        session,
                        delivery=delivery,
                        event_type="email_failed",
                        reason_code=error_type,
                        event_payload={"channel": "email", "provider": provider},
                    )
                    failed_count += 1
                    EMAIL_SEND_TOTAL.labels(provider=provider, email_type="notification", status="failed").inc()
                    EMAIL_SEND_CONTEXT_TOTAL.labels(
                        channel="growth",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                        status="failed",
                    ).inc()
                    EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
                    logger.warning(
                        "growth_notification_email_failed",
                        delivery_id=str(delivery.id),
                        provider=provider,
                        error_type=error_type,
                    )
                finally:
                    duration = perf_counter() - started_at
                    EMAIL_SEND_DURATION.labels(provider=provider, email_type="notification").observe(duration)
                    EMAIL_SEND_CONTEXT_DURATION.labels(
                        channel="growth",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                    ).observe(duration)
                    await session.commit()

    logger.info(
        "growth_notification_email_batch_complete",
        sent=sent_count,
        failed=failed_count,
    )
    return {"sent": sent_count, "failed": failed_count}
