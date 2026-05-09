import pytest

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.permissions import (
    Permission,
    can_assign_role,
    check_minimum_role,
    has_permission,
)
from src.domain.enums import AdminRole


class TestAuthService:
    @pytest.mark.asyncio
    async def test_hash_and_verify_password(self):
        hashed = await AuthService.hash_password("testpassword123")
        assert AuthService.verify_password("testpassword123", hashed)
        assert not AuthService.verify_password("wrong", hashed)


class TestPermissions:
    def test_owner_super_admin_has_all(self):
        for perm in Permission:
            assert has_permission(AdminRole.OWNER_SUPER_ADMIN, perm)

    def test_super_admin_has_all(self):
        for perm in Permission:
            assert has_permission(AdminRole.SUPER_ADMIN, perm)

    def test_viewer_limited(self):
        assert has_permission(AdminRole.VIEWER, Permission.USER_READ)
        assert not has_permission(AdminRole.VIEWER, Permission.USER_CREATE)
        assert not has_permission(AdminRole.VIEWER, Permission.SERVER_DELETE)

    def test_role_hierarchy(self):
        assert check_minimum_role(AdminRole.OWNER_SUPER_ADMIN, AdminRole.SUPER_ADMIN)
        assert check_minimum_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN)
        assert check_minimum_role(AdminRole.ADMIN, AdminRole.ADMIN)
        assert check_minimum_role(AdminRole.FINANCE, AdminRole.FINANCE)
        assert not check_minimum_role(AdminRole.FINANCE, AdminRole.SUPPORT)
        assert not check_minimum_role(AdminRole.SUPPORT, AdminRole.FINANCE)
        assert not check_minimum_role(AdminRole.VIEWER, AdminRole.ADMIN)

    def test_operator_permissions(self):
        assert has_permission(AdminRole.OPERATOR, Permission.USER_READ)
        assert has_permission(AdminRole.OPERATOR, Permission.SERVER_UPDATE)
        assert has_permission(AdminRole.OPERATOR, Permission.SUBSCRIPTION_CREATE)
        assert not has_permission(AdminRole.OPERATOR, Permission.USER_CREATE)
        assert not has_permission(AdminRole.OPERATOR, Permission.PAYMENT_READ)
        assert not has_permission(AdminRole.OPERATOR, Permission.MANAGE_ADMINS)

    def test_finance_permissions(self):
        assert has_permission(AdminRole.FINANCE, Permission.USER_READ)
        assert has_permission(AdminRole.FINANCE, Permission.PAYMENT_READ)
        assert has_permission(AdminRole.FINANCE, Permission.AUDIT_READ)
        assert has_permission(AdminRole.FINANCE, Permission.WEBHOOK_READ)
        assert not has_permission(AdminRole.FINANCE, Permission.USER_UPDATE)
        assert not has_permission(AdminRole.FINANCE, Permission.PAYMENT_CREATE)
        assert not has_permission(AdminRole.FINANCE, Permission.VPN_CREDENTIAL_REGENERATE)
        assert not has_permission(AdminRole.FINANCE, Permission.SERVER_UPDATE)

    def test_role_assignment_order_includes_finance(self):
        assert can_assign_role(AdminRole.ADMIN, AdminRole.FINANCE)
        assert can_assign_role(AdminRole.SUPER_ADMIN, AdminRole.OPERATOR)
        assert not can_assign_role(AdminRole.FINANCE, AdminRole.SUPPORT)
        assert not can_assign_role(AdminRole.OPERATOR, AdminRole.ADMIN)
