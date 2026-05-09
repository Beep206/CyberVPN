"""S1-ADM-003 admin 2FA enforcement checks."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.auth.permissions import Permission
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.roles import require_permission


def _admin_user(
    role: AdminRole | str = AdminRole.FINANCE,
    *,
    totp_enabled: bool = False,
) -> AdminUserModel:
    role_value = role.value if isinstance(role, AdminRole) else role
    return AdminUserModel(
        login=f"s1-2fa-{role_value.replace('/', '-')}",
        email=f"{role_value.replace('/', '-')}@example.test",
        role=role_value,
        is_active=True,
        totp_enabled=totp_enabled,
    )


@pytest.mark.asyncio
async def test_stage1_admin_permission_denies_user_without_2fa_when_required(monkeypatch) -> None:
    monkeypatch.setattr("src.presentation.dependencies.roles.settings.admin_2fa_required", True)
    payment_read = require_permission(Permission.PAYMENT_READ)

    with pytest.raises(HTTPException) as exc_info:
        await payment_read(_admin_user(AdminRole.FINANCE, totp_enabled=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin 2FA required"


@pytest.mark.asyncio
async def test_stage1_admin_permission_allows_user_with_2fa_when_required(monkeypatch) -> None:
    monkeypatch.setattr("src.presentation.dependencies.roles.settings.admin_2fa_required", True)
    payment_read = require_permission(Permission.PAYMENT_READ)

    assert await payment_read(_admin_user(AdminRole.FINANCE, totp_enabled=True))


@pytest.mark.asyncio
async def test_stage1_admin_2fa_gate_can_be_disabled_for_local_development(monkeypatch) -> None:
    monkeypatch.setattr("src.presentation.dependencies.roles.settings.admin_2fa_required", False)
    payment_read = require_permission(Permission.PAYMENT_READ)

    assert await payment_read(_admin_user(AdminRole.FINANCE, totp_enabled=False))


@pytest.mark.asyncio
async def test_stage1_invalid_role_still_fails_closed_before_2fa_check(monkeypatch) -> None:
    monkeypatch.setattr("src.presentation.dependencies.roles.settings.admin_2fa_required", True)
    payment_read = require_permission(Permission.PAYMENT_READ)

    with pytest.raises(HTTPException) as exc_info:
        await payment_read(_admin_user("legacy_root", totp_enabled=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid admin role"


@pytest.mark.asyncio
async def test_stage1_admin_2fa_enforced_through_fastapi_dependency_pipeline(monkeypatch) -> None:
    monkeypatch.setattr("src.presentation.dependencies.roles.settings.admin_2fa_required", True)
    app = FastAPI()

    @app.get("/finance")
    async def finance_route(
        _: AdminUserModel = Depends(require_permission(Permission.PAYMENT_READ)),
    ) -> dict[str, str]:
        return {"surface": "finance"}

    @app.get("/2fa-setup-like")
    async def two_factor_setup_like_route(
        _: AdminUserModel = Depends(get_current_active_user),
    ) -> dict[str, str]:
        return {"surface": "2fa_setup"}

    async def request_as(user: AdminUserModel, path: str):
        async def fake_current_user() -> AdminUserModel:
            return user

        app.dependency_overrides[get_current_active_user] = fake_current_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://admin.cyber-vpn.net") as client:
            return await client.get(path)

    without_2fa = await request_as(_admin_user(AdminRole.FINANCE, totp_enabled=False), "/finance")
    with_2fa = await request_as(_admin_user(AdminRole.FINANCE, totp_enabled=True), "/finance")
    setup_without_2fa = await request_as(_admin_user(AdminRole.FINANCE, totp_enabled=False), "/2fa-setup-like")

    assert without_2fa.status_code == 403
    assert without_2fa.json()["detail"] == "Admin 2FA required"
    assert with_2fa.status_code == 200
    assert setup_without_2fa.status_code == 200
