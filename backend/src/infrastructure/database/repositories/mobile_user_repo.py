"""Repository for mobile user database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models.mobile_device_model import MobileDeviceModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel


class MobileUserRepository:
    """Repository for mobile user CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> MobileUserModel | None:
        """Get mobile user by UUID."""
        return await self._session.get(MobileUserModel, id)

    async def get_by_id_with_devices(self, id: UUID) -> MobileUserModel | None:
        """Get mobile user by UUID with devices eagerly loaded."""
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.id == id).options(selectinload(MobileUserModel.devices))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> MobileUserModel | None:
        """Get mobile user by email address."""
        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.email == email))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> MobileUserModel | None:
        """Get mobile user by Telegram ID."""
        result = await self._session.execute(select(MobileUserModel).where(MobileUserModel.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_remnawave_uuid(self, remnawave_uuid: str) -> MobileUserModel | None:
        """Get mobile user by Remnawave VPN user UUID."""
        result = await self._session.execute(
            select(MobileUserModel).where(MobileUserModel.remnawave_uuid == remnawave_uuid)
        )
        return result.scalar_one_or_none()

    async def create(self, model: MobileUserModel) -> MobileUserModel:
        """Create new mobile user."""
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: MobileUserModel) -> MobileUserModel:
        """Update existing mobile user."""
        await self._session.merge(model)
        await self._session.flush()
        return model


class MobileDeviceRepository:
    """Repository for mobile device CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_device_id_and_user(self, device_id: str, user_id: UUID) -> MobileDeviceModel | None:
        """Get device by device_id and user_id combination."""
        result = await self._session.execute(
            select(MobileDeviceModel).where(
                MobileDeviceModel.device_id == device_id,
                MobileDeviceModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_devices(self, user_id: UUID) -> list[MobileDeviceModel]:
        """Get all devices for a user."""
        result = await self._session.execute(select(MobileDeviceModel).where(MobileDeviceModel.user_id == user_id))
        return list(result.scalars().all())

    async def create(self, model: MobileDeviceModel) -> MobileDeviceModel:
        """Create new device registration."""
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: MobileDeviceModel) -> MobileDeviceModel:
        """Update device information."""
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def delete(self, model: MobileDeviceModel) -> None:
        """Delete device registration."""
        await self._session.delete(model)
        await self._session.flush()
