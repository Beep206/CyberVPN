"""Send password reset email via Resend, Brevo, or SMTP (dev mode)."""

from time import perf_counter

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    EMAIL_SEND_CONTEXT_DURATION,
    EMAIL_SEND_CONTEXT_TOTAL,
    EMAIL_SEND_DURATION,
    EMAIL_SEND_ERRORS,
    EMAIL_SEND_TOTAL,
)
from src.services.email import ResendClient, SmtpClient

logger = structlog.get_logger(__name__)


def _classify_email_error(exc: Exception) -> str:
    error_name = type(exc).__name__.lower()
    if "timeout" in error_name:
        return "timeout"
    if any(keyword in error_name for keyword in ("connect", "socket", "network")):
        return "network_error"
    if any(keyword in error_name for keyword in ("http", "api", "smtp", "response", "status")):
        return "api_error"
    return "unknown"


def _normalize_locale(locale: str | None) -> str:
    if not locale:
        return "unknown"
    normalized = locale.strip()
    return normalized or "unknown"


@broker.task(
    task_name="send_password_reset_email",
    queue="email",
    retry_policy="email_delivery",
)
async def send_password_reset_email(
    email: str,
    otp_code: str,
    locale: str = "en-EN",
    channel: str = "web",
) -> dict:
    """Send password reset OTP email."""
    settings = get_settings()
    started_at = perf_counter()

    if settings.email_dev_mode:
        provider = "smtp"
        logger.info(
            "sending_password_reset_email",
            email=email,
            locale=locale,
            provider=provider,
            dev_mode=True,
        )
        try:
            async with SmtpClient() as client:
                result = await client.send_password_reset(email=email, code=otp_code, locale=locale)

            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="password_reset", status="success").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="password_reset",
                locale=_normalize_locale(locale),
                status="success",
            ).inc()
            duration = perf_counter() - started_at
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="password_reset").observe(duration)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="password_reset",
                locale=_normalize_locale(locale),
            ).observe(duration)
            return {
                "success": True,
                "provider": provider,
                "server": result.get("server"),
                "message_id": result.get("id"),
            }
        except Exception as exc:
            error_type = _classify_email_error(exc)
            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="password_reset", status="failed").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="password_reset",
                locale=_normalize_locale(locale),
                status="failed",
            ).inc()
            EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
            duration = perf_counter() - started_at
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="password_reset").observe(duration)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="password_reset",
                locale=_normalize_locale(locale),
            ).observe(duration)
            logger.error("password_reset_email_failed", email=email, provider=provider, error=str(exc))
            raise

    provider = "resend"
    logger.info("sending_password_reset_email", email=email, locale=locale, provider=provider)
    try:
        async with ResendClient() as client:
            result = await client.send_password_reset(email=email, code=otp_code, locale=locale)

        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="password_reset", status="success").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="password_reset",
            locale=_normalize_locale(locale),
            status="success",
        ).inc()
        duration = perf_counter() - started_at
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="password_reset").observe(duration)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="password_reset",
            locale=_normalize_locale(locale),
        ).observe(duration)
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id") or result.get("messageId"),
        }
    except Exception as exc:
        error_type = _classify_email_error(exc)
        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="password_reset", status="failed").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="password_reset",
            locale=_normalize_locale(locale),
            status="failed",
        ).inc()
        EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
        duration = perf_counter() - started_at
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="password_reset").observe(duration)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="password_reset",
            locale=_normalize_locale(locale),
        ).observe(duration)
        logger.error("password_reset_email_failed", email=email, provider=provider, error=str(exc))
        raise
