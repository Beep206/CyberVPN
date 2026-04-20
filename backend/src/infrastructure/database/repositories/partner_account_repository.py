"""Repository for partner workspace accounts, roles, and memberships."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.partner_role import BUILTIN_PARTNER_ROLE_DEFINITIONS
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel


class PartnerAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_builtin_roles(self) -> list[PartnerRoleModel]:
        result = await self._session.execute(select(PartnerRoleModel))
        existing = list(result.scalars().all())
        existing_by_key = {role.role_key: role for role in existing}

        created: list[PartnerRoleModel] = []
        for definition in BUILTIN_PARTNER_ROLE_DEFINITIONS:
            existing_role = existing_by_key.get(definition.role_key)
            if existing_role is not None:
                expected_permissions = [permission.value for permission in definition.permissions]
                if (
                    existing_role.display_name != definition.display_name
                    or existing_role.description != definition.description
                    or sorted(existing_role.permission_keys) != sorted(expected_permissions)
                    or existing_role.is_system is not True
                ):
                    existing_role.display_name = definition.display_name
                    existing_role.description = definition.description
                    existing_role.permission_keys = expected_permissions
                    existing_role.is_system = True
                continue

            model = PartnerRoleModel(
                role_key=definition.role_key,
                display_name=definition.display_name,
                description=definition.description,
                permission_keys=[permission.value for permission in definition.permissions],
                is_system=True,
            )
            self._session.add(model)
            created.append(model)

        if created:
            await self._session.flush()
            existing.extend(created)

        return existing

    async def list_roles(self) -> list[PartnerRoleModel]:
        await self.ensure_builtin_roles()
        result = await self._session.execute(select(PartnerRoleModel).order_by(PartnerRoleModel.display_name.asc()))
        return list(result.scalars().all())

    async def get_role_by_key(self, role_key: str) -> PartnerRoleModel | None:
        await self.ensure_builtin_roles()
        result = await self._session.execute(select(PartnerRoleModel).where(PartnerRoleModel.role_key == role_key))
        return result.scalar_one_or_none()

    async def get_role_by_id(self, id: UUID) -> PartnerRoleModel | None:
        await self.ensure_builtin_roles()
        return await self._session.get(PartnerRoleModel, id)

    async def get_account_by_id(self, id: UUID) -> PartnerAccountModel | None:
        return await self._session.get(PartnerAccountModel, id)

    async def get_account_by_key(self, account_key: str) -> PartnerAccountModel | None:
        result = await self._session.execute(
            select(PartnerAccountModel).where(PartnerAccountModel.account_key == account_key)
        )
        return result.scalar_one_or_none()

    async def get_account_by_legacy_owner_user_id(self, user_id: UUID) -> PartnerAccountModel | None:
        result = await self._session.execute(
            select(PartnerAccountModel).where(PartnerAccountModel.legacy_owner_user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_account(self, model: PartnerAccountModel) -> PartnerAccountModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_account(self, model: PartnerAccountModel) -> PartnerAccountModel:
        await self._session.merge(model)
        await self._session.flush()
        return model

    async def list_accounts_for_admin_user(self, admin_user_id: UUID) -> list[PartnerAccountModel]:
        result = await self._session.execute(
            select(PartnerAccountModel)
            .join(
                PartnerAccountUserModel,
                PartnerAccountUserModel.partner_account_id == PartnerAccountModel.id,
            )
            .where(
                PartnerAccountUserModel.admin_user_id == admin_user_id,
                PartnerAccountUserModel.membership_status == "active",
            )
            .order_by(PartnerAccountModel.display_name.asc())
        )
        return list(result.scalars().all())

    async def list_accounts(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerAccountModel]:
        statement = select(PartnerAccountModel)

        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    PartnerAccountModel.display_name.ilike(pattern),
                    PartnerAccountModel.account_key.ilike(pattern),
                )
            )

        normalized_status = (status or "").strip()
        if normalized_status:
            statement = statement.where(PartnerAccountModel.status == normalized_status)

        result = await self._session.execute(
            statement
            .order_by(PartnerAccountModel.updated_at.desc(), PartnerAccountModel.display_name.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_membership(
        self,
        partner_account_id: UUID,
        admin_user_id: UUID,
    ) -> PartnerAccountUserModel | None:
        result = await self._session.execute(
            select(PartnerAccountUserModel).where(
                PartnerAccountUserModel.partner_account_id == partner_account_id,
                PartnerAccountUserModel.admin_user_id == admin_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_membership_by_id(self, membership_id: UUID) -> PartnerAccountUserModel | None:
        return await self._session.get(PartnerAccountUserModel, membership_id)

    async def list_memberships(self, partner_account_id: UUID) -> list[PartnerAccountUserModel]:
        result = await self._session.execute(
            select(PartnerAccountUserModel)
            .where(PartnerAccountUserModel.partner_account_id == partner_account_id)
            .order_by(PartnerAccountUserModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_membership(self, model: PartnerAccountUserModel) -> PartnerAccountUserModel:
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_membership(self, model: PartnerAccountUserModel) -> PartnerAccountUserModel:
        await self._session.merge(model)
        await self._session.flush()
        return model
