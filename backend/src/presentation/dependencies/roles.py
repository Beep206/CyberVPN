from fastapi import Depends, HTTPException, status

from src.application.use_cases.auth.permissions import Permission, check_minimum_role, has_permission
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user


def _resolve_admin_role(user: AdminUserModel) -> AdminRole:
    try:
        return AdminRole(user.role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin role",
        ) from exc


def _enforce_admin_2fa(user: AdminUserModel) -> None:
    if not settings.admin_2fa_required:
        return
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin 2FA required",
        )


def require_role(minimum_role: AdminRole):
    async def role_checker(
        user: AdminUserModel = Depends(get_current_active_user),
    ) -> AdminUserModel:
        user_role = _resolve_admin_role(user)
        _enforce_admin_2fa(user)
        if not check_minimum_role(user_role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires minimum role: {minimum_role.value}",
            )
        return user

    return role_checker


def require_permission(permission: Permission):
    async def permission_checker(
        user: AdminUserModel = Depends(get_current_active_user),
    ) -> AdminUserModel:
        user_role = _resolve_admin_role(user)
        _enforce_admin_2fa(user)
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return user

    return permission_checker
