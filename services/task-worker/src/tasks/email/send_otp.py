"""Send OTP verification email via Resend, Brevo, or SMTP (dev mode)."""

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.email import BrevoClient, ResendClient, SmtpClient

logger = structlog.get_logger(__name__)


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
                result = await client.send_otp(email=email, code=otp_code, locale=locale)

            logger.info(
                "otp_email_sent",
                email=email,
                provider=provider,
                server=result.get("server"),
                message_id=result.get("id"),
            )
            return {
                "success": True,
                "provider": provider,
                "server": result.get("server"),
                "message_id": result.get("id"),
            }

        except Exception as e:
            logger.error(
                "otp_email_failed",
                email=email,
                provider=provider,
                error=str(e),
            )
            raise

    # Production mode: Use API providers
    provider = "brevo" if is_resend else "resend"

    logger.info(
        "sending_otp_email",
        email=email,
        locale=locale,
        is_resend=is_resend,
        provider=provider,
    )

    try:
        if is_resend:
            async with BrevoClient() as client:
                result = await client.send_otp(email=email, code=otp_code, locale=locale)
        else:
            async with ResendClient() as client:
                result = await client.send_otp(email=email, code=otp_code, locale=locale)

        logger.info(
            "otp_email_sent",
            email=email,
            provider=provider,
            message_id=result.get("id"),
        )
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id"),
        }

    except Exception as e:
        logger.error(
            "otp_email_failed",
            email=email,
            provider=provider,
            error=str(e),
        )
        raise
