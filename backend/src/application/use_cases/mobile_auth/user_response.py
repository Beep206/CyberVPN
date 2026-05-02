"""Helpers for building consistent mobile user profile responses."""

from __future__ import annotations

from src.application.dto.mobile_auth import SubscriptionInfoDTO, UserResponseDTO
from src.infrastructure.database.models.mobile_user_model import MobileUserModel

_TELEGRAM_PLACEHOLDER_EMAIL_DOMAIN = "@telegram.local"


def build_mobile_user_response(
    user: MobileUserModel,
    *,
    subscription: SubscriptionInfoDTO | None = None,
) -> UserResponseDTO:
    """Map a mobile user model into the public mobile auth/profile shape."""
    linked_providers: list[str] = []
    if user.telegram_subject or user.telegram_id is not None:
        linked_providers.append("telegram")

    return UserResponseDTO(
        id=user.id,
        email=user.email,
        username=user.username,
        status=user.status,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        is_email_verified=not user.email.endswith(_TELEGRAM_PLACEHOLDER_EMAIL_DOMAIN),
        is_2fa_enabled=user.totp_enabled,
        linked_providers=linked_providers,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        subscription=subscription,
    )
