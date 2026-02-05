"""Send OTP verification email task.

Uses Resend.com for initial OTP, Brevo for resend requests.
Tracks metrics in Prometheus for Grafana monitoring.
"""

from typing import Any, cast

import structlog

from src.broker import broker
from src.metrics import OTP_EMAILS_SENT, OTP_EMAIL_ERRORS
from src.services.email.resend_client import ResendClient, ResendError
from src.services.email.brevo_client import BrevoClient, BrevoError

logger = structlog.get_logger(__name__)


@broker.task(task_name="send_otp_email", queue="email")
async def send_otp_email(
    email: str,
    otp_code: str,
    locale: str = "en-EN",
    is_resend: bool = False,
) -> dict[str, Any]:
    """
    Send OTP verification email to user.

    Args:
        email: Recipient email address
        otp_code: 6-digit OTP code
        locale: User's locale for email template
        is_resend: If True, use Brevo (secondary); otherwise use Resend (primary)

    Returns:
        dict with provider, message_id, and status

    Provider Selection:
        - Initial OTP: Resend.com (modern API, fast delivery)
        - Resend OTP: Brevo (different IP reputation, backup)

    This allows maximizing free tier limits across providers and provides
    redundancy if one provider has deliverability issues.
    """
    provider = "brevo" if is_resend else "resend"
    action = "resend" if is_resend else "initial"

    logger.info(
        "sending_otp_email",
        email=email,
        provider=provider,
        action=action,
        locale=locale,
    )

    try:
        if is_resend:
            # Use Brevo for resend requests
            async with BrevoClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                )
        else:
            # Use Resend for initial OTP
            async with ResendClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                )

        # Track success metrics
        OTP_EMAILS_SENT.labels(provider=provider, action=action, status="success").inc()

        message_id = result.get("id") or result.get("messageId")
        logger.info(
            "otp_email_sent_success",
            email=email,
            provider=provider,
            action=action,
            message_id=message_id,
        )

        return {
            "provider": provider,
            "message_id": message_id,
            "status": "sent",
            "action": action,
        }

    except (ResendError, BrevoError) as e:
        OTP_EMAILS_SENT.labels(provider=provider, action=action, status="failed").inc()
        OTP_EMAIL_ERRORS.labels(provider=provider, error_type="api_error").inc()

        logger.error(
            "otp_email_failed",
            email=email,
            provider=provider,
            action=action,
            error=str(e),
            status_code=getattr(e, "status_code", None),
        )

        # Re-raise for retry middleware
        raise

    except Exception as e:
        OTP_EMAILS_SENT.labels(provider=provider, action=action, status="failed").inc()
        OTP_EMAIL_ERRORS.labels(provider=provider, error_type="unknown").inc()

        logger.exception(
            "otp_email_unexpected_error",
            email=email,
            provider=provider,
            error=str(e),
        )
        raise


# Apply retry policy for email delivery
send_otp_email = cast(Any, send_otp_email).with_labels(retry_policy="email_delivery")
