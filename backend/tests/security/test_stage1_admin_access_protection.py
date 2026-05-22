"""S1-ADM-001 admin host/access protection checks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from src.presentation.middleware.admin_host_guard import is_admin_host_protected_path, normalize_host


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"s1-adm-001-{label}".encode()).hexdigest()[:length]


def test_stage1_admin_host_guard_normalizes_hosts() -> None:
    assert normalize_host("ADMIN.CYBER-VPN.NET:443") == "admin.cyber-vpn.net"
    assert normalize_host("https://admin.cyber-vpn.net") == "admin.cyber-vpn.net"
    assert normalize_host("[::1]:8000") == "::1"
    assert normalize_host("admin.cyber-vpn.net, evil.example") == "admin.cyber-vpn.net"


def test_stage1_admin_host_guard_path_scope() -> None:
    assert is_admin_host_protected_path("/api/v1/admin")
    assert is_admin_host_protected_path("/api/v1/admin/audit-log")
    assert not is_admin_host_protected_path("/api/v1/adminish")
    assert not is_admin_host_protected_path("/api/v1/admin/growth-reporting/internal/refresh")
    assert not is_admin_host_protected_path("/api/v1/status")


def test_stage1_production_admin_api_requires_admin_host() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        import asyncio
        import json

        from fastapi import HTTPException
        from httpx import ASGITransport, AsyncClient

        from src.main import app
        from src.presentation.dependencies.auth import get_current_active_user

        async def fake_current_active_user():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_active_user] = fake_current_active_user

        async def main():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
                wrong_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={"Host": "cyber-vpn.net"},
                )
                redirect_only_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={"Host": "admin.cyber-vpn.org"},
                )
                allowed_host = await client.get(
                    "/api/v1/admin/audit-log",
                    headers={"Host": "admin.cyber-vpn.net"},
                )
                wrong_preflight = await client.options(
                    "/api/v1/admin/audit-log",
                    headers={
                        "Host": "cyber-vpn.net",
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                allowed_preflight = await client.options(
                    "/api/v1/admin/audit-log",
                    headers={
                        "Host": "admin.cyber-vpn.net",
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                status = await client.get(
                    "/api/v1/status",
                    headers={"Host": "cyber-vpn.net"},
                )

                print(
                    "S1_ADM_001_RESULT="
                    + json.dumps(
                        {
                            "wrong_host": {
                                "status": wrong_host.status_code,
                                "body": wrong_host.json(),
                            },
                            "redirect_only_host": {
                                "status": redirect_only_host.status_code,
                                "body": redirect_only_host.json(),
                            },
                            "allowed_host": {
                                "status": allowed_host.status_code,
                                "body": allowed_host.json(),
                            },
                            "wrong_preflight": {
                                "status": wrong_preflight.status_code,
                                "allow_origin": wrong_preflight.headers.get("access-control-allow-origin"),
                            },
                            "allowed_preflight": {
                                "status": allowed_preflight.status_code,
                                "allow_origin": allowed_preflight.headers.get("access-control-allow-origin"),
                            },
                            "status": {
                                "status": status.status_code,
                            },
                        },
                        sort_keys=True,
                    )
                )

        asyncio.run(main())
        """
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "CORS_ORIGINS": "https://cyber-vpn.net,https://admin.cyber-vpn.net",
        "COOKIE_DOMAIN": "cyber-vpn.net",
        "COOKIE_SECURE": "true",
        "ADMIN_HOST_PROTECTION_ENABLED": "true",
        "ADMIN_ALLOWED_HOSTS": "admin.cyber-vpn.net",
        "ADMIN_2FA_REQUIRED": "true",
        "RATE_LIMIT_ENABLED": "false",
        "OTEL_ENABLED": "false",
        "ENABLE_METRICS": "false",
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
    result_line = next(line for line in completed.stdout.splitlines() if line.startswith("S1_ADM_001_RESULT="))
    result = json.loads(result_line.removeprefix("S1_ADM_001_RESULT="))

    assert result == {
        "allowed_host": {
            "body": {"detail": "Not authenticated"},
            "status": 401,
        },
        "allowed_preflight": {
            "allow_origin": "https://admin.cyber-vpn.net",
            "status": 200,
        },
        "redirect_only_host": {
            "body": {"detail": "Not found"},
            "status": 404,
        },
        "status": {
            "status": 200,
        },
        "wrong_host": {
            "body": {"detail": "Not found"},
            "status": 404,
        },
        "wrong_preflight": {
            "allow_origin": None,
            "status": 404,
        },
    }
