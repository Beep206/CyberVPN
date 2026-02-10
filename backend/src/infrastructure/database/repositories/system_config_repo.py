"""Infrastructure repository for system_config table."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.system_config_model import SystemConfigModel


class SystemConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, key: str) -> SystemConfigModel | None:
        return await self._session.get(SystemConfigModel, key)

    async def get_value(self, key: str, default: Any = None) -> Any:
        model = await self._session.get(SystemConfigModel, key)
        if model is None:
            return default
        return model.value

    async def set(self, key: str, value: dict[str, Any], updated_by: UUID | None = None) -> SystemConfigModel:
        model = await self._session.get(SystemConfigModel, key)
        if model is None:
            model = SystemConfigModel(key=key, value=value, updated_by=updated_by)
            self._session.add(model)
        else:
            model.value = value
            if updated_by is not None:
                model.updated_by = updated_by
        await self._session.flush()
        return model

    async def get_all(self) -> list[SystemConfigModel]:
        result = await self._session.execute(select(SystemConfigModel).order_by(SystemConfigModel.key))
        return list(result.scalars().all())
