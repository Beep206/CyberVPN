"""Mobile token refresh use case.

Handles JWT token refresh for mobile app users.
"""

from dataclasses import dataclass

from src.application.dto.mobile_auth import (
    RefreshTokenRequestDTO,
    TokenResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.config.settings import settings
from src.domain.exceptions import InvalidTokenError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileRefreshUseCase:
    """Use case for refreshing mobile app authentication tokens.

    Validates refresh token, verifies device, and issues new token pair.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService

    async def execute(self, request: RefreshTokenRequestDTO) -> TokenResponseDTO:
        """Refresh authentication tokens.

        Args:
            request: Refresh request with current refresh token and device ID.

        Returns:
            TokenResponseDTO with new access and refresh tokens.

        Raises:
            InvalidTokenError: If refresh token is invalid, expired, or device mismatch.
        """
        # Decode and validate refresh token
        try:
            payload = self.auth_service.decode_token(request.refresh_token)
        except Exception:
            raise InvalidTokenError()

        # Verify token type
        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        # Verify user exists and is active
        from uuid import UUID

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise InvalidTokenError()

        # Verify device is registered to this user
        device = await self.device_repo.get_by_device_id_and_user(
            device_id=request.device_id,
            user_id=user.id,
        )
        if not device:
            raise InvalidTokenError()

        # Generate new tokens
        access_token = self.auth_service.create_access_token(
            subject=str(user.id),
            role="mobile_user",
            extra={"device_id": request.device_id},
        )
        refresh_token = self.auth_service.create_refresh_token(
            subject=str(user.id),
        )

        return TokenResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
