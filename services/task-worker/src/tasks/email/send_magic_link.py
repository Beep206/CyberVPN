"""Send magic link email via Resend, Brevo, or SMTP (dev mode)."""

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


@broker.task(
    task_name="send_magic_link_email",
    queue="email",
    retry_policy="email_delivery",
)
async def send_magic_link_email(
    email: str,
    token: str,
    locale: str = "en-EN",
    is_resend: bool = False,
    otp_code: str = "",
    channel: str = "web",
) -> dict:
    """
    Send magic link email for passwordless login.

    Constructs the magic link URL from token and base URL, then sends
    via the appropriate email provider.

    In dev mode (EMAIL_DEV_MODE=true): Uses Mailpit SMTP with round-robin rotation.
    In production:
        - Initial: Resend.com (primary provider)
        - Resend: Brevo (secondary provider, different IP reputation)

    Args:
        email: Recipient email address
        token: Magic link token
        locale: User's locale for email template
        is_resend: If True and not in dev mode, use Brevo
        otp_code: Optional 6-digit OTP code to display alongside the link

    Returns:
        API response with message ID and provider info
    """
    settings = get_settings()
    started_at = perf_counter()

    # Construct full magic link URL
    base_url = settings.magic_link_base_url.rstrip("/")
    magic_link_url = f"{base_url}/{locale}/magic-link/verify?token={token}"

    # Dev mode: Use SMTP (Mailpit) with round-robin
    if settings.email_dev_mode:
        provider = "smtp"
        logger.info(
            "sending_magic_link_email",
            email=email,
            locale=locale,
            is_resend=is_resend,
            provider=provider,
            dev_mode=True,
        )

        try:
            async with SmtpClient() as client:
                result = await client.send_magic_link(
                    email=email,
                    magic_link_url=magic_link_url,
                    locale=locale,
                    otp_code=otp_code,
                )

            logger.info(
                "magic_link_email_sent",
                email=email,
                provider=provider,
                server=result.get("server"),
                message_id=result.get("id"),
            )
            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="magic_link", status="success").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="magic_link",
                locale=_normalize_locale(locale),
                status="success",
            ).inc()
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="magic_link").observe(perf_counter() - started_at)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="magic_link",
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
            EMAIL_SEND_TOTAL.labels(provider=provider, email_type="magic_link", status="failed").inc()
            EMAIL_SEND_CONTEXT_TOTAL.labels(
                channel=channel,
                provider=provider,
                email_type="magic_link",
                locale=_normalize_locale(locale),
                status="failed",
            ).inc()
            EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
            EMAIL_SEND_DURATION.labels(provider=provider, email_type="magic_link").observe(perf_counter() - started_at)
            EMAIL_SEND_CONTEXT_DURATION.labels(
                channel=channel,
                provider=provider,
                email_type="magic_link",
                locale=_normalize_locale(locale),
            ).observe(perf_counter() - started_at)
            logger.error(
                "magic_link_email_failed",
                email=email,
                provider=provider,
                error=str(e),
            )
            raise

    # Production mode: Use API providers
    provider = "brevo" if is_resend else "resend"

    logger.info(
        "sending_magic_link_email",
        email=email,
        locale=locale,
        is_resend=is_resend,
        provider=provider,
    )

    try:
        if is_resend:
            async with BrevoClient() as client:
                result = await client.send_magic_link(
                    email=email,
                    magic_link_url=magic_link_url,
                    locale=locale,
                    otp_code=otp_code,
                )
        else:
            async with ResendClient() as client:
                result = await client.send_magic_link(
                    email=email,
                    magic_link_url=magic_link_url,
                    locale=locale,
                    otp_code=otp_code,
                )

        logger.info(
            "magic_link_email_sent",
            email=email,
            provider=provider,
            message_id=result.get("id") or result.get("messageId"),
        )
        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="magic_link", status="success").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="magic_link",
            locale=_normalize_locale(locale),
            status="success",
        ).inc()
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="magic_link").observe(perf_counter() - started_at)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="magic_link",
            locale=_normalize_locale(locale),
        ).observe(perf_counter() - started_at)
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id") or result.get("messageId"),
        }

    except Exception as e:
        error_type = _classify_email_error(e)
        EMAIL_SEND_TOTAL.labels(provider=provider, email_type="magic_link", status="failed").inc()
        EMAIL_SEND_CONTEXT_TOTAL.labels(
            channel=channel,
            provider=provider,
            email_type="magic_link",
            locale=_normalize_locale(locale),
            status="failed",
        ).inc()
        EMAIL_SEND_ERRORS.labels(provider=provider, error_type=error_type).inc()
        EMAIL_SEND_DURATION.labels(provider=provider, email_type="magic_link").observe(perf_counter() - started_at)
        EMAIL_SEND_CONTEXT_DURATION.labels(
            channel=channel,
            provider=provider,
            email_type="magic_link",
            locale=_normalize_locale(locale),
        ).observe(perf_counter() - started_at)
        logger.error(
            "magic_link_email_failed",
            email=email,
            provider=provider,
            error=str(e),
        )
        raise
