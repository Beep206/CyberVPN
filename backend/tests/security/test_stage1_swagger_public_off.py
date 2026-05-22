"""S1-BE-004 public Swagger/OpenAPI exposure checks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import _swagger_enabled_for_environment, app, metrics_app, settings

PUBLIC_DOC_PATHS = ("/docs", "/docs/", "/openapi.json", "/redoc", "/redoc/")


def _non_secret_test_value(label: str, length: int = 64) -> str:
    return hashlib.sha512(f"s1-be-004-{label}".encode()).hexdigest()[:length]


@pytest.mark.parametrize(
    ("environment", "configured_enabled", "expected_enabled"),
    [
        ("development", True, True),
        ("staging", True, True),
        ("test", False, False),
        ("production", False, False),
        ("production", True, False),
        ("Production", True, False),
    ],
)
def test_stage1_swagger_gate_forces_public_docs_off_in_production(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    configured_enabled: bool,
    expected_enabled: bool,
) -> None:
    monkeypatch.setattr(settings, "environment", environment)
    monkeypatch.setattr(settings, "swagger_enabled", configured_enabled)

    assert _swagger_enabled_for_environment() is expected_enabled


@pytest.mark.asyncio
async def test_stage1_current_app_returns_404_for_public_docs_routes() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        statuses = {path: (await client.get(path)).status_code for path in PUBLIC_DOC_PATHS}
        health_status = (await client.get("/health")).status_code

    assert statuses == {path: 404 for path in PUBLIC_DOC_PATHS}
    assert health_status == 200


def test_stage1_production_import_does_not_mount_docs_when_env_enables_swagger() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = textwrap.dedent(
        """
        import json
        from src.main import app, swagger_enabled_for_environment

        paths = sorted({getattr(route, "path", "") for route in app.routes})
        result = {
            "swagger_enabled_for_environment": swagger_enabled_for_environment,
            "public_doc_paths_present": [
                path for path in ["/docs", "/openapi.json", "/redoc"] if path in paths
            ],
            "openapi_url": app.openapi_url,
            "docs_url": app.docs_url,
            "redoc_url": app.redoc_url,
        }
        print("S1_BE_004_RESULT=" + json.dumps(result, sort_keys=True))
        """
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "SWAGGER_ENABLED": "true",
        "CORS_ORIGINS": "https://cyber-vpn.net,https://admin.cyber-vpn.net",
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
    result_line = next(line for line in completed.stdout.splitlines() if line.startswith("S1_BE_004_RESULT="))
    result = json.loads(result_line.removeprefix("S1_BE_004_RESULT="))

    assert result == {
        "docs_url": None,
        "openapi_url": None,
        "public_doc_paths_present": [],
        "redoc_url": None,
        "swagger_enabled_for_environment": False,
    }


def test_stage1_metrics_app_never_mounts_public_docs_routes() -> None:
    paths = {getattr(route, "path", "") for route in metrics_app.routes}

    assert metrics_app.openapi_url is None
    assert metrics_app.docs_url is None
    assert metrics_app.redoc_url is None
    assert not ({"/docs", "/openapi.json", "/redoc"} & paths)
