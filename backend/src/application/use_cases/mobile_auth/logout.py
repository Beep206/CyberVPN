"""Mobile logout use case.

Handles logout and token revocation for mobile app users.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from src.application.dto.mobile_auth import LogoutRequestDTO
from src.application.services.auth_service import AuthService
from src.domain.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileLogoutUseCase:
    """Use case for logging out mobile app users.

    Validates refresh token and optionally removes device registration.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService

    async def execute(self, request: LogoutRequestDTO, remove_device: bool = False) -> None:
        """Logout a mobile user.

        Args:
            request: Logout request with refresh token and device ID.
            remove_device: If True, removes device registration entirely.

        Raises:
            InvalidTokenError: If refresh token is invalid or device mismatch.
        """
        # Decode and validate refresh token
        try:
            payload = self.auth_service.decode_token(request.refresh_token)
        except Exception as e:
            logger.warning("Mobile logout token decode failed: %s", e)
            raise InvalidTokenError()

        # Verify token type
        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        # Verify user exists
        from uuid import UUID

        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user:
            raise InvalidTokenError()

        # Verify device belongs to this user
        device = await self.device_repo.get_by_device_id_and_user(
            device_id=request.device_id,
            user_id=user.id,
        )
        if not device:
            raise InvalidTokenError()

        # Update device last active or remove it
        if remove_device:
            await self.device_repo.delete(device)
        else:
            # Just mark as inactive by clearing push token
            device.push_token = None
            device.last_active_at = datetime.now(UTC)
            await self.device_repo.update(device)

        # Note: For a more complete implementation, we would store refresh tokens
        # in the database and mark them as revoked. This basic implementation
        # relies on token expiration and device validation.
