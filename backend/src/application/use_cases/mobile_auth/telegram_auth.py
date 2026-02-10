"""Telegram OAuth authentication use case.

Handles Telegram Login Widget callback validation and user creation/linking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    DeviceInfoDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TelegramAuthRequestDTO,
    TokenResponseDTO,
    UserResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.application.services.telegram_auth import TelegramAuthService
from src.config.settings import settings
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
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
            user = await self._create_user_from_telegram(telegram_data)
            is_new_user = True
        else:
            # Update existing user's Telegram data if needed
            await self._update_telegram_data(user, telegram_data)

        # Register or update device
        await self._register_device(user.id, request.device)

        # Update last login timestamp
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        # Generate tokens
        # MED-003: Properly unpack token tuple (token, jti, expires_at)
        access_token, _access_jti, _access_expire = self.auth_service.create_access_token(
            subject=str(user.id),
            role="mobile_user",
            extra={"device_id": request.device.device_id},
        )
        refresh_token, _refresh_jti, _refresh_expire = self.auth_service.create_refresh_token(
            subject=str(user.id),
        )

        # Build response
        tokens = TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

        # Fetch subscription from Remnawave (cached, with fallback to NONE).
        if self.subscription_client and user.remnawave_uuid:
            subscription = await self.subscription_client.get_subscription(user.remnawave_uuid)
        else:
            subscription = SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

        user_response = UserResponseDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            status=user.status,
            telegram_id=user.telegram_id,
            telegram_username=user.telegram_username,
            created_at=user.created_at,
            subscription=subscription,
        )

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

        The user will have no password (can only login via Telegram).
        Email is generated from Telegram ID to ensure uniqueness.
        """
        # Generate placeholder email from Telegram ID
        # User can update this later if needed
        placeholder_email = f"tg{telegram_data.telegram_id}@telegram.local"

        # Build username from Telegram data
        username = telegram_data.username
        if not username:
            username = f"{telegram_data.first_name}"
            if telegram_data.last_name:
                username = f"{username} {telegram_data.last_name}"

        user = MobileUserModel(
            email=placeholder_email,
            password_hash=None,  # No password for Telegram-only auth
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

    async def _register_device(self, user_id, device: DeviceInfoDTO) -> None:
        """Register or update device for the user."""
        existing_device = await self.device_repo.get_by_device_id_and_user(
            device_id=device.device_id,
            user_id=user_id,
        )

        if existing_device:
            # Update existing device
            existing_device.platform = device.platform.value
            existing_device.platform_id = device.platform_id
            existing_device.os_version = device.os_version
            existing_device.app_version = device.app_version
            existing_device.device_model = device.device_model
            existing_device.push_token = device.push_token
            existing_device.last_active_at = datetime.now(UTC)
            await self.device_repo.update(existing_device)
        else:
            # Create new device
            new_device = MobileDeviceModel(
                device_id=device.device_id,
                platform=device.platform.value,
                platform_id=device.platform_id,
                os_version=device.os_version,
                app_version=device.app_version,
                device_model=device.device_model,
                push_token=device.push_token,
                user_id=user_id,
                last_active_at=datetime.now(UTC),
            )
            await self.device_repo.create(new_device)
