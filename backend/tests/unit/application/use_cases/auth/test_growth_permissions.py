from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import AdminRole
from src.presentation.dependencies.roles import require_permission

GROWTH_PERMISSIONS = (
    Permission.GROWTH_CAMPAIGNS_READ,
    Permission.GROWTH_CAMPAIGNS_WRITE,
    Permission.GROWTH_CAMPAIGNS_PUBLISH,
    Permission.GROWTH_CAMPAIGNS_PAUSE,
    Permission.GROWTH_CAMPAIGNS_REVOKE,
    Permission.GROWTH_RULES_VIEW,
    Permission.GROWTH_RULES_EDIT,
    Permission.GROWTH_RULES_VALIDATE,
    Permission.GROWTH_RULES_PUBLISH,
    Permission.GROWTH_RULES_APPROVE,
)


def _admin_user(role: AdminRole) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), role=role.value, totp_enabled=False)


def _admin_realm() -> RealmResolution:
    return RealmResolution(
        auth_realm=SimpleNamespace(
            id=uuid4(),
            realm_key="admin",
            realm_type="admin",
            audience="cybervpn:admin",
            cookie_namespace="admin",
        ),
        source="test",
    )


def test_growth_permissions_are_reserved_for_admin_level_roles() -> None:
    for role in (AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OWNER_SUPER_ADMIN):
        for permission in GROWTH_PERMISSIONS:
            assert has_permission(role, permission)

    for role in (AdminRole.VIEWER, AdminRole.SUPPORT, AdminRole.FINANCE, AdminRole.OPERATOR):
        for permission in GROWTH_PERMISSIONS:
            assert not has_permission(role, permission)


@pytest.mark.asyncio
async def test_growth_rule_validation_dependency_rejects_analytics_only_viewer() -> None:
    checker = require_permission(Permission.GROWTH_RULES_VALIDATE)

    with pytest.raises(HTTPException) as exc_info:
        await checker(user=_admin_user(AdminRole.VIEWER), current_realm=_admin_realm())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Missing permission: growth.rules.validate"


@pytest.mark.asyncio
async def test_growth_campaign_publish_dependency_allows_admin() -> None:
    checker = require_permission(Permission.GROWTH_CAMPAIGNS_PUBLISH)
    user = _admin_user(AdminRole.ADMIN)

    resolved = await checker(user=user, current_realm=_admin_realm())

    assert resolved is user
