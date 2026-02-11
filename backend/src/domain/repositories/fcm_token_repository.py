"""Abstract repository interface for FCM token operations."""

from abc import ABC, abstractmethod
from typing import Literal
from uuid import UUID

from src.domain.entities.fcm_token import FCMToken


class FCMTokenRepository(ABC):
    """Repository interface for FCM token persistence."""

    @abstractmethod
    async def upsert(
        self,
        user_id: UUID,
        token: str,
        device_id: str,
        platform: Literal["android", "ios"],
    ) -> FCMToken:
        """Insert or update FCM token for a device.

        If a token already exists for this (user_id, device_id), replace it.

        Args:
            user_id: Admin user UUID
            token: FCM registration token from Firebase SDK
            device_id: Unique device identifier
            platform: Mobile platform (android/ios)

        Returns:
            The created or updated FCM token entity
        """
        ...

    @abstractmethod
    async def delete(
        self,
        user_id: UUID,
        device_id: str,
    ) -> None:
        """Remove FCM token for a specific device.

        Called on logout or when user disables push notifications.

        Args:
            user_id: Admin user UUID
            device_id: Device identifier whose token should be removed
        """
        ...

    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
    ) -> list[FCMToken]:
        """Retrieve all FCM tokens for a user (all their devices).

        Args:
            user_id: Admin user UUID

        Returns:
            List of FCM tokens for all user devices
        """
        ...

    @abstractmethod
    async def get_by_device(
        self,
        user_id: UUID,
        device_id: str,
    ) -> FCMToken | None:
        """Get FCM token for a specific user device.

        Args:
            user_id: Admin user UUID
            device_id: Device identifier

        Returns:
            FCM token if exists, None otherwise
        """
        ...
