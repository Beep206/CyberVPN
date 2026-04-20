"""Read partner workspace details with account-level stats."""

from __future__ import annotations

from uuid import UUID

from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository


class GetPartnerWorkspaceUseCase:
    def __init__(
        self,
        partner_account_repo: PartnerAccountRepository,
        partner_repo: PartnerRepository,
    ) -> None:
        self._partner_account_repo = partner_account_repo
        self._partner_repo = partner_repo

    async def execute(self, partner_account_id: UUID) -> dict:
        account = await self._partner_account_repo.get_account_by_id(partner_account_id)
        if account is None:
            msg = f"Partner workspace not found: {partner_account_id}"
            raise ValueError(msg)

        memberships = await self._partner_account_repo.list_memberships(partner_account_id)
        roles = await self._partner_account_repo.list_roles()
        role_by_id = {role.id: role for role in roles}
        admin_users = await AdminUserRepository(self._partner_account_repo._session).list_by_ids(
            [membership.admin_user_id for membership in memberships],
        )
        operator_by_id = {item.id: item for item in admin_users}
        stats_map = await self._partner_repo.get_account_stats_map([partner_account_id])

        return {
            "account": account,
            "memberships": memberships,
            "role_by_id": role_by_id,
            "operator_by_id": operator_by_id,
            "stats": stats_map.get(
                partner_account_id,
                {
                    "code_count": 0,
                    "active_code_count": 0,
                    "total_clients": 0,
                    "total_earned": 0,
                    "last_activity_at": None,
                },
            ),
        }
