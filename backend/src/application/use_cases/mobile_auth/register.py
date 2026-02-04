"""Mobile user registration use case.

Handles registration of new mobile app users with device tracking.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.application.dto.mobile_auth import (
    AuthResponseDTO,
    RegisterRequestDTO,
    SubscriptionInfoDTO,
    SubscriptionStatus,
    TokenResponseDTO,
    UserResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import DuplicateUsernameError
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileRegisterUseCase:
    """Use case for registering new mobile app users.

    Creates a new mobile user account, registers the device,
    and returns authentication tokens.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService

    async def execute(self, request: RegisterRequestDTO) -> AuthResponseDTO:
        """Register a new mobile user.

        Args:
            request: Registration request with email, password, and device info.

        Returns:
            AuthResponseDTO with tokens and user data.

        Raises:
            DuplicateUsernameError: If email already exists.
        """
        # Check email uniqueness
        existing_user = await self.user_repo.get_by_email(request.email)
        if existing_user:
            raise DuplicateUsernameError(username=request.email)

        # Hash password
        password_hash = await self.auth_service.hash_password(request.password)

        # Create mobile user
        user = MobileUserModel(
            email=request.email,
            password_hash=password_hash,
            is_active=True,
            status="active",
        )
        created_user = await self.user_repo.create(user)

        # Register device
        device = MobileDeviceModel(
            device_id=request.device.device_id,
            platform=request.device.platform.value,
            platform_id=request.device.platform_id,
            os_version=request.device.os_version,
            app_version=request.device.app_version,
            device_model=request.device.device_model,
            push_token=request.device.push_token,
            user_id=created_user.id,
            last_active_at=datetime.now(timezone.utc),
        )
        await self.device_repo.create(device)

        # Generate tokens
        access_token = self.auth_service.create_access_token(
            subject=str(created_user.id),
            role="mobile_user",
            extra={"device_id": request.device.device_id},
        )
        refresh_token = self.auth_service.create_refresh_token(
            subject=str(created_user.id),
        )

        # Build response
        tokens = TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

        subscription = SubscriptionInfoDTO(
            status=SubscriptionStatus.NONE,
        )

        user_response = UserResponseDTO(
            id=created_user.id,
            email=created_user.email,
            username=created_user.username,
            status=created_user.status,
            telegram_id=created_user.telegram_id,
            telegram_username=created_user.telegram_username,
            created_at=created_user.created_at,
            subscription=subscription,
        )

        return AuthResponseDTO(
            tokens=tokens,
            user=user_response,
            is_new_user=True,
        )
