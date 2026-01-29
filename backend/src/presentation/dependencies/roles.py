from fastapi import Depends, HTTPException, status

from src.application.use_cases.auth.permissions import Permission, check_minimum_role, has_permission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user


def require_role(minimum_role: AdminRole):
    async def role_checker(
        user: AdminUserModel = Depends(get_current_active_user),
    ) -> AdminUserModel:
        user_role = AdminRole(user.role)
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
        user_role = AdminRole(user.role)
        if not has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return user
    return permission_checker
