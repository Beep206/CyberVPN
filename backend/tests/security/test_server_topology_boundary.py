"""Global server topology is available only in the authorized admin realm."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.auth_realms import RealmResolution
from src.application.use_cases.servers.manage_servers import ManageServersUseCase
from src.application.use_cases.servers.server_stats import ServerStatsUseCase
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.presentation.api.v1.servers import routes as server_routes
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client


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


def _admin_user(role: AdminRole) -> AdminUserModel:
    return AdminUserModel(
        login=f"server-topology-{role.value}",
        email=f"server-topology-{role.value}@example.test",
        role=role.value,
        is_active=True,
        totp_enabled=True,
    )


async def _request(
    *,
    realm_type: str,
    role: AdminRole,
    path: str,
) -> object:
    app = FastAPI()
    app.include_router(server_routes.router, prefix="/api/v1")

    async def fake_db() -> object:
        return object()

    async def fake_client() -> object:
        return object()

    async def fake_user() -> AdminUserModel:
        return _admin_user(role)

    async def fake_realm() -> RealmResolution:
        return _realm(realm_type)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_remnawave_client] = fake_client
    app.dependency_overrides[get_current_active_user] = fake_user
    app.dependency_overrides[get_request_admin_realm] = fake_realm

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://admin.cyber-vpn.net",
    ) as client:
        return await client.get(path)


@pytest.fixture
def provider_reads(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    list_servers = AsyncMock(return_value=[])
    server_stats = AsyncMock(
        return_value={
            "online": 0,
            "offline": 0,
            "warning": 0,
            "maintenance": 0,
            "total": 0,
        }
    )
    get_server = AsyncMock(return_value=None)
    monkeypatch.setattr(ManageServersUseCase, "get_all", list_servers)
    monkeypatch.setattr(ServerStatsUseCase, "execute", server_stats)
    monkeypatch.setattr(ManageServersUseCase, "get_by_uuid", get_server)

    async def bypass_cache(
        _key: str,
        _ttl: int,
        fetch: Callable[[], Awaitable[object]],
    ) -> object:
        return await fetch()

    monkeypatch.setattr(server_routes.response_cache, "get_or_fetch", bypass_cache)
    return list_servers, server_stats, get_server


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("realm_type", ["customer", "partner"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/servers",
        "/api/v1/servers/stats",
        f"/api/v1/servers/{uuid4()}",
    ],
)
async def test_global_server_topology_rejects_non_admin_realms_before_provider_read(
    realm_type: str,
    path: str,
    provider_reads: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    response = await _request(
        realm_type=realm_type,
        role=AdminRole.SUPER_ADMIN,
        path=path,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin realm required"
    for provider_read in provider_reads:
        provider_read.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/servers", "/api/v1/servers/stats"])
async def test_global_server_topology_requires_server_read_permission_before_provider_read(
    path: str,
    provider_reads: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    response = await _request(
        realm_type="admin",
        role=AdminRole.FINANCE,
        path=path,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing permission: server_read"
    for provider_read in provider_reads:
        provider_read.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "provider_index"),
    [
        ("/api/v1/servers", 0),
        ("/api/v1/servers/stats", 1),
    ],
)
async def test_global_server_topology_allows_admin_with_server_read(
    path: str,
    provider_index: int,
    provider_reads: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    response = await _request(
        realm_type="admin",
        role=AdminRole.VIEWER,
        path=path,
    )

    assert response.status_code == 200
    provider_reads[provider_index].assert_awaited_once()
