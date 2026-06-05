"""S1-BE-006 CSRF protection checks for cookie-auth browser flows."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.middleware.csrf import CSRFMiddleware, normalize_origin, request_has_auth_cookie


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://cyber-vpn.net", "https://cyber-vpn.net"),
        ("https://cyber-vpn.net/dashboard", "https://cyber-vpn.net"),
        ("https://admin.cyber-vpn.net/path?q=1", "https://admin.cyber-vpn.net"),
        ("null", None),
        ("", None),
        ("not-a-url", None),
    ],
)
def test_stage1_csrf_origin_normalization(value: str, expected: str | None) -> None:
    assert normalize_origin(value) == expected


def test_stage1_csrf_auth_cookie_detection() -> None:
    assert request_has_auth_cookie({"access_token": "token"})
    assert request_has_auth_cookie({"customer_access_token": "token"})
    assert request_has_auth_cookie({"customer_refresh_token": "token"})
    assert not request_has_auth_cookie({"analytics_id": "value"})


def _build_test_app(allowed_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CSRFMiddleware,
        allowed_origins=allowed_origins or ["https://cyber-vpn.net", "https://admin.cyber-vpn.net"],
    )

    @app.post("/api/v1/profile")
    async def profile_update():
        return {"status": "ok"}

    @app.get("/api/v1/profile")
    async def profile_read():
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
async def test_stage1_csrf_blocks_cookie_auth_unsafe_request_without_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("access_token", "token")
        response = await client.post("/api/v1/profile")

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF origin validation failed"}


@pytest.mark.asyncio
async def test_stage1_csrf_allows_cookie_auth_unsafe_request_from_approved_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("customer_access_token", "token")
        response = await client.post(
            "/api/v1/profile",
            headers={"Origin": "https://cyber-vpn.net"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stage1_csrf_allows_cookie_auth_unsafe_request_from_approved_referer() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("customer_access_token", "token")
        response = await client.post(
            "/api/v1/profile",
            headers={"Referer": "https://cyber-vpn.net/account"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stage1_csrf_blocks_cookie_auth_unsafe_request_from_redirect_only_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("access_token", "token")
        response = await client.post(
            "/api/v1/profile",
            headers={"Origin": "https://cyber-vpn.org"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_stage1_csrf_allows_cookie_auth_unsafe_request_from_approved_local_stage_origin() -> None:
    allowed_origins = [
        "http://127.0.0.1:13000",
        "http://127.0.0.1:13001",
    ]
    async with AsyncClient(
        transport=ASGITransport(app=_build_test_app(allowed_origins)),
        base_url="http://127.0.0.1:18080",
    ) as client:
        client.cookies.set("access_token", "token")
        response = await client.post(
            "/api/v1/profile",
            headers={"Origin": "http://127.0.0.1:13001"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stage1_csrf_blocks_cookie_auth_unsafe_request_from_unapproved_local_origin() -> None:
    allowed_origins = [
        "http://127.0.0.1:13000",
        "http://127.0.0.1:13001",
    ]
    async with AsyncClient(
        transport=ASGITransport(app=_build_test_app(allowed_origins)),
        base_url="http://127.0.0.1:18080",
    ) as client:
        client.cookies.set("access_token", "token")
        response = await client.post(
            "/api/v1/profile",
            headers={"Origin": "http://127.0.0.1:13002"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_stage1_csrf_allows_bearer_token_and_non_cookie_requests_without_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("access_token", "token")
        bearer_response = await client.post(
            "/api/v1/profile",
            headers={"Authorization": "Bearer local-test-token"},
        )
        client.cookies.clear()
        no_cookie_response = await client.post("/api/v1/profile")

    assert bearer_response.status_code == 200
    assert no_cookie_response.status_code == 200


@pytest.mark.asyncio
async def test_stage1_csrf_allows_safe_methods_without_origin() -> None:
    async with AsyncClient(transport=ASGITransport(app=_build_test_app()), base_url="https://backend") as client:
        client.cookies.set("access_token", "token")
        response = await client.get("/api/v1/profile")

    assert response.status_code == 200


def test_stage1_production_app_enforces_csrf_for_cookie_auth_unsafe_requests(
    production_app_security_snapshot: dict,
) -> None:
    assert production_app_security_snapshot["csrf"] == {
        "approved_origin_status": 405,
        "bearer_status": 405,
        "csrf_middleware_installed": True,
        "missing_origin_status": 403,
    }


def test_stage1_local_stage_app_enforces_csrf_with_approved_loopback_origins(
    local_stage_app_security_snapshot: dict,
) -> None:
    assert local_stage_app_security_snapshot == {
        "approved_origin_status": 405,
        "csrf_middleware_installed": True,
        "unapproved_origin_status": 403,
    }
