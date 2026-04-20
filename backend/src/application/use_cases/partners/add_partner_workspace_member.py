"""Partner workspace membership management."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository


class AddPartnerWorkspaceMemberUseCase:
    def __init__(self, session: AsyncSession, partner_account_repo: PartnerAccountRepository) -> None:
        self._session = session
        self._repo = partner_account_repo

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        admin_user_id: UUID,
        role_key: str,
        invited_by_admin_user_id: UUID | None,
    ) -> PartnerAccountUserModel:
        account = await self._repo.get_account_by_id(partner_account_id)
        if account is None:
            msg = f"Partner workspace not found: {partner_account_id}"
            raise ValueError(msg)

        operator = await self._session.get(AdminUserModel, admin_user_id)
        if operator is None:
            msg = f"Partner operator not found: {admin_user_id}"
            raise ValueError(msg)

        role = await self._repo.get_role_by_key(role_key)
        if role is None:
            msg = f"Partner workspace role not found: {role_key}"
            raise ValueError(msg)

        membership = await self._repo.get_membership(partner_account_id, admin_user_id)
        if membership is None:
            membership = PartnerAccountUserModel(
                partner_account_id=partner_account_id,
                admin_user_id=admin_user_id,
                role_id=role.id,
                membership_status="active",
                invited_by_admin_user_id=invited_by_admin_user_id,
            )
            return await self._repo.create_membership(membership)

        membership.role_id = role.id
        membership.membership_status = "active"
        membership.invited_by_admin_user_id = invited_by_admin_user_id
        return await self._repo.update_membership(membership)
