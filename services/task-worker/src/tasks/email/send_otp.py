"""Send OTP verification email via Resend, Brevo, or SMTP (dev mode)."""

from time import perf_counter
from urllib.parse import urlencode

import structlog

from src.broker import broker
from src.config import get_settings
from src.metrics import (
    EMAIL_SEND_CONTEXT_DURATION,
    EMAIL_SEND_CONTEXT_TOTAL,
    EMAIL_SEND_DURATION,
    EMAIL_SEND_ERRORS,
    EMAIL_SEND_TOTAL,
    OTP_EMAIL_ERRORS,
    OTP_EMAILS_SENT,
)
from src.services.email import BrevoClient, ResendClient, SmtpClient

logger = structlog.get_logger(__name__)


def _classify_email_error(exc: Exception) -> str:
    """Map provider exceptions to low-cardinality metric labels."""
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


def _has_secret(secret: object) -> bool:
    get_secret_value = getattr(secret, "get_secret_value", None)
    if get_secret_value is None:
        return bool(str(secret or "").strip())
    return bool(str(get_secret_value()).strip())


def _select_api_provider(*, is_resend: bool, settings: object) -> str:
    if not is_resend:
        return "resend"
    if _has_secret(getattr(settings, "brevo_api_key", None)):
        return "brevo"
    logger.warning("brevo_api_key_not_configured_falling_back_to_resend", is_resend=is_resend)
    return "resend"


def _build_activation_url(*, base_url: str, email: str, otp_code: str, locale: str) -> str:
    normalized_base = (base_url or "http://localhost:9001").rstrip("/")
    normalized_locale = (locale or "en-EN").strip() or "en-EN"
    query = urlencode({"email": email, "code": otp_code})
    return f"{normalized_base}/{normalized_locale}/verify?{query}"


@broker.task(
    task_name="send_otp_email",
    queue="email",
    retry_policy="email_delivery",
)
async def send_otp_email(
    email: str,
    otp_code: str,
    locale: str = "en-EN",
    is_resend: bool = False,
    channel: str = "web",
) -> dict:
    """
    Send OTP verification email.

    In dev mode (EMAIL_DEV_MODE=true): Uses Mailpit SMTP with round-robin rotation.
    In production:
        - Initial: Resend.com (primary provider)
        - Resend: Brevo (secondary provider, different IP reputation)

    Args:
        email: Recipient email address
        otp_code: 6-digit OTP code
        locale: User's locale for email template
        is_resend: If True and not in dev mode, use Brevo

    Returns:
        API response with message ID and provider info
    """
    settings = get_settings()
    action = "resend" if is_resend else "initial"
    started_at = perf_counter()
    activation_url = _build_activation_url(
        base_url=getattr(settings, "magic_link_base_url", ""),
        email=email,
        otp_code=otp_code,
        locale=locale,
    )

    # Dev mode: Use SMTP (Mailpit) with round-robin
    if settings.email_dev_mode:
        provider = "smtp"
        logger.info(
            "sending_otp_email",
            email=email,
            locale=locale,
            is_resend=is_resend,
            provider=provider,
            dev_mode=True,
        )

        try:
            async with SmtpClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )

            logger.info(
                "otp_email_sent",
                email=email,
                provider=provider,
                server=result.get("server"),
                message_id=result.get("id"),
            )
            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="otp", status="success").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="otp",
                locale=_normalize_locale(locale),
                status="success",
            ).inc()
            OTP_EMAILS_SENT.labels(provider=provider, action=action, status="success").inc()
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="otp").observe(perf_counter() - started_at)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="otp",
                locale=_normalize_locale(locale),
            ).observe(perf_counter() - started_at)
            return {
                "success": True,
                "provider": provider,
                "server": result.get("server"),
                "message_id": result.get("id"),
            }

        except Exception as e:
            error_type = _classify_email_error(e)
            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="otp", status="failed").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="otp",
                locale=_normalize_locale(locale),
                status="failed",
            ).inc()
            EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
            OTP_EMAILS_SENT.labels(provider=provider, action=action, status="failed").inc()
            OTP_EMAIL_ERRORS.labels(provider=provider, error_type=error_type).inc()
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="otp").observe(perf_counter() - started_at)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="otp",
                locale=_normalize_locale(locale),
            ).observe(perf_counter() - started_at)
            logger.error(
                "otp_email_failed",
                email=email,
                provider=provider,
                error=str(e),
            )
            raise

    # Production mode: use Brevo for resend only when it is configured.
    # During S2, Resend is the confirmed production provider; Brevo remains optional.
    provider = _select_api_provider(is_resend=is_resend, settings=settings)

    logger.info(
        "sending_otp_email",
        email=email,
        locale=locale,
        is_resend=is_resend,
        provider=provider,
    )

    try:
        if provider == "brevo":
            async with BrevoClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )
        else:
            async with ResendClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )

        logger.info(
            "otp_email_sent",
            email=email,
            provider=provider,
            message_id=result.get("id"),
        )
        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="otp", status="success").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="otp",
            locale=_normalize_locale(locale),
            status="success",
        ).inc()
        OTP_EMAILS_SENT.labels(provider=provider, action=action, status="success").inc()
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="otp").observe(perf_counter() - started_at)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="otp",
            locale=_normalize_locale(locale),
        ).observe(perf_counter() - started_at)
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id"),
        }

    except Exception as e:
        error_type = _classify_email_error(e)
        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="otp", status="failed").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="otp",
            locale=_normalize_locale(locale),
            status="failed",
        ).inc()
        EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
        OTP_EMAILS_SENT.labels(provider=provider, action=action, status="failed").inc()
        OTP_EMAIL_ERRORS.labels(provider=provider, error_type=error_type).inc()
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="otp").observe(perf_counter() - started_at)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="otp",
            locale=_normalize_locale(locale),
        ).observe(perf_counter() - started_at)
        logger.error(
            "otp_email_failed",
            email=email,
            provider=provider,
            error=str(e),
        )
        raise
