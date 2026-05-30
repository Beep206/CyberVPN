"""S1-ADM-002 admin RBAC matrix checks."""

from __future__ import annotations

from collections.abc import Iterable

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.auth.permissions import Permission, check_minimum_role, has_permission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.roles import require_permission, require_role


def _admin_user(role: AdminRole | str) -> AdminUserModel:
    role_value = role.value if isinstance(role, AdminRole) else role
    return AdminUserModel(
        login=f"s1-rbac-{role_value.replace('/', '-')}",
        email=f"{role_value.replace('/', '-')}@example.test",
        role=role_value,
    )


def _assert_permissions(
    role: AdminRole,
    *,
    allowed: Iterable[Permission],
    denied: Iterable[Permission],
) -> None:
    for permission in allowed:
        assert has_permission(role, permission), f"{role.value} should have {permission.value}"
    for permission in denied:
        assert not has_permission(role, permission), f"{role.value} should not have {permission.value}"


def test_stage1_owner_and_super_admin_have_complete_permission_set() -> None:
    for role in (AdminRole.OWNER_SUPER_ADMIN, AdminRole.SUPER_ADMIN):
        for permission in Permission:
            assert has_permission(role, permission), f"{role.value} should have {permission.value}"


def test_stage1_support_ops_finance_permission_matrix_is_separated() -> None:
    _assert_permissions(
        AdminRole.SUPPORT,
        allowed={
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.SUPPORT_TICKET_READ,
            Permission.SERVER_READ,
            Permission.MONITORING_READ,
            Permission.VPN_CREDENTIAL_REGENERATE,
        },
        denied={
            Permission.PAYMENT_READ,
            Permission.PAYMENT_CREATE,
            Permission.AUDIT_READ,
            Permission.WEBHOOK_READ,
            Permission.SERVER_UPDATE,
            Permission.SUBSCRIPTION_CREATE,
            Permission.MANAGE_INVITES,
        },
    )
    _assert_permissions(
        AdminRole.OPERATOR,
        allowed={
            Permission.USER_READ,
            Permission.SERVER_READ,
            Permission.SERVER_CREATE,
            Permission.SERVER_UPDATE,
            Permission.MONITORING_READ,
            Permission.SUBSCRIPTION_CREATE,
            Permission.VIEW_ANALYTICS,
        },
        denied={
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.PAYMENT_READ,
            Permission.PAYMENT_CREATE,
            Permission.AUDIT_READ,
            Permission.WEBHOOK_READ,
            Permission.VPN_CREDENTIAL_REGENERATE,
            Permission.MANAGE_INVITES,
            Permission.SUPPORT_TICKET_READ,
        },
    )
    _assert_permissions(
        AdminRole.FINANCE,
        allowed={
            Permission.USER_READ,
            Permission.PAYMENT_READ,
            Permission.AUDIT_READ,
            Permission.WEBHOOK_READ,
        },
        denied={
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.SERVER_READ,
            Permission.SERVER_UPDATE,
            Permission.MONITORING_READ,
            Permission.SUBSCRIPTION_CREATE,
            Permission.VPN_CREDENTIAL_REGENERATE,
            Permission.MANAGE_INVITES,
            Permission.VIEW_ANALYTICS,
            Permission.SUPPORT_TICKET_READ,
        },
    )


def test_stage1_minimum_role_matrix_is_not_linear_for_finance() -> None:
    assert check_minimum_role(AdminRole.FINANCE, AdminRole.FINANCE)
    assert check_minimum_role(AdminRole.ADMIN, AdminRole.FINANCE)
    assert check_minimum_role(AdminRole.OWNER_SUPER_ADMIN, AdminRole.FINANCE)

    assert not check_minimum_role(AdminRole.FINANCE, AdminRole.SUPPORT)
    assert not check_minimum_role(AdminRole.FINANCE, AdminRole.OPERATOR)
    assert not check_minimum_role(AdminRole.FINANCE, AdminRole.ADMIN)
    assert not check_minimum_role(AdminRole.SUPPORT, AdminRole.FINANCE)
    assert not check_minimum_role(AdminRole.OPERATOR, AdminRole.FINANCE)


@pytest.mark.asyncio
async def test_stage1_permission_dependency_enforces_cross_role_denials() -> None:
    payment_read = require_permission(Permission.PAYMENT_READ)
    credential_regen = require_permission(Permission.VPN_CREDENTIAL_REGENERATE)
    subscription_create = require_permission(Permission.SUBSCRIPTION_CREATE)
    server_update = require_permission(Permission.SERVER_UPDATE)
    support_ticket_read = require_permission(Permission.SUPPORT_TICKET_READ)

    assert await payment_read(_admin_user(AdminRole.FINANCE))
    assert await credential_regen(_admin_user(AdminRole.SUPPORT))
    assert await subscription_create(_admin_user(AdminRole.OPERATOR))
    assert await server_update(_admin_user(AdminRole.OPERATOR))
    assert await support_ticket_read(_admin_user(AdminRole.SUPPORT))

    with pytest.raises(HTTPException) as finance_vpn_error:
        await credential_regen(_admin_user(AdminRole.FINANCE))
    assert finance_vpn_error.value.status_code == 403
    assert finance_vpn_error.value.detail == "Missing permission: vpn_credential_regenerate"

    with pytest.raises(HTTPException) as support_payment_error:
        await payment_read(_admin_user(AdminRole.SUPPORT))
    assert support_payment_error.value.status_code == 403
    assert support_payment_error.value.detail == "Missing permission: payment_read"

    with pytest.raises(HTTPException) as ops_payment_error:
        await payment_read(_admin_user(AdminRole.OPERATOR))
    assert ops_payment_error.value.status_code == 403
    assert ops_payment_error.value.detail == "Missing permission: payment_read"

    with pytest.raises(HTTPException) as support_subscription_error:
        await subscription_create(_admin_user(AdminRole.SUPPORT))
    assert support_subscription_error.value.status_code == 403
    assert support_subscription_error.value.detail == "Missing permission: subscription_create"

    for denied_role in (AdminRole.VIEWER, AdminRole.FINANCE):
        with pytest.raises(HTTPException) as support_ticket_error:
            await support_ticket_read(_admin_user(denied_role))
        assert support_ticket_error.value.status_code == 403
        assert support_ticket_error.value.detail == "Missing permission: support_ticket_read"


@pytest.mark.asyncio
async def test_stage1_role_dependency_rejects_wrong_or_invalid_roles() -> None:
    finance_role = require_role(AdminRole.FINANCE)
    support_role = require_role(AdminRole.SUPPORT)
    operator_role = require_role(AdminRole.OPERATOR)

    assert await finance_role(_admin_user(AdminRole.FINANCE))
    assert await finance_role(_admin_user(AdminRole.ADMIN))
    assert await support_role(_admin_user(AdminRole.SUPPORT))
    assert await operator_role(_admin_user(AdminRole.OPERATOR))

    with pytest.raises(HTTPException) as finance_support_error:
        await support_role(_admin_user(AdminRole.FINANCE))
    assert finance_support_error.value.status_code == 403
    assert finance_support_error.value.detail == "Requires minimum role: support"

    with pytest.raises(HTTPException) as support_finance_error:
        await finance_role(_admin_user(AdminRole.SUPPORT))
    assert support_finance_error.value.status_code == 403
    assert support_finance_error.value.detail == "Requires minimum role: finance"

    with pytest.raises(HTTPException) as invalid_role_error:
        await finance_role(_admin_user("legacy_root"))
    assert invalid_role_error.value.status_code == 403
    assert invalid_role_error.value.detail == "Invalid admin role"


@pytest.mark.asyncio
async def test_stage1_rbac_matrix_works_through_fastapi_dependency_pipeline() -> None:
    app = FastAPI()

    @app.get("/finance")
    async def finance_route(
        _: AdminUserModel = Depends(require_permission(Permission.PAYMENT_READ)),
    ) -> dict[str, str]:
        return {"surface": "finance"}

    @app.get("/support")
    async def support_route(
        _: AdminUserModel = Depends(require_permission(Permission.VPN_CREDENTIAL_REGENERATE)),
    ) -> dict[str, str]:
        return {"surface": "support"}

    @app.get("/ops")
    async def ops_route(
        _: AdminUserModel = Depends(require_permission(Permission.SERVER_UPDATE)),
    ) -> dict[str, str]:
        return {"surface": "ops"}

    async def request_as(role: AdminRole | str, path: str):
        async def fake_current_user() -> AdminUserModel:
            return _admin_user(role)

        app.dependency_overrides[get_current_active_user] = fake_current_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://admin.cyber-vpn.net") as client:
            return await client.get(path)

    assert (await request_as(AdminRole.FINANCE, "/finance")).status_code == 200
    assert (await request_as(AdminRole.SUPPORT, "/support")).status_code == 200
    assert (await request_as(AdminRole.OPERATOR, "/ops")).status_code == 200

    finance_on_support = await request_as(AdminRole.FINANCE, "/support")
    support_on_finance = await request_as(AdminRole.SUPPORT, "/finance")
    ops_on_finance = await request_as(AdminRole.OPERATOR, "/finance")
    finance_on_ops = await request_as(AdminRole.FINANCE, "/ops")
    invalid_role = await request_as("legacy_root", "/finance")

    assert finance_on_support.status_code == 403
    assert finance_on_support.json()["detail"] == "Missing permission: vpn_credential_regenerate"
    assert support_on_finance.status_code == 403
    assert support_on_finance.json()["detail"] == "Missing permission: payment_read"
    assert ops_on_finance.status_code == 403
    assert ops_on_finance.json()["detail"] == "Missing permission: payment_read"
    assert finance_on_ops.status_code == 403
    assert finance_on_ops.json()["detail"] == "Missing permission: server_update"
    assert invalid_role.status_code == 403
    assert invalid_role.json()["detail"] == "Invalid admin role"
