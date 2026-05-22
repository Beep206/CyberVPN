"""S1-BE-005 CORS and cookie-domain production safety checks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"s1-be-005-{label}".encode()).hexdigest()[:length]


def test_stage1_production_app_cors_allows_only_primary_net_origins() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        import asyncio
        import json

        from httpx import ASGITransport, AsyncClient

        from src.config.settings import settings
        from src.main import app

        async def main():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
                public_preflight = await client.options(
                    "/api/v1/status",
                    headers={
                        "Origin": "https://cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                admin_preflight = await client.options(
                    "/api/v1/status",
                    headers={
                        "Origin": "https://admin.cyber-vpn.net",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                redirect_only_preflight = await client.options(
                    "/api/v1/status",
                    headers={
                        "Origin": "https://cyber-vpn.org",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                result = {
                    "cors_origins": settings.cors_origins,
                    "cookie_domain": settings.cookie_domain,
                    "cookie_secure": settings.cookie_secure,
                    "public_preflight": {
                        "status": public_preflight.status_code,
                        "allow_origin": public_preflight.headers.get("access-control-allow-origin"),
                        "allow_credentials": public_preflight.headers.get("access-control-allow-credentials"),
                    },
                    "admin_preflight": {
                        "status": admin_preflight.status_code,
                        "allow_origin": admin_preflight.headers.get("access-control-allow-origin"),
                        "allow_credentials": admin_preflight.headers.get("access-control-allow-credentials"),
                    },
                    "redirect_only_preflight": {
                        "status": redirect_only_preflight.status_code,
                        "allow_origin": redirect_only_preflight.headers.get("access-control-allow-origin"),
                    },
                }
                print("S1_BE_005_RESULT=" + json.dumps(result, sort_keys=True))

        asyncio.run(main())
        """
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "CORS_ORIGINS": "https://cyber-vpn.net,https://admin.cyber-vpn.net",
        "COOKIE_DOMAIN": "cyber-vpn.net",
        "COOKIE_SECURE": "true",
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
    result_line = next(line for line in completed.stdout.splitlines() if line.startswith("S1_BE_005_RESULT="))
    result = json.loads(result_line.removeprefix("S1_BE_005_RESULT="))

    assert result == {
        "admin_preflight": {
            "allow_credentials": "true",
            "allow_origin": "https://admin.cyber-vpn.net",
            "status": 200,
        },
        "cookie_domain": "cyber-vpn.net",
        "cookie_secure": True,
        "cors_origins": [
            "https://cyber-vpn.net",
            "https://admin.cyber-vpn.net",
        ],
        "public_preflight": {
            "allow_credentials": "true",
            "allow_origin": "https://cyber-vpn.net",
            "status": 200,
        },
        "redirect_only_preflight": {
            "allow_origin": None,
            "status": 400,
        },
    }
