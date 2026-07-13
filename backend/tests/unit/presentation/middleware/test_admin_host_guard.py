from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.middleware.admin_host_guard import (
    TASK2_ROUTE_EVIDENCE_EXEMPT_PATH,
    TASK2_ROUTE_EVIDENCE_HOST,
    AdminHostGuardMiddleware,
)


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

    @app.post(TASK2_ROUTE_EVIDENCE_EXEMPT_PATH)
    async def task2_route_evidence() -> dict[str, str]:
        return {"status": "task2-evidence-open"}

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


async def test_admin_host_guard_allows_only_exact_task2_collector_on_dedicated_host() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), client=("203.0.113.10", 52344)),
        base_url=f"https://{TASK2_ROUTE_EVIDENCE_HOST}",
    ) as client:
        collector = await client.post(TASK2_ROUTE_EVIDENCE_EXEMPT_PATH)
        other_admin = await client.get("/api/v1/admin/ping")

    assert collector.status_code == 200
    assert collector.json() == {"status": "task2-evidence-open"}
    assert other_admin.status_code == 404


async def test_admin_host_guard_rejects_task2_collector_on_other_host() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), client=("203.0.113.10", 52344)),
        base_url="https://api.cyber-vpn.net",
    ) as client:
        response = await client.post(TASK2_ROUTE_EVIDENCE_EXEMPT_PATH)

    assert response.status_code == 404
