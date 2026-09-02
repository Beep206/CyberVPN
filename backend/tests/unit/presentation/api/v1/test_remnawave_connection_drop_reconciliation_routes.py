from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute

from src.application.use_cases.auth_realms.resolve_realm import RealmResolution
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.presentation.api.v1.remnawave_connections import routes
from src.presentation.api.v1.remnawave_connections.drop_receipts import (
    RemnawaveConnectionDropReceiptRecord,
    RemnawaveConnectionDropState,
)
from src.presentation.api.v1.remnawave_connections.job_registry import RemnawaveConnectionJobAudience
from src.presentation.api.v1.remnawave_connections.reconciliation import (
    RemnawaveConnectionDropReconciliationConflictError,
    RemnawaveConnectionDropReconciliationNotFoundError,
    RemnawaveConnectionDropReconciliationReason,
)
from src.presentation.middleware.csrf import CSRFMiddleware

_RECEIPT_ID = "r" * 43
_PATH = f"/api/v1/admin/remnawave/connections/drop-receipts/{_RECEIPT_ID}/reconcile"


def _admin(role: AdminRole = AdminRole.ADMIN) -> AdminUserModel:
    return AdminUserModel(
        id=uuid4(),
        login=f"reconciliation-{uuid4()}",
        role=role.value,
        is_active=True,
        totp_enabled=True,
    )


def _realm(realm_type: str) -> RealmResolution:
    return RealmResolution(
        auth_realm=AuthRealmModel(
            id=uuid4(),
            realm_key=f"{realm_type}-{uuid4()}",
            realm_type=realm_type,
            display_name=realm_type,
            audience=f"cybervpn-{realm_type}-{uuid4()}",
            cookie_namespace=realm_type,
            status="active",
            is_default=False,
        ),
        source="test",
    )


def _record() -> RemnawaveConnectionDropReceiptRecord:
    now = datetime.now(UTC)
    return RemnawaveConnectionDropReceiptRecord(
        database_id=uuid4(),
        receipt_id=_RECEIPT_ID,
        hmac_key_id="a" * 64,
        audience=RemnawaveConnectionJobAudience.ADMIN,
        actor_id=uuid4(),
        scope_hmac="b" * 64,
        payload_hmac="c" * 64,
        state=RemnawaveConnectionDropState.ACCEPTED,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(days=1),
        reconciled_at=now,
        reconciled_by_admin_id=uuid4(),
        reconciliation_reason=RemnawaveConnectionDropReconciliationReason.PROVIDER_CONFIRMED_APPLIED.value,
        reconciliation_reference="CASE-ABC123",
    )


def _route() -> APIRoute:
    return next(
        route
        for route in routes.router.routes
        if isinstance(route, APIRoute) and route.path.endswith("/{receipt_id}/reconcile")
    )


def _role_dependency():
    return next(
        dependency.call for dependency in _route().dependant.dependencies if dependency.call.__name__ == "role_checker"
    )


def _app(service: AsyncMock, *, authorization_dependency=None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CSRFMiddleware, allowed_origins=["https://admin.cyber-vpn.net"])
    app.include_router(routes.router, prefix="/api/v1")

    async def allow_admin() -> AdminUserModel:
        return _admin()

    app.dependency_overrides[_role_dependency()] = authorization_dependency or allow_admin
    app.dependency_overrides[routes.get_remnawave_connection_drop_reconciliation_service] = lambda: service
    return app


@pytest.mark.unit
def test_reconciliation_service_dependency_does_not_read_current_hmac_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()

    def unavailable_secret() -> bytes:
        raise RuntimeError("rotating secret unavailable")

    monkeypatch.setattr(
        routes,
        "configured_connection_drop_hmac_secret",
        unavailable_secret,
    )

    service = routes.get_remnawave_connection_drop_reconciliation_service(db)

    assert service._db is db  # noqa: SLF001 - exact dependency boundary


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "realm_type", "expected_status"),
    [
        (AdminRole.ADMIN, "admin", 200),
        (AdminRole.SUPER_ADMIN, "admin", 200),
        (AdminRole.OWNER_SUPER_ADMIN, "admin", 200),
        (AdminRole.OPERATOR, "admin", 403),
        (AdminRole.ADMIN, "partner", 403),
        (AdminRole.ADMIN, "customer", 403),
    ],
)
async def test_reconciliation_role_boundary_is_global_admin_only(
    role: AdminRole,
    realm_type: str,
    expected_status: int,
) -> None:
    checker = _role_dependency()
    if expected_status == 200:
        assert await checker(user=_admin(role), current_realm=_realm(realm_type))
    else:
        with pytest.raises(HTTPException) as denied:
            await checker(user=_admin(role), current_realm=_realm(realm_type))
        assert denied.value.status_code == expected_status


@pytest.mark.unit
async def test_anonymous_direct_reconciliation_url_is_denied_before_service() -> None:
    service = AsyncMock()

    async def deny_anonymous() -> None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(service, authorization_dependency=deny_anonymous)),
        base_url="https://backend",
    ) as client:
        response = await client.post(
            _PATH,
            json={
                "outcome": "accepted",
                "reason": "provider_confirmed_applied",
                "reference": "CASE-ABC123",
            },
        )

    assert response.status_code == 401
    service.reconcile.assert_not_awaited()


@pytest.mark.unit
async def test_cookie_reconciliation_requires_approved_origin_but_server_bearer_does_not() -> None:
    service = AsyncMock()
    service.reconcile.return_value = _record()
    app = _app(service)
    body = {
        "outcome": "accepted",
        "reason": "provider_confirmed_applied",
        "reference": "CASE-ABC123",
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://backend") as client:
        client.cookies.set("access_token", "cookie-session")
        missing_origin = await client.post(_PATH, json=body)
        approved_origin = await client.post(
            _PATH,
            json=body,
            headers={"Origin": "https://admin.cyber-vpn.net"},
        )
        bearer = await client.post(
            _PATH,
            json=body,
            headers={"Authorization": "Bearer server-authorized-token"},
        )

    assert missing_origin.status_code == 403
    assert approved_origin.status_code == 200
    assert bearer.status_code == 200
    assert service.reconcile.await_count == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "body",
    [
        {
            "outcome": "accepted",
            "reason": "provider_confirmed_not_applied",
            "reference": "CASE-ABC123",
        },
        {
            "outcome": "accepted",
            "reason": "provider_confirmed_applied",
            "reference": "provider said yes in raw payload",
        },
        {
            "outcome": "accepted",
            "reason": "provider_confirmed_applied",
            "reference": "CASE-ABC123",
            "expiresInSeconds": 999999,
            "hmac": "secret",
            "scope": "admin:global",
        },
    ],
)
async def test_reconciliation_request_rejects_mismatched_or_sensitive_client_fields(body: dict[str, object]) -> None:
    service = AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(service)),
        base_url="https://backend",
    ) as client:
        response = await client.post(_PATH, json=body)

    assert response.status_code == 422
    service.reconcile.assert_not_awaited()


@pytest.mark.unit
async def test_strict_receipt_id_and_unknown_or_conflicting_receipts_have_safe_statuses() -> None:
    invalid_service = AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(invalid_service)),
        base_url="https://backend",
    ) as client:
        invalid = await client.post(
            "/api/v1/admin/remnawave/connections/drop-receipts/short/reconcile",
            json={
                "outcome": "accepted",
                "reason": "provider_confirmed_applied",
                "reference": "CASE-ABC123",
            },
        )
    assert invalid.status_code == 422
    invalid_service.reconcile.assert_not_awaited()

    not_found_service = AsyncMock()
    not_found_service.reconcile.side_effect = RemnawaveConnectionDropReconciliationNotFoundError()
    conflict_service = AsyncMock()
    conflict_service.reconcile.side_effect = RemnawaveConnectionDropReconciliationConflictError()
    body = {
        "outcome": "accepted",
        "reason": "provider_confirmed_applied",
        "reference": "CASE-ABC123",
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(not_found_service)),
        base_url="https://backend",
    ) as client:
        not_found = await client.post(_PATH, json=body)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app(conflict_service)),
        base_url="https://backend",
    ) as client:
        conflict = await client.post(_PATH, json=body)

    assert not_found.status_code == 404
    assert conflict.status_code == 409


@pytest.mark.unit
def test_openapi_exposes_reconciliation_only_on_admin_surface_with_bounded_contract() -> None:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    openapi = app.openapi()
    paths = openapi["paths"]
    operation = paths["/api/v1/admin/remnawave/connections/drop-receipts/{receipt_id}/reconcile"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = openapi["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]

    assert request_schema["additionalProperties"] is False
    assert set(request_schema["properties"]) == {"outcome", "reason", "reference"}
    assert set(request_schema["required"]) == {"outcome", "reason", "reference"}
    assert not any("reconcile" in path for path in paths if "/partner" in path or "/customer" in path)
