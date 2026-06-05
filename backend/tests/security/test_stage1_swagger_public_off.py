"""S1-BE-004 public Swagger/OpenAPI exposure checks."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import _swagger_enabled_for_environment, app, metrics_app, settings

PUBLIC_DOC_PATHS = ("/docs", "/docs/", "/openapi.json", "/redoc", "/redoc/")


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


def test_stage1_production_import_does_not_mount_docs_when_env_enables_swagger(
    production_app_security_snapshot: dict,
) -> None:
    assert production_app_security_snapshot["swagger"] == {
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
