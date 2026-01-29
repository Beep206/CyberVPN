from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.permissions import Permission, has_permission, check_minimum_role
from src.domain.enums import AdminRole


class TestAuthService:
    def test_hash_and_verify_password(self):
        service = AuthService.__new__(AuthService)
        hashed = AuthService.hash_password("testpassword123")
        assert AuthService.verify_password("testpassword123", hashed)
        assert not AuthService.verify_password("wrong", hashed)


class TestPermissions:
    def test_super_admin_has_all(self):
        for perm in Permission:
            assert has_permission(AdminRole.SUPER_ADMIN, perm)

    def test_viewer_limited(self):
        assert has_permission(AdminRole.VIEWER, Permission.USER_READ)
        assert not has_permission(AdminRole.VIEWER, Permission.USER_CREATE)
        assert not has_permission(AdminRole.VIEWER, Permission.SERVER_DELETE)

    def test_role_hierarchy(self):
        assert check_minimum_role(AdminRole.SUPER_ADMIN, AdminRole.ADMIN)
        assert check_minimum_role(AdminRole.ADMIN, AdminRole.ADMIN)
        assert not check_minimum_role(AdminRole.VIEWER, AdminRole.ADMIN)

    def test_operator_permissions(self):
        assert has_permission(AdminRole.OPERATOR, Permission.USER_READ)
        assert has_permission(AdminRole.OPERATOR, Permission.USER_CREATE)
        assert has_permission(AdminRole.OPERATOR, Permission.PAYMENT_READ)
        assert not has_permission(AdminRole.OPERATOR, Permission.MANAGE_ADMINS)
