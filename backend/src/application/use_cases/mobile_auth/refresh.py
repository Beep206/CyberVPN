"""Mobile token refresh use case.

Handles JWT token refresh for mobile app users.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import (
    RefreshTokenRequestDTO,
    TokenResponseDTO,
)
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.application.use_cases.auth.refresh_token import RefreshTokenReplayError
from src.domain.exceptions import InvalidTokenError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class MobileRefreshUseCase:
    """Use case for refreshing mobile app authentication tokens.

    Validates refresh token, verifies device, and issues new token pair.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, request: RefreshTokenRequestDTO) -> TokenResponseDTO:
        """Refresh authentication tokens.

        Args:
            request: Refresh request with current refresh token and device ID.

        Returns:
            TokenResponseDTO with new access and refresh tokens.

        Raises:
            InvalidTokenError: If refresh token is invalid, expired, or device mismatch.
        """
        try:
            return await self._mobile_sessions().refresh(
                refresh_token=request.refresh_token,
                device_id=request.device_id,
            )
        except RefreshTokenReplayError:
            raise
        except InvalidTokenError:
            raise
        except Exception as exc:
            logger.warning("Mobile refresh failed: %s", exc)
            raise InvalidTokenError() from exc

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileRefreshUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
