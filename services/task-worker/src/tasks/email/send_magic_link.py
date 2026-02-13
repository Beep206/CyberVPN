"""Send magic link email via Resend, Brevo, or SMTP (dev mode)."""

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.email import BrevoClient, ResendClient, SmtpClient

logger = structlog.get_logger(__name__)


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
            return {
                "success": True,
                "provider": provider,
                "server": result.get("server"),
                "message_id": result.get("id"),
            }

        except Exception as e:
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
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id") or result.get("messageId"),
        }

    except Exception as e:
        logger.error(
            "magic_link_email_failed",
            email=email,
            provider=provider,
            error=str(e),
        )
        raise
