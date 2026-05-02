"""List active mobile devices for the current user."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.mobile_auth import DeviceSessionDTO
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository


@dataclass
class MobileListDevicesUseCase:
    """Return device registrations associated with the current mobile user."""

    user_repo: MobileUserRepository

    async def execute(self, user_id: UUID) -> list[DeviceSessionDTO]:
        user = await self.user_repo.get_by_id_with_devices(user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        return [
            DeviceSessionDTO(
                id=device.device_id,
                name=device.device_model,
                platform=device.platform,
                ip_address=None,
                last_active_at=device.last_active_at,
                created_at=device.registered_at,
                is_current=False,
            )
            for device in user.devices
        ]
