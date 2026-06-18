"""Safe email provider routing policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EmailProvider = Literal["smtp", "resend"]
EmailRouteReason = Literal["dev_smtp", "smtp_primary", "explicit_resend_fallback"]


@dataclass(frozen=True)
class EmailDeliveryRoute:
    """Selected provider route for a single email delivery attempt."""

    provider: EmailProvider
    reason: EmailRouteReason


def _has_secret(secret: object) -> bool:
    get_secret_value = getattr(secret, "get_secret_value", None)
    if get_secret_value is None:
        return bool(str(secret or "").strip())
    return bool(str(get_secret_value()).strip())


def select_auth_email_route(*, settings: object, is_resend: bool) -> EmailDeliveryRoute:
    """Route auth mail through cyber-vpn.net SMTP unless explicit Resend fallback is enabled."""
    if bool(getattr(settings, "email_dev_mode", False)):
        return EmailDeliveryRoute(provider="smtp", reason="dev_smtp")

    if is_resend and bool(getattr(settings, "email_resend_fallback_enabled", False)):
        if not _has_secret(getattr(settings, "resend_api_key", None)):
            raise RuntimeError("resend_fallback_enabled_without_resend_api_key")
        return EmailDeliveryRoute(provider="resend", reason="explicit_resend_fallback")

    return EmailDeliveryRoute(provider="smtp", reason="smtp_primary")


def select_system_email_route(*, settings: object) -> EmailDeliveryRoute:
    """Route system mail through the configured SMTP primary provider."""
    if bool(getattr(settings, "email_dev_mode", False)):
        return EmailDeliveryRoute(provider="smtp", reason="dev_smtp")
    return EmailDeliveryRoute(provider="smtp", reason="smtp_primary")
