"""S1-BE-006 CSRF protection checks for cookie-auth browser flows."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.middleware.csrf import CSRFMiddleware, normalize_origin, request_has_auth_cookie


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"s1-be-006-{label}".encode()).hexdigest()[:length]


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


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CSRFMiddleware,
        allowed_origins=["https://cyber-vpn.net", "https://admin.cyber-vpn.net"],
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


def test_stage1_production_app_enforces_csrf_for_cookie_auth_unsafe_requests() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        import asyncio
        import json

        from httpx import ASGITransport, AsyncClient

        from src.main import app
        from src.presentation.middleware.csrf import CSRFMiddleware

        async def main():
            middleware_names = [item.cls.__name__ for item in app.user_middleware]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
                client.cookies.set("access_token", "token")
                missing_origin = await client.post("/api/v1/status")
                approved_origin = await client.post(
                    "/api/v1/status",
                    headers={"Origin": "https://cyber-vpn.net"},
                )
                bearer = await client.post(
                    "/api/v1/status",
                    headers={"Authorization": "Bearer local-token"},
                )
            result = {
                "csrf_middleware_installed": "CSRFMiddleware" in middleware_names,
                "missing_origin_status": missing_origin.status_code,
                "approved_origin_status": approved_origin.status_code,
                "bearer_status": bearer.status_code,
            }
            print("S1_BE_006_RESULT=" + json.dumps(result, sort_keys=True))

        assert CSRFMiddleware.__name__ == "CSRFMiddleware"
        asyncio.run(main())
        """
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "RATE_LIMIT_ENABLED": "false",
        "CORS_ORIGINS": "https://cyber-vpn.net,https://admin.cyber-vpn.net",
        "COOKIE_DOMAIN": "",
        "COOKIE_SECURE": "true",
        "CSRF_PROTECTION_ENABLED": "true",
        "ADMIN_2FA_REQUIRED": "true",
        "REMNAWAVE_TOKEN": _non_secret_test_value("remnawave"),
        "JWT_SECRET": _non_secret_test_value("jwt"),
        "CRYPTOBOT_TOKEN": _non_secret_test_value("cryptobot"),
        "TOTP_ENCRYPTION_KEY": _non_secret_test_value("totp"),
        "OAUTH_TOKEN_ENCRYPTION_KEY": _non_secret_test_value("oauth"),
        "OAUTH_ENABLED_LOGIN_PROVIDERS": "",
        "PYTHONPATH": str(repo_root / "backend"),
    }

    completed = subprocess.run(  # noqa: S603 - static interpreter/script used for fresh import proof.
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result_line = next(line for line in completed.stdout.splitlines() if line.startswith("S1_BE_006_RESULT="))
    result = json.loads(result_line.removeprefix("S1_BE_006_RESULT="))

    assert result == {
        "approved_origin_status": 405,
        "bearer_status": 405,
        "csrf_middleware_installed": True,
        "missing_origin_status": 403,
    }
