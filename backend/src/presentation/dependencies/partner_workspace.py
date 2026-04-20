"""Partner workspace access and permission dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db


@dataclass(frozen=True)
class PartnerWorkspaceAccess:
    workspace: PartnerAccountModel
    membership: PartnerAccountUserModel | None
    role: PartnerRoleModel | None
    permission_keys: frozenset[str]
    is_internal_admin_override: bool


def _is_internal_admin(user: AdminUserModel) -> bool:
    return AdminRole(user.role) in {AdminRole.ADMIN, AdminRole.SUPER_ADMIN}


async def get_partner_workspace_access(
    workspace_id: UUID,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceAccess:
    return await resolve_partner_workspace_access(
        workspace_id=workspace_id,
        current_user=current_user,
        db=db,
    )


async def resolve_partner_workspace_access(
    *,
    workspace_id: UUID,
    current_user: AdminUserModel,
    db: AsyncSession,
) -> PartnerWorkspaceAccess:
    repo = PartnerAccountRepository(db)
    workspace = await repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")

    if _is_internal_admin(current_user):
        return PartnerWorkspaceAccess(
            workspace=workspace,
            membership=None,
            role=None,
            permission_keys=frozenset(permission.value for permission in PartnerPermission),
            is_internal_admin_override=True,
        )

    membership = await repo.get_membership(workspace_id, current_user.id)
    if membership is None or membership.membership_status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner workspace access denied")

    role = await repo.get_role_by_id(membership.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner workspace role is missing")

    return PartnerWorkspaceAccess(
        workspace=workspace,
        membership=membership,
        role=role,
        permission_keys=frozenset(role.permission_keys),
        is_internal_admin_override=False,
    )


def require_partner_workspace_permission(permission: PartnerPermission):
    async def permission_checker(
        access: PartnerWorkspaceAccess = Depends(get_partner_workspace_access),
    ) -> PartnerWorkspaceAccess:
        if permission.value not in access.permission_keys:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing partner workspace permission: {permission.value}",
            )
        return access

    return permission_checker
