"""Remove a registered mobile device/session."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.exceptions import UserNotFoundError, ValidationError
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileRemoveDeviceUseCase:
    """Delete a mobile device registration owned by the current user."""

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository

    async def execute(self, *, user_id: UUID, device_id: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        device = await self.device_repo.get_by_device_id_and_user(device_id=device_id, user_id=user_id)
        if device is None:
            raise ValidationError("Device not found")

        await self.device_repo.delete(device)
