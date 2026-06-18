"""Send OTP verification email through safe SMTP primary routing."""

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
    OTP_EMAIL_ERRORS,
    OTP_EMAILS_SENT,
)
from src.services.email import ResendClient, SmtpClient
from src.services.email.privacy import recipient_log_fields
from src.services.email.routing import select_auth_email_route
from src.tasks.email.payloads import (
    claim_email_task_payload,
    consume_email_task_payload,
    legacy_email_task_payload,
    release_email_task_payload,
    resolve_email_task_payload,
)

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


def _build_activation_url(
    *,
    base_url: str,
    locale: str,
    email: str | None = None,
    otp_code: str | None = None,
) -> str:
    del email, otp_code
    normalized_base = (base_url or "http://localhost:9001").rstrip("/")
    normalized_locale = (locale or "en-EN").strip() or "en-EN"
    return f"{normalized_base}/{normalized_locale}/verify"


@broker.task(
    task_name="send_otp_email",
    queue="email",
    retry_policy="email_delivery",
)
async def send_otp_email(
    payload_ref: str = "",
    email: str = "",
    otp_code: str = "",
    locale: str = "en-EN",
    is_resend: bool = False,
    channel: str = "web",
) -> dict:
    """
    Send OTP verification email.

    In dev mode (EMAIL_DEV_MODE=true): Uses Mailpit SMTP with round-robin rotation.
    Outside dev mode: Uses cyber-vpn.net SMTP primary. Resend is only selected
    when a resend/fallback task is explicit and EMAIL_RESEND_FALLBACK_ENABLED=true.

    Args:
        email: Recipient email address
        otp_code: 6-digit OTP code
        locale: User's locale for email template
        is_resend: Explicit resend/fallback signal; does not by itself bypass SMTP primary

    Returns:
        API response with message ID and provider info
    """
    settings = get_settings()
    started_at = perf_counter()
    payload_claimed = False

    if payload_ref:
        await claim_email_task_payload(payload_ref)
        payload_claimed = True
        try:
            payload = await resolve_email_task_payload(payload_ref, expected_kind="otp")
        except Exception:
            await release_email_task_payload(payload_ref)
            raise
    else:
        payload = legacy_email_task_payload(
            kind="otp",
            email=email,
            otp_code=otp_code,
            locale=locale,
            is_resend=is_resend,
            channel=channel,
        )

    email = payload.email
    otp_code = payload.otp_code
    locale = payload.locale
    is_resend = payload.is_resend
    channel = payload.channel
    action = "resend" if is_resend else "initial"
    recipient_fields = recipient_log_fields(email)
    activation_url = _build_activation_url(
        base_url=getattr(settings, "magic_link_base_url", ""),
        locale=locale,
    )
    provider = "unknown"

    try:
        # Dev mode: Use SMTP (Mailpit) with round-robin
        if settings.email_dev_mode:
            provider = "smtp"
            logger.info(
                "sending_otp_email",
                locale=locale,
                is_resend=is_resend,
                provider=provider,
                dev_mode=True,
                **recipient_fields,
            )

            async with SmtpClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )

            logger.info(
                "otp_email_sent",
                provider=provider,
                server=result.get("server"),
                message_id=result.get("id"),
                **recipient_fields,
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
            if payload_ref:
                try:
                    await consume_email_task_payload(payload_ref)
                except Exception as cleanup_error:
                    logger.error(
                        "email_task_payload_consume_failed_after_send",
                        provider=provider,
                        error=str(cleanup_error),
                        **recipient_fields,
                    )
            return {
                "success": True,
                "provider": provider,
                "server": result.get("server"),
                "message_id": result.get("id"),
            }

        route = select_auth_email_route(settings=settings, is_resend=is_resend)
        provider = route.provider

        logger.info(
            "sending_otp_email",
            locale=locale,
            is_resend=is_resend,
            provider=provider,
            route_reason=route.reason,
            **recipient_fields,
        )
        if provider == "resend":
            async with ResendClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )
        else:
            async with SmtpClient() as client:
                result = await client.send_otp(
                    email=email,
                    code=otp_code,
                    locale=locale,
                    activation_url=activation_url,
                )

        logger.info(
            "otp_email_sent",
            provider=provider,
            message_id=result.get("id"),
            **recipient_fields,
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
        if payload_ref:
            try:
                await consume_email_task_payload(payload_ref)
            except Exception as cleanup_error:
                logger.error(
                    "email_task_payload_consume_failed_after_send",
                    provider=provider,
                    error=str(cleanup_error),
                    **recipient_fields,
                )
        return {
            "success": True,
            "provider": provider,
            "message_id": result.get("id"),
        }

    except Exception as e:
        if payload_ref and payload_claimed:
            await release_email_task_payload(payload_ref)
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
            provider=provider,
            error=str(e),
            **recipient_fields,
        )
        raise
