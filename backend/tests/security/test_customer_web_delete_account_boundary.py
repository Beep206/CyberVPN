"""Customer web account deletion must use the durable privacy workflow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.mobile_auth.delete_account import MobileDeleteAccountUseCase
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway
from src.presentation.api.v1.auth import routes as auth_routes
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.auth_realms import get_request_web_auth_realm
from src.presentation.dependencies.database import get_db


def _realm(realm_type: str) -> RealmResolution:
    return RealmResolution(
        auth_realm=AuthRealmModel(
            id=uuid4(),
            realm_key=realm_type,
            realm_type=realm_type,
            display_name=f"{realm_type} realm",
            audience=f"cybervpn:{realm_type}",
            cookie_namespace=realm_type,
            is_default=True,
        ),
        source="test",
    )


async def _delete_request(
    *,
    realm_type: str,
    path: str,
    db: AsyncMock,
    redis_client: AsyncMock,
) -> tuple[object, SimpleNamespace]:
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/v1")
    current_user = SimpleNamespace(id=uuid4(), is_active=True, deleted_at=None)

    app.dependency_overrides[get_current_active_web_user] = lambda: current_user
    app.dependency_overrides[get_request_web_auth_realm] = lambda: _realm(realm_type)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth_routes.get_redis] = lambda: redis_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://my.cyber-vpn.net",
    ) as client:
        response = await client.delete(path)
    return response, current_user


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/auth/me", "/api/v1/auth/me/"])
async def test_customer_web_delete_account_requires_privacy_request_before_any_mutation(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    redis_client = AsyncMock()
    admin_delete_constructor = Mock()
    admin_repo_constructor = Mock()
    mobile_delete = AsyncMock()
    provider_delete = AsyncMock()
    monkeypatch.setattr(auth_routes, "DeleteAccountUseCase", admin_delete_constructor)
    monkeypatch.setattr(auth_routes, "AdminUserRepository", admin_repo_constructor)
    monkeypatch.setattr(MobileDeleteAccountUseCase, "execute", mobile_delete)
    monkeypatch.setattr(RemnawaveUserGateway, "delete", provider_delete)

    response, current_user = await _delete_request(
        realm_type="customer",
        path=path,
        db=db,
        redis_client=redis_client,
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "CUSTOMER_ACCOUNT_DELETION_REQUIRES_PRIVACY_REQUEST",
            "message": (
                "Customer account deletion must use the privacy request workflow at "
                "POST /api/v1/auth/me/privacy-requests."
            ),
        }
    }
    assert current_user.is_active is True
    assert current_user.deleted_at is None
    admin_repo_constructor.assert_not_called()
    admin_delete_constructor.assert_not_called()
    mobile_delete.assert_not_awaited()
    provider_delete.assert_not_awaited()
    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.delete.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("realm_type", ["admin", "partner"])
async def test_non_customer_web_delete_account_preserves_existing_soft_delete_path(
    realm_type: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    redis_client = AsyncMock()
    user_repo = object()
    admin_repo_constructor = Mock(return_value=user_repo)
    delete_use_case = Mock()
    delete_use_case.execute = AsyncMock()
    admin_delete_constructor = Mock(return_value=delete_use_case)
    monkeypatch.setattr(auth_routes, "AdminUserRepository", admin_repo_constructor)
    monkeypatch.setattr(auth_routes, "DeleteAccountUseCase", admin_delete_constructor)

    response, current_user = await _delete_request(
        realm_type=realm_type,
        path="/api/v1/auth/me",
        db=db,
        redis_client=redis_client,
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Account has been deleted"}
    admin_repo_constructor.assert_called_once_with(db)
    admin_delete_constructor.assert_called_once_with(
        user_repo=user_repo,
        session=db,
        redis_client=redis_client,
    )
    delete_use_case.execute.assert_awaited_once_with(current_user.id)
