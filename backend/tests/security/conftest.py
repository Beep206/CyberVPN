"""Shared subprocess-backed app snapshots for security tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

FRESH_APP_IMPORT_TIMEOUT_SECONDS = 30


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"security-fresh-app-{label}".encode()).hexdigest()[:length]


def _fresh_app_env(repo_root: Path, overrides: dict[str, str]) -> dict[str, str]:
    env = {
        **os.environ,
        "REMNAWAVE_TOKEN": _non_secret_test_value("remnawave"),
        "JWT_SECRET": _non_secret_test_value("jwt"),
        "CRYPTOBOT_TOKEN": _non_secret_test_value("cryptobot"),
        "TOTP_ENCRYPTION_KEY": _non_secret_test_value("totp"),
        "OAUTH_TOKEN_ENCRYPTION_KEY": _non_secret_test_value("oauth"),
        "OAUTH_ENABLED_LOGIN_PROVIDERS": "",
        "PYTHONPATH": str(repo_root / "backend"),
    }
    env.update(overrides)
    return env


def _run_fresh_app_script(marker: str, script: str, env: dict[str, str], repo_root: Path) -> dict[str, Any]:
    completed = subprocess.run(  # noqa: S603 - static interpreter/script used for fresh import proof.
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=FRESH_APP_IMPORT_TIMEOUT_SECONDS,
    )
    result_line = next(line for line in completed.stdout.splitlines() if line.startswith(marker))
    return json.loads(result_line.removeprefix(marker))


@pytest.fixture(scope="session")
def production_app_security_snapshot() -> dict[str, Any]:
    """Import the production app once and collect security-critical surface proofs."""
    repo_root = Path(__file__).resolve().parents[3]
    marker = "S1_PRODUCTION_SECURITY_RESULT="
    script = textwrap.dedent(
        f"""
        import asyncio
        import json

        from fastapi import HTTPException
        from httpx import ASGITransport, AsyncClient

        from src.config.settings import settings
        from src.main import app, swagger_enabled_for_environment
        from src.presentation.dependencies.auth import get_current_active_user

        async def fake_current_active_user():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_active_user] = fake_current_active_user

        async def main():
            paths = sorted({{getattr(route, "path", "") for route in app.routes}})
            middleware_names = [item.cls.__name__ for item in app.user_middleware]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
                wrong_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={{"Host": "cyber-vpn.net"}},
                )
                redirect_only_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={{"Host": "admin.cyber-vpn.org"}},
                )
                allowed_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={{"Host": "admin.cyber-vpn.net"}},
                )
                wrong_preflight = await client.options(
                    "/api/v1/admin/audit-log",
                    headers={{
                        "Host": "cyber-vpn.net",
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    }},
                )
                allowed_preflight = await client.options(
                    "/api/v1/admin/audit-log",
                    headers={{
                        "Host": "admin.cyber-vpn.net",
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    }},
                )
                status = await client.get(
                    "/api/v1/status",
                    headers={{"Host": "cyber-vpn.net"}},
                )
                public_preflight = await client.options(
                    "/api/v1/status",
                    headers={{
                        "Origin": "https://cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    }},
                )
                admin_preflight = await client.options(
                    "/api/v1/status",
                    headers={{
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    }},
                )
                redirect_only_preflight = await client.options(
                    "/api/v1/status",
                    headers={{
                        "Origin": "https://cyber-vpn.org",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    }},
                )
                client.cookies.set("access_token", "token")
                missing_origin = await client.post("/api/v1/status")
                approved_origin = await client.post(
                    "/api/v1/status",
                    headers={{"Origin": "https://cyber-vpn.net"}},
                )
                bearer = await client.post(
                    "/api/v1/status",
                    headers={{"Authorization": "Bearer local-token"}},
                )

            result = {{
                "admin_host": {{
                    "wrong_host": {{
                        "status": wrong_host.status_code,
                        "body": wrong_host.json(),
                    }},
                    "redirect_only_host": {{
                        "status": redirect_only_host.status_code,
                        "body": redirect_only_host.json(),
                    }},
                    "allowed_host": {{
                        "status": allowed_host.status_code,
                        "body": allowed_host.json(),
                    }},
                    "wrong_preflight": {{
                        "status": wrong_preflight.status_code,
                        "allow_origin": wrong_preflight.headers.get("access-control-allow-origin"),
                    }},
                    "allowed_preflight": {{
                        "status": allowed_preflight.status_code,
                        "allow_origin": allowed_preflight.headers.get("access-control-allow-origin"),
                    }},
                    "status": {{
                        "status": status.status_code,
                    }},
                }},
                "cors_cookie": {{
                    "cors_origins": settings.cors_origins,
                    "cookie_domain": settings.cookie_domain,
                    "cookie_secure": settings.cookie_secure,
                    "public_preflight": {{
                        "status": public_preflight.status_code,
                        "allow_origin": public_preflight.headers.get("access-control-allow-origin"),
                        "allow_credentials": public_preflight.headers.get("access-control-allow-credentials"),
                    }},
                    "admin_preflight": {{
                        "status": admin_preflight.status_code,
                        "allow_origin": admin_preflight.headers.get("access-control-allow-origin"),
                        "allow_credentials": admin_preflight.headers.get("access-control-allow-credentials"),
                    }},
                    "redirect_only_preflight": {{
                        "status": redirect_only_preflight.status_code,
                        "allow_origin": redirect_only_preflight.headers.get("access-control-allow-origin"),
                    }},
                }},
                "csrf": {{
                    "csrf_middleware_installed": "CSRFMiddleware" in middleware_names,
                    "missing_origin_status": missing_origin.status_code,
                    "approved_origin_status": approved_origin.status_code,
                    "bearer_status": bearer.status_code,
                }},
                "swagger": {{
                    "swagger_enabled_for_environment": swagger_enabled_for_environment,
                    "public_doc_paths_present": [
                        path for path in ["/docs", "/openapi.json", "/redoc"] if path in paths
                    ],
                    "openapi_url": app.openapi_url,
                    "docs_url": app.docs_url,
                    "redoc_url": app.redoc_url,
                }},
            }}
            print({marker!r} + json.dumps(result, sort_keys=True))

        asyncio.run(main())
        """
    )
    env = _fresh_app_env(
        repo_root,
        {
            "ENVIRONMENT": "production",
            "SWAGGER_ENABLED": "true",
            "CORS_ORIGINS": "https://cyber-vpn.net,https://admin.cyber-vpn.net",
            "COOKIE_DOMAIN": "cyber-vpn.net",
            "COOKIE_SECURE": "true",
            "ADMIN_HOST_PROTECTION_ENABLED": "true",
            "ADMIN_ALLOWED_HOSTS": "admin.cyber-vpn.net",
            "ADMIN_2FA_REQUIRED": "true",
            "RATE_LIMIT_ENABLED": "false",
            "OTEL_ENABLED": "false",
            "ENABLE_METRICS": "false",
            "CSRF_PROTECTION_ENABLED": "true",
        },
    )
    return _run_fresh_app_script(marker, script, env, repo_root)


@pytest.fixture(scope="session")
def local_stage_app_security_snapshot() -> dict[str, Any]:
    """Import the local-stage app once and collect loopback security proofs."""
    repo_root = Path(__file__).resolve().parents[3]
    marker = "S1_LOCAL_STAGE_SECURITY_RESULT="
    script = textwrap.dedent(
        f"""
        import asyncio
        import json

        from httpx import ASGITransport, AsyncClient

        from src.main import app

        async def main():
            middleware_names = [item.cls.__name__ for item in app.user_middleware]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:18080") as client:
                client.cookies.set("access_token", "token")
                approved_origin = await client.post(
                    "/api/v1/status",
                    headers={{"Origin": "http://127.0.0.1:13001"}},
                )
                unapproved_origin = await client.post(
                    "/api/v1/status",
                    headers={{"Origin": "http://127.0.0.1:13002"}},
                )
            result = {{
                "csrf_middleware_installed": "CSRFMiddleware" in middleware_names,
                "approved_origin_status": approved_origin.status_code,
                "unapproved_origin_status": unapproved_origin.status_code,
            }}
            print({marker!r} + json.dumps(result, sort_keys=True))

        asyncio.run(main())
        """
    )
    env = _fresh_app_env(
        repo_root,
        {
            "ENVIRONMENT": "local-stage",
            "RATE_LIMIT_ENABLED": "false",
            "CORS_ORIGINS": (
                "http://localhost:13000,http://localhost:13001,"
                "http://127.0.0.1:13000,http://127.0.0.1:13001"
            ),
            "PASSKEY_ENABLED": "true",
            "PASSKEY_RP_ID": "localhost",
            "PASSKEY_ALLOWED_ORIGINS": (
                "http://localhost:13000,http://localhost:13001,"
                "http://127.0.0.1:13000,http://127.0.0.1:13001"
            ),
            "COOKIE_DOMAIN": "",
            "COOKIE_SECURE": "false",
            "CSRF_PROTECTION_ENABLED": "true",
        },
    )
    return _run_fresh_app_script(marker, script, env, repo_root)
