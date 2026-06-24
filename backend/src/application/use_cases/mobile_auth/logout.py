"""Mobile logout use case.

Handles logout and token revocation for mobile app users.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import LogoutRequestDTO
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.use_cases.auth.logout import LogoutResult
from src.domain.exceptions import InvalidTokenError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class MobileLogoutUseCase:
    """Use case for logging out mobile app users.

    Validates refresh token and optionally removes device registration.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, request: LogoutRequestDTO, remove_device: bool = False) -> LogoutResult:
        """Logout a mobile user.

        Args:
            request: Logout request with refresh token and device ID.
            remove_device: If True, removes device registration entirely.

        Raises:
            InvalidTokenError: If refresh token is invalid or device mismatch.
        """
        try:
            return await self._mobile_sessions().logout(
                refresh_token=request.refresh_token,
                device_id=request.device_id,
            )
        except InvalidTokenError:
            raise
        except Exception as exc:
            logger.warning("Mobile logout failed: %s", exc)
            raise InvalidTokenError() from exc

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileLogoutUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
