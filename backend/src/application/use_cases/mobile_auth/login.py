"""Mobile user login use case.

Handles authentication of mobile app users with credential validation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    LoginRequestDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TokenResponseDTO,
    UserResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidCredentialsError
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileLoginUseCase:
    """Use case for authenticating mobile app users.

    Validates credentials, updates device info, and returns authentication tokens.
    Supports extended refresh token TTL with remember_me option.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService

    async def execute(self, request: LoginRequestDTO) -> AuthResponseDTO:
        """Authenticate a mobile user.

        Args:
            request: Login request with email, password, device info, and remember_me flag.

        Returns:
            AuthResponseDTO with tokens and user data.

        Raises:
            InvalidCredentialsError: If email not found or password incorrect.
        """
        # Find user by email
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise InvalidCredentialsError()

        # Verify password
        is_valid = await self.auth_service.verify_password(request.password, user.password_hash)
        if not is_valid:
            raise InvalidCredentialsError()

        # Check account status
        if not user.is_active:
            raise InvalidCredentialsError()

        # Update or create device registration
        device = await self.device_repo.get_by_device_id_and_user(
            device_id=request.device.device_id,
            user_id=user.id,
        )

        if device:
            # Update existing device
            device.platform = request.device.platform.value
            device.platform_id = request.device.platform_id
            device.os_version = request.device.os_version
            device.app_version = request.device.app_version
            device.device_model = request.device.device_model
            device.push_token = request.device.push_token
            device.last_active_at = datetime.now(timezone.utc)
            await self.device_repo.update(device)
        else:
            # Register new device
            device = MobileDeviceModel(
                device_id=request.device.device_id,
                platform=request.device.platform.value,
                platform_id=request.device.platform_id,
                os_version=request.device.os_version,
                app_version=request.device.app_version,
                device_model=request.device.device_model,
                push_token=request.device.push_token,
                user_id=user.id,
                last_active_at=datetime.now(timezone.utc),
            )
            await self.device_repo.create(device)

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await self.user_repo.update(user)

        # Generate tokens
        access_token = self.auth_service.create_access_token(
            subject=str(user.id),
            role="mobile_user",
            extra={"device_id": request.device.device_id},
        )

        # Create refresh token with extended TTL if remember_me
        refresh_token = self._create_refresh_token(
            subject=str(user.id),
            remember_me=request.remember_me,
        )

        # Calculate expires_in based on settings
        expires_in = settings.access_token_expire_minutes * 60

        # Build response
        tokens = TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
        )

        subscription = SubscriptionInfoDTO(
            status=SubscriptionStatus.NONE,
            # TODO: Fetch actual subscription from Remnawave
        )

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

        return AuthResponseDTO(
            tokens=tokens,
            user=user_response,
            is_new_user=False,
        )

    def _create_refresh_token(self, subject: str, remember_me: bool) -> str:
        """Create refresh token with optional extended TTL.

        Args:
            subject: User ID string.
            remember_me: If True, use 30-day TTL; otherwise, use standard 7-day TTL.

        Returns:
            JWT refresh token string.
        """
        return self.auth_service.create_refresh_token(subject, remember_me=remember_me)
