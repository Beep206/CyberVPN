from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel


class AdminUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> AdminUserModel | None:
        return await self._session.get(AdminUserModel, id)

    @staticmethod
    def _realm_scope_clause(realm_id: UUID | None, *, include_legacy_default: bool = False):
        if realm_id is None:
            return None
        if include_legacy_default:
            return or_(AdminUserModel.auth_realm_id == realm_id, AdminUserModel.auth_realm_id.is_(None))
        return AdminUserModel.auth_realm_id == realm_id

    async def get_by_login(
        self,
        login: str,
        *,
        realm_id: UUID | None = None,
        include_legacy_default: bool = False,
    ) -> AdminUserModel | None:
        stmt = select(AdminUserModel).where(AdminUserModel.login == login)
        realm_clause = self._realm_scope_clause(realm_id, include_legacy_default=include_legacy_default)
        if realm_clause is not None:
            stmt = stmt.where(realm_clause)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
        *,
        realm_id: UUID | None = None,
        include_legacy_default: bool = False,
    ) -> AdminUserModel | None:
        stmt = select(AdminUserModel).where(func.lower(AdminUserModel.email) == email.lower())
        realm_clause = self._realm_scope_clause(realm_id, include_legacy_default=include_legacy_default)
        if realm_clause is not None:
            stmt = stmt.where(realm_clause)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_login_or_email(
        self,
        login_or_email: str,
        *,
        realm_id: UUID | None = None,
        include_legacy_default: bool = False,
    ) -> AdminUserModel | None:
        stmt = select(AdminUserModel).where(
            (AdminUserModel.login == login_or_email) | (func.lower(AdminUserModel.email) == login_or_email.lower())
        )
        realm_clause = self._realm_scope_clause(realm_id, include_legacy_default=include_legacy_default)
        if realm_clause is not None:
            stmt = stmt.where(realm_clause)
        result = await self._session.execute(stmt)
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

    async def list_by_ids(self, ids: list[UUID]) -> list[AdminUserModel]:
        if not ids:
            return []

        result = await self._session.execute(select(AdminUserModel).where(AdminUserModel.id.in_(ids)))
        return list(result.scalars().all())
