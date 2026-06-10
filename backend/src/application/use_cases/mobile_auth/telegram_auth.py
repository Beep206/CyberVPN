"""Telegram OAuth authentication use case.

Handles Telegram Login Widget callback validation and user creation/linking.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TelegramAuthRequestDTO,
)
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.services.public_registration_policy import ensure_public_registration_enabled
from src.application.services.public_uid_allocator import allocate_public_uid
from src.application.services.telegram_auth import TelegramAuthService
from src.application.use_cases.mobile_auth.user_response import build_mobile_user_response
from src.domain.entities.auth_realm import DEFAULT_AUTH_REALMS, stable_auth_realm_id
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)

if TYPE_CHECKING:
    from src.infrastructure.remnawave.subscription_client import CachedSubscriptionClient


@dataclass
class MobileTelegramAuthUseCase:
    """Use case for authenticating mobile users via Telegram OAuth.

    Validates Telegram Login Widget callback, creates new accounts
    or links existing accounts, and returns authentication tokens.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    telegram_auth_service: TelegramAuthService
    subscription_client: CachedSubscriptionClient | None = None
    allow_new_users: bool = True
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, request: TelegramAuthRequestDTO) -> tuple[AuthResponseDTO, bool]:
        """Authenticate a user via Telegram OAuth.

        Args:
            request: Telegram auth request with auth_data and device info.

        Returns:
            Tuple of (AuthResponseDTO with tokens and user data, is_new_user bool).

        Raises:
            InvalidTelegramAuthError: If Telegram signature is invalid.
            TelegramAuthExpiredError: If auth_date is too old.
        """
        # Validate Telegram auth data and extract user info
        telegram_data = self.telegram_auth_service.validate_auth_data(request.auth_data)

        # Check if user exists by Telegram ID
        user = await self.user_repo.get_by_telegram_id(telegram_data.telegram_id)
        is_new_user = False

        if not user:
            # Create new user from Telegram data
            ensure_public_registration_enabled(
                channel="mobile_telegram",
                registration_enabled=self.allow_new_users,
            )
            user = await self._create_user_from_telegram(telegram_data)
            is_new_user = True
        else:
            # Update existing user's Telegram data if needed
            await self._update_telegram_data(user, telegram_data)

        # Update last login timestamp
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        tokens = await self._mobile_sessions().issue_session(user=user, device=request.device)

        # Fetch subscription from Remnawave (cached, with fallback to NONE).
        if self.subscription_client and user.remnawave_uuid:
            subscription = await self.subscription_client.get_subscription(user.remnawave_uuid)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        user_response = build_mobile_user_response(user, subscription=subscription)

        return (
            AuthResponseDTO(
                tokens=tokens,
                user=user_response,
                is_new_user=is_new_user,
            ),
            is_new_user,
        )

    async def _create_user_from_telegram(self, telegram_data) -> MobileUserModel:
        """Create a new user from Telegram data.

        The user gets a synthetic password hash so storage stays compatible with
        the existing non-null mobile password schema while password login remains
        disabled until the user explicitly sets credentials.
        """
        # Generate placeholder email from Telegram ID
        # User can update this later if needed
        placeholder_email = f"tg{telegram_data.telegram_id}@telegram.local"
        password_hash = await self.auth_service.hash_password(secrets.token_urlsafe(32))

        # Build username from Telegram data
        username = telegram_data.username
        if not username:
            username = f"{telegram_data.first_name}"
            if telegram_data.last_name:
                username = f"{username} {telegram_data.last_name}"

        user = MobileUserModel(
            auth_realm_id=stable_auth_realm_id(str(DEFAULT_AUTH_REALMS["customer"]["realm_key"])),
            public_uid=await allocate_public_uid(self.user_repo),
            email=placeholder_email,
            password_hash=password_hash,
            username=username,
            telegram_id=telegram_data.telegram_id,
            telegram_username=telegram_data.username,
            is_active=True,
            status="active",
        )
        return await self.user_repo.create(user)

    async def _update_telegram_data(self, user: MobileUserModel, telegram_data) -> None:
        """Update user's Telegram data if changed."""
        changed = False

        if user.telegram_username != telegram_data.username:
            user.telegram_username = telegram_data.username
            changed = True

        # Update username if it matches the old Telegram username pattern
        # and Telegram username changed
        if telegram_data.username and user.username and user.username.startswith("@"):
            user.username = telegram_data.username
            changed = True

        if changed:
            await self.user_repo.update(user)

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileTelegramAuthUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
