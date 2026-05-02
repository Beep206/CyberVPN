"""Process recurring customer growth reporting deliveries."""

from __future__ import annotations

from time import perf_counter, time
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    EMAIL_SEND_CONTEXT_DURATION,
    EMAIL_SEND_CONTEXT_TOTAL,
    EMAIL_SEND_DURATION,
    EMAIL_SEND_ERRORS,
    EMAIL_SEND_TOTAL,
    GROWTH_REPORTING_DELIVERY_CONSECUTIVE_FAILURES,
    GROWTH_REPORTING_DELIVERY_DURATION,
    GROWTH_REPORTING_DELIVERY_LAST_ATTEMPT_UNIXTIME,
    GROWTH_REPORTING_DELIVERY_LAST_CLAIMED,
    GROWTH_REPORTING_DELIVERY_LAST_DELIVERED,
    GROWTH_REPORTING_DELIVERY_LAST_FAILED,
    GROWTH_REPORTING_DELIVERY_LAST_SUCCESS_UNIXTIME,
    GROWTH_REPORTING_DELIVERY_RUNS_TOTAL,
)
from src.services.backend_api_client import BackendAPIClient
from src.services.email import BrevoClient, ResendClient, SmtpClient

logger = structlog.get_logger(__name__)

DEFAULT_GROWTH_REPORTING_DELIVERY_LIMIT = 10


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


def _select_email_client() -> tuple[type[SmtpClient] | type[ResendClient] | type[BrevoClient], str]:
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


def _extract_provider_message_id(result: dict[str, Any]) -> str | None:
    for key in ("id", "messageId", "message_id"):
        value = result.get(key)
        if value is not None:
            return str(value)
    return None


def _record_run_result(
    *,
    result: str,
    claimed_count: int,
    delivered_count: int,
    failed_count: int,
    duration_seconds: float,
) -> None:
    now_unix = time()
    GROWTH_REPORTING_DELIVERY_LAST_ATTEMPT_UNIXTIME.set(now_unix)
    GROWTH_REPORTING_DELIVERY_LAST_CLAIMED.set(max(claimed_count, 0))
    GROWTH_REPORTING_DELIVERY_LAST_DELIVERED.set(max(delivered_count, 0))
    GROWTH_REPORTING_DELIVERY_LAST_FAILED.set(max(failed_count, 0))
    GROWTH_REPORTING_DELIVERY_DURATION.observe(duration_seconds)
    GROWTH_REPORTING_DELIVERY_RUNS_TOTAL.labels(result=result).inc()
    if result == "failure":
        GROWTH_REPORTING_DELIVERY_CONSECUTIVE_FAILURES.inc()
    else:
        GROWTH_REPORTING_DELIVERY_CONSECUTIVE_FAILURES.set(0)
        GROWTH_REPORTING_DELIVERY_LAST_SUCCESS_UNIXTIME.set(now_unix)


@broker.task(task_name="process_growth_reporting_deliveries", queue="email")
async def process_growth_reporting_deliveries() -> dict[str, Any]:
    """Claim due growth reporting deliveries from backend, send email, and finalize status."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("growth_reporting_delivery_skipped", reason="backend_api_not_configured")
        _record_run_result(
            result="skipped",
            claimed_count=0,
            delivered_count=0,
            failed_count=0,
            duration_seconds=0,
        )
        return {"skipped": True, "reason": "backend_api_not_configured"}

    started = perf_counter()
    claimed_count = 0
    delivered_count = 0
    failed_count = 0

    async with BackendAPIClient() as backend:
        if not backend.enabled:
            logger.info("growth_reporting_delivery_skipped", reason="backend_api_disabled")
            _record_run_result(
                result="skipped",
                claimed_count=0,
                delivered_count=0,
                failed_count=0,
                duration_seconds=0,
            )
            return {"skipped": True, "reason": "backend_api_disabled"}

        claim_response = await backend.claim_growth_reporting_deliveries(
            {"limit": DEFAULT_GROWTH_REPORTING_DELIVERY_LIMIT},
        )
        deliveries = list(claim_response.get("deliveries") or [])
        claimed_count = int(claim_response.get("claimed_count", 0) or 0)
        skipped_count = int(claim_response.get("skipped_count", 0) or 0)
        overdue_count = int(claim_response.get("overdue_count", 0) or 0)

        if not deliveries:
            _record_run_result(
                result="skipped",
                claimed_count=claimed_count,
                delivered_count=0,
                failed_count=0,
                duration_seconds=perf_counter() - started,
            )
            result = {
                "claimed_count": claimed_count,
                "delivered_count": 0,
                "failed_count": 0,
                "skipped_count": skipped_count,
                "overdue_count": overdue_count,
            }
            logger.info("growth_reporting_delivery_noop", **result)
            return result

        try:
            client_cls, provider = _select_email_client()
        except RuntimeError as exc:
            error_type = _classify_email_error(exc)
            for delivery in deliveries:
                await backend.complete_growth_reporting_delivery(
                    delivery_id=str(delivery["delivery_id"]),
                    payload={
                        "delivery_status": "failed",
                        "provider_name": "unknown",
                        "provider_message_id": None,
                        "failure_message": error_type,
                    },
                )
            failed_count = len(deliveries)
            _record_run_result(
                result="failure",
                claimed_count=claimed_count,
                delivered_count=0,
                failed_count=failed_count,
                duration_seconds=perf_counter() - started,
            )
            logger.error(
                "growth_reporting_delivery_provider_unavailable",
                claimed_count=claimed_count,
                skipped_count=skipped_count,
                overdue_count=overdue_count,
            )
            return {
                "claimed_count": claimed_count,
                "delivered_count": 0,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "overdue_count": overdue_count,
                "provider": "unknown",
            }

        async with client_cls() as client:
            for delivery in deliveries:
                locale = _normalize_locale(str(delivery.get("locale") or "en-EN"))
                recipient_email = str(delivery.get("recipient_email") or "").strip()
                send_started = perf_counter()
                try:
                    if not recipient_email:
                        raise RuntimeError("email_unavailable")

                    provider_result = await client.send_growth_notification(
                        email=recipient_email,
                        subject=str(delivery.get("subject") or "").strip() or None,
                        title=str(delivery.get("title") or "Growth reporting digest"),
                        message=str(delivery.get("message") or ""),
                        locale=locale,
                        cta_url="",
                        notes=[str(item) for item in list(delivery.get("notes") or []) if str(item).strip()],
                    )
                    if str(provider_result.get("status") or "").lower() == "skipped":
                        raise RuntimeError("provider_unavailable")

                    await backend.complete_growth_reporting_delivery(
                        delivery_id=str(delivery["delivery_id"]),
                        payload={
                            "delivery_status": "delivered",
                            "provider_name": provider,
                            "provider_message_id": _extract_provider_message_id(provider_result),
                            "failure_message": None,
                        },
                    )
                    delivered_count += 1
                    EMAIL_SEND_TOTAL.labels(provider=provider, email_type="notification", status="success").inc()
                    EMAIL_SEND_CONTEXT_TOTAL.labels(
                        channel="growth_reporting",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                        status="success",
                    ).inc()
                except Exception as exc:
                    error_type = _classify_email_error(exc)
                    await backend.complete_growth_reporting_delivery(
                        delivery_id=str(delivery["delivery_id"]),
                        payload={
                            "delivery_status": "failed",
                            "provider_name": provider,
                            "provider_message_id": None,
                            "failure_message": error_type,
                        },
                    )
                    failed_count += 1
                    EMAIL_SEND_TOTAL.labels(provider=provider, email_type="notification", status="failed").inc()
                    EMAIL_SEND_CONTEXT_TOTAL.labels(
                        channel="growth_reporting",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                        status="failed",
                    ).inc()
                    EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
                    logger.warning(
                        "growth_reporting_delivery_failed",
                        delivery_id=str(delivery["delivery_id"]),
                        provider=provider,
                        error_type=error_type,
                    )
                finally:
                    duration = perf_counter() - send_started
                    EMAIL_SEND_DURATION.labels(provider=provider, email_type="notification").observe(duration)
                    EMAIL_SEND_CONTEXT_DURATION.labels(
                        channel="growth_reporting",
                        provider=provider,
                        email_type="notification",
                        locale=locale,
                    ).observe(duration)

    result_label = "success"
    if delivered_count == 0 and failed_count > 0:
        result_label = "failure"
    elif delivered_count > 0 and failed_count > 0:
        result_label = "partial"
    elif delivered_count == 0:
        result_label = "skipped"

    _record_run_result(
        result=result_label,
        claimed_count=claimed_count,
        delivered_count=delivered_count,
        failed_count=failed_count,
        duration_seconds=perf_counter() - started,
    )
    result = {
        "claimed_count": claimed_count,
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "overdue_count": overdue_count,
    }
    logger.info("growth_reporting_delivery_complete", result=result_label, **result)
    return result
