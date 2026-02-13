from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class AdminUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> AdminUserModel | None:
        return await self._session.get(AdminUserModel, id)

    async def get_by_login(self, login: str) -> AdminUserModel | None:
        result = await self._session.execute(select(AdminUserModel).where(AdminUserModel.login == login))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> AdminUserModel | None:
        result = await self._session.execute(
            select(AdminUserModel).where(func.lower(AdminUserModel.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_login_or_email(self, login_or_email: str) -> AdminUserModel | None:
        result = await self._session.execute(
            select(AdminUserModel).where(
                (AdminUserModel.login == login_or_email) | (AdminUserModel.email == login_or_email)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, model: AdminUserModel) -> AdminUserModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update(self, model: AdminUserModel) -> AdminUserModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def get_by_telegram_id(self, telegram_id: int) -> AdminUserModel | None:
        result = await self._session.execute(select(AdminUserModel).where(AdminUserModel.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_all(self, offset: int = 0, limit: int = 100) -> list[AdminUserModel]:
        result = await self._session.execute(select(AdminUserModel).offset(offset).limit(limit))
        return list(result.scalars().all())
