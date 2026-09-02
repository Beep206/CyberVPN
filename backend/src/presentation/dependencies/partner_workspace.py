"""Partner workspace access and permission dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.partner_permission import PartnerPermission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel
from src.infrastructure.database.models.partner_workspace_profile_model import PartnerWorkspaceProfileModel
from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_workspace_profile_repository import (
    PartnerWorkspaceProfileRepository,
)
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_web_auth_realm
from src.presentation.dependencies.database import get_db

_WORKSPACE_WRITE_PERMISSIONS = frozenset(
    {
        PartnerPermission.OPERATIONS_WRITE.value,
        PartnerPermission.MEMBERSHIP_WRITE.value,
        PartnerPermission.CODES_WRITE.value,
        PartnerPermission.PAYOUTS_WRITE.value,
        PartnerPermission.TRAFFIC_WRITE.value,
        PartnerPermission.INTEGRATIONS_WRITE.value,
        PartnerPermission.REMNAWAVE_WRITE.value,
        PartnerPermission.REMNAWAVE_EXECUTE.value,
        PartnerPermission.REMNAWAVE_SSH.value,
    }
)
_FROZEN_WORKSPACE_STATUSES = frozenset({"suspended", "rejected", "terminated"})
_EXCLUSIVE_REMNAWAVE_RESOURCE_TYPES = frozenset({"node", "service_identity", "profile", "integration"})


@dataclass(frozen=True)
class PartnerWorkspaceAccess:
    workspace: PartnerAccountModel
    membership: PartnerAccountUserModel | None
    role: PartnerRoleModel | None
    permission_keys: frozenset[str]
    is_internal_admin_override: bool


def _is_internal_admin(user: AdminUserModel) -> bool:
    return AdminRole(user.role) in {AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OWNER_SUPER_ADMIN}


async def get_partner_workspace_access(
    workspace_id: UUID,
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
    current_user: AdminUserModel = Depends(get_current_active_web_user),
    db: AsyncSession = Depends(get_db),
) -> PartnerWorkspaceAccess:
    if current_realm.realm_type != "partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner realm session is required for partner workspace routes",
        )
    return await resolve_partner_workspace_access(
        workspace_id=workspace_id,
        current_user=current_user,
        db=db,
        allow_internal_admin_override=False,
    )


async def resolve_partner_workspace_access(
    *,
    workspace_id: UUID,
    current_user: AdminUserModel,
    db: AsyncSession,
    allow_internal_admin_override: bool = True,
) -> PartnerWorkspaceAccess:
    repo = PartnerAccountRepository(db)
    workspace = await repo.get_account_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner workspace not found")

    if allow_internal_admin_override and _is_internal_admin(current_user):
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
        current_user: AdminUserModel = Depends(get_current_active_web_user),
        db: AsyncSession = Depends(get_db),
    ) -> PartnerWorkspaceAccess:
        await enforce_partner_workspace_permission(
            access=access,
            permission=permission,
            current_user=current_user,
            db=db,
        )
        return access

    return permission_checker


async def enforce_partner_workspace_permission(
    *,
    access: PartnerWorkspaceAccess,
    permission: PartnerPermission,
    current_user: AdminUserModel,
    db: AsyncSession,
) -> None:
    if permission.value not in access.permission_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing partner workspace permission: {permission.value}",
        )

    # Reject stale/frozen access before the policy lookup. Besides avoiding an
    # unnecessary query, this keeps capability checks fail-closed even when a
    # lightweight DB double is used by callers that cannot reach the MFA path.
    enforce_loaded_partner_workspace_permission(
        access=access,
        permission=permission,
        current_user=current_user,
        profile=None,
    )
    if permission.value in _WORKSPACE_WRITE_PERMISSIONS and not access.is_internal_admin_override:
        profile = await PartnerWorkspaceProfileRepository(db).get_by_account_id(access.workspace.id)
        enforce_loaded_partner_workspace_permission(
            access=access,
            permission=permission,
            current_user=current_user,
            profile=profile,
        )


def enforce_loaded_partner_workspace_permission(
    *,
    access: PartnerWorkspaceAccess,
    permission: PartnerPermission,
    current_user: AdminUserModel,
    profile: PartnerWorkspaceProfileModel | None,
) -> None:
    """Enforce workspace policy from rows already locked by a mutation.

    Privileged provider mutations must re-evaluate the same policy after their
    durable reservation commit. Accepting a loaded profile avoids a second,
    unlocked policy read while preserving this module as the sole owner of
    frozen-workspace and MFA semantics.
    """

    if permission.value not in access.permission_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing partner workspace permission: {permission.value}",
        )

    if permission.value not in _WORKSPACE_WRITE_PERMISSIONS or access.is_internal_admin_override:
        return

    if access.workspace.status in _FROZEN_WORKSPACE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner workspace is not writable in current status",
        )

    if profile is not None and profile.require_mfa_for_workspace and not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner workspace 2FA required for privileged action",
        )


async def enforce_partner_remnawave_resource_grant(
    *,
    access: PartnerWorkspaceAccess,
    resource_type: str,
    resource_uuid: UUID,
    permission: PartnerPermission,
    db: AsyncSession,
) -> PartnerRemnawaveResourceGrantModel:
    """Enforce an active exact object-level Remnawave grant.

    Missing or foreign objects deliberately return 404 to avoid making the
    partner API an existence oracle. The member's explicit role permission and
    an audited grant for this exact workspace object must both allow the
    operation. Browser SSH is admin-only and is never accepted here.
    """

    if permission is PartnerPermission.REMNAWAVE_SSH:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Browser SSH is admin-only")
    if permission.value not in access.permission_keys:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")
    filters = (
        PartnerRemnawaveResourceGrantModel.resource_type == resource_type,
        PartnerRemnawaveResourceGrantModel.resource_uuid == resource_uuid,
        PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
    )
    if resource_type in _EXCLUSIVE_REMNAWAVE_RESOURCE_TYPES:
        # The partial unique index is the concurrency guard. This global read
        # additionally fails closed if a request reaches an incompletely
        # migrated or corrupted database with cross-workspace duplicates.
        grants = list((await db.execute(select(PartnerRemnawaveResourceGrantModel).where(*filters))).scalars().all())
        grant = grants[0] if len(grants) == 1 else None
    else:
        grant = (
            await db.execute(
                select(PartnerRemnawaveResourceGrantModel).where(
                    PartnerRemnawaveResourceGrantModel.workspace_id == access.workspace.id,
                    *filters,
                )
            )
        ).scalar_one_or_none()
    if (
        grant is None
        or grant.workspace_id != access.workspace.id
        or grant.resource_type != resource_type
        or grant.resource_uuid != resource_uuid
        or grant.revoked_at is not None
        or permission.value not in grant.permission_keys
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave resource not found")
    return grant
