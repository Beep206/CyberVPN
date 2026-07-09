from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.middleware.admin_host_guard import AdminHostGuardMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        AdminHostGuardMiddleware,
        allowed_hosts=["admin.cyber-vpn.net"],
        environment="production",
        trust_proxy_headers=True,
        trusted_proxy_ips=["10.0.0.0/8"],
    )

    @app.get("/api/v1/admin/ping")
    async def admin_ping() -> dict[str, str]:
        return {"status": "admin-open"}

    @app.get("/api/v1/status")
    async def public_status() -> dict[str, str]:
        return {"status": "public-open"}

    return app


async def test_admin_host_guard_ignores_forwarded_host_from_untrusted_peer() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), client=("203.0.113.10", 52344)),
        base_url="https://backend.internal",
    ) as client:
        response = await client.get(
            "/api/v1/admin/ping",
            headers={"x-forwarded-host": "admin.cyber-vpn.net"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


async def test_admin_host_guard_accepts_forwarded_host_from_trusted_proxy() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), client=("10.0.0.25", 52344)),
        base_url="https://backend.internal",
    ) as client:
        response = await client.get(
            "/api/v1/admin/ping",
            headers={"x-forwarded-host": "admin.cyber-vpn.net"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "admin-open"}


async def test_admin_host_guard_keeps_public_routes_outside_admin_boundary() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), client=("203.0.113.10", 52344)),
        base_url="https://backend.internal",
    ) as client:
        response = await client.get(
            "/api/v1/status",
            headers={"x-forwarded-host": "evil.example"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "public-open"}
