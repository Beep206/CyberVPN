"""Mobile device registration use case.

Handles device registration and updates for mobile app users.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.dto.mobile_auth import (
    DeviceInfoDTO,
    DeviceResponseDTO,
)
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.repositories.mobile_user_repo import (
    MobileDeviceRepository,
    MobileUserRepository,
)


@dataclass
class MobileDeviceRegistrationUseCase:
    """Use case for registering or updating mobile device.

    Handles device registration for push notifications and session management.
    """

    user_repo: MobileUserRepository
    device_repo: MobileDeviceRepository

    async def execute(self, user_id: UUID, device: DeviceInfoDTO) -> DeviceResponseDTO:
        """Register or update a mobile device.

        Args:
            user_id: UUID of the authenticated user.
            device: Device information to register or update.

        Returns:
            DeviceResponseDTO with registration confirmation.

        Raises:
            UserNotFoundError: If user not found or inactive.
        """
        # Verify user exists and is active
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(identifier=str(user_id))

        # Check if device already registered
        existing_device = await self.device_repo.get_by_device_id_and_user(
            device_id=device.device_id,
            user_id=user_id,
        )

        now = datetime.now(timezone.utc)

        if existing_device:
            # Update existing device
            existing_device.platform = device.platform.value
            existing_device.platform_id = device.platform_id
            existing_device.os_version = device.os_version
            existing_device.app_version = device.app_version
            existing_device.device_model = device.device_model
            existing_device.push_token = device.push_token
            existing_device.last_active_at = now
            await self.device_repo.update(existing_device)

            return DeviceResponseDTO(
                device_id=existing_device.device_id,
                registered_at=existing_device.registered_at,
                last_active_at=now,
            )
        else:
            # Create new device registration
            new_device = MobileDeviceModel(
                device_id=device.device_id,
                platform=device.platform.value,
                platform_id=device.platform_id,
                os_version=device.os_version,
                app_version=device.app_version,
                device_model=device.device_model,
                push_token=device.push_token,
                user_id=user_id,
                last_active_at=now,
            )
            created_device = await self.device_repo.create(new_device)

            return DeviceResponseDTO(
                device_id=created_device.device_id,
                registered_at=created_device.registered_at,
                last_active_at=now,
            )
