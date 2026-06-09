"""List active mobile devices for the current user."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.mobile_auth import DeviceSessionDTO
from src.application.services.auth_service import AuthService
from src.application.services.mobile_session import MobileSessionService
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileDeviceRepository, MobileUserRepository


@dataclass
class MobileListDevicesUseCase:
    """Return device registrations associated with the current mobile user."""

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository
    auth_service: AuthService
    session: AsyncSession | None = None
    mobile_session_service: MobileSessionService | None = None

    async def execute(self, user_id: UUID) -> list[DeviceSessionDTO]:
        try:
            return await self._mobile_sessions().list_devices(user_id=user_id)
        except UserNotFoundError:
            raise

    def _mobile_sessions(self) -> MobileSessionService:
        if self.mobile_session_service is not None:
            return self.mobile_session_service
        if self.session is None:
            raise RuntimeError("MobileListDevicesUseCase requires session-backed mobile sessions")
        return MobileSessionService(
            session=self.session,
            auth_service=self.auth_service,
            user_repo=self.user_repo,
            device_repo=self.device_repo,
        )
