from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.application.services import remnawave_create_attempt_settlement as settlement_module
from src.application.services.remnawave_create_attempt_settlement import (
    RemnawaveCustomerCreateAttemptConflict,
    RemnawaveCustomerCreateAttemptNotFound,
    RemnawaveCustomerCreateAttemptResult,
)
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.entities.user import User
from src.domain.enums import AdminRole, UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel
from src.infrastructure.remnawave.client import RemnawaveClient, RemnawaveProtocolError
from src.presentation.api.v1.admin.remnawave_create_attempts import routes
from src.presentation.api.v1.admin.remnawave_create_attempts.schemas import (
    ReopenCustomerCreateAttemptRequest,
    SettleCustomerCreateAttemptRequest,
)
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client


def _admin(*, role: AdminRole = AdminRole.ADMIN) -> AdminUserModel:
    return AdminUserModel(
        id=uuid4(),
        login=f"settlement-{uuid4()}",
        role=role.value,
        is_active=True,
        deleted_at=None,
        totp_enabled=True,
    )


def _realm(realm_type: str = "admin") -> RealmResolution:
    realm = AuthRealmModel(
        id=uuid4(),
        realm_key=f"{realm_type}-{uuid4()}",
        realm_type=realm_type,
        display_name=realm_type,
        audience=f"cybervpn-{realm_type}-{uuid4()}",
        cookie_namespace=realm_type,
        status="active",
        is_default=False,
    )
    return RealmResolution(auth_realm=realm, source="test")


def _request(path: str = "/api/v1/admin/remnawave/customer-create-attempts/test/settle") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [(b"user-agent", b"settlement-test")],
            "client": ("203.0.113.25", 43110),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


@pytest.mark.unit
@pytest.mark.parametrize("numeric_id", [True, False, 0, -1])
def test_settlement_schema_rejects_boolean_or_nonpositive_numeric_ids(numeric_id: object) -> None:
    with pytest.raises(ValidationError):
        SettleCustomerCreateAttemptRequest(provider_numeric_user_id=numeric_id)


@pytest.mark.unit
@pytest.mark.parametrize("reason_code", ["contains spaces", "../../escape", "secret=raw", "x"])
def test_transition_reason_is_bounded_safe_code(reason_code: str) -> None:
    with pytest.raises(ValidationError):
        ReopenCustomerCreateAttemptRequest(reason_code=reason_code)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_settlement_commits_mapping_completion_and_one_redacted_audit(monkeypatch) -> None:
    attempt_id = uuid4()
    customer_id = uuid4()
    legacy_uuid = uuid4()
    result = RemnawaveCustomerCreateAttemptResult(
        attempt_id=attempt_id,
        customer_account_id=customer_id,
        state="completed",
        changed=True,
        user_ref=RemnawaveUserRef(id=731, legacy_uuid=legacy_uuid),
    )
    service = AsyncMock()
    service.settle.return_value = result
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    audited: list[dict[str, object]] = []

    async def audit(**kwargs: object) -> None:
        audited.append(kwargs)

    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    db = AsyncMock()
    response = await routes.settle_customer_create_attempt(
        attempt_id=attempt_id,
        body=SettleCustomerCreateAttemptRequest(
            provider_numeric_user_id=731,
            provider_legacy_uuid=legacy_uuid,
            reason_code="authoritative_provider_readback",
        ),
        request=_request(),
        current_admin=_admin(),
        db=cast(AsyncSession, db),
        client=cast(RemnawaveClient, object()),
    )

    assert response.changed is True
    assert response.provider_numeric_user_id == 731
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    assert len(audited) == 1
    assert audited[0]["action"] == "remnawave.customer_create_attempt.settled"
    details = cast(dict[str, object], audited[0]["details"])
    assert details == {
        "outcome": "completed",
        "customer_account_id": customer_id,
        "provider_numeric_user_id": 731,
        "provider_legacy_uuid_present": True,
        "reason_code": "authoritative_provider_readback",
    }
    assert not any(
        sensitive in str(details).lower()
        for sensitive in ("email", "username", "password", "config", "credential", "secret", "token")
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotent_completed_replay_does_not_append_duplicate_audit(monkeypatch) -> None:
    attempt_id = uuid4()
    service = AsyncMock()
    service.settle.return_value = RemnawaveCustomerCreateAttemptResult(
        attempt_id=attempt_id,
        customer_account_id=uuid4(),
        state="completed",
        changed=False,
        user_ref=RemnawaveUserRef(id=731),
    )
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    audit = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    db = AsyncMock()

    response = await routes.settle_customer_create_attempt(
        attempt_id=attempt_id,
        body=SettleCustomerCreateAttemptRequest(provider_numeric_user_id=731),
        request=_request(),
        current_admin=_admin(),
        db=cast(AsyncSession, db),
        client=cast(RemnawaveClient, object()),
    )

    assert response.changed is False
    audit.assert_not_awaited()
    db.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_customer_attempt_is_hidden_and_transaction_is_rolled_back(monkeypatch) -> None:
    service = AsyncMock()
    service.settle.side_effect = RemnawaveCustomerCreateAttemptNotFound("hidden")
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    db = AsyncMock()

    with pytest.raises(HTTPException) as hidden:
        await routes.settle_customer_create_attempt(
            attempt_id=uuid4(),
            body=SettleCustomerCreateAttemptRequest(provider_numeric_user_id=731),
            request=_request(),
            current_admin=_admin(),
            db=cast(AsyncSession, db),
            client=cast(RemnawaveClient, object()),
        )

    assert hidden.value.status_code == 404
    assert hidden.value.detail == "Customer create attempt not found"
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (RemnawaveCustomerCreateAttemptConflict("mismatch"), 409),
        (httpx.RequestError("provider unavailable"), 503),
        (RemnawaveProtocolError(), 503),
    ],
)
async def test_settlement_maps_safe_conflict_and_provider_unavailable_errors(
    monkeypatch,
    error: Exception,
    expected_status: int,
) -> None:
    service = AsyncMock()
    service.settle.side_effect = error
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    db = AsyncMock()

    with pytest.raises(HTTPException) as rejected:
        await routes.settle_customer_create_attempt(
            attempt_id=uuid4(),
            body=SettleCustomerCreateAttemptRequest(provider_numeric_user_id=731),
            request=_request(),
            current_admin=_admin(),
            db=cast(AsyncSession, db),
            client=cast(RemnawaveClient, object()),
        )

    assert rejected.value.status_code == expected_status
    assert "mismatch" not in str(rejected.value.detail)
    assert "provider unavailable" not in str(rejected.value.detail)
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reopen_audit_proves_provider_mutation_is_not_rearmed(monkeypatch) -> None:
    attempt_id = uuid4()
    customer_id = uuid4()
    service = AsyncMock()
    service.reopen.return_value = RemnawaveCustomerCreateAttemptResult(
        attempt_id=attempt_id,
        customer_account_id=customer_id,
        state="reconciliation_required",
        changed=True,
    )
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    audited: list[dict[str, object]] = []

    async def audit(**kwargs: object) -> None:
        audited.append(kwargs)

    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    db = AsyncMock()
    response = await routes.reopen_customer_create_attempt(
        attempt_id=attempt_id,
        body=ReopenCustomerCreateAttemptRequest(),
        request=_request(),
        current_admin=_admin(),
        db=cast(AsyncSession, db),
    )

    assert response.state == "reconciliation_required"
    details = cast(dict[str, object], audited[0]["details"])
    assert details["provider_mutation_rearmed"] is False
    db.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reopen_conflict_is_stable_and_rolls_back(monkeypatch) -> None:
    service = AsyncMock()
    service.reopen.side_effect = RemnawaveCustomerCreateAttemptConflict("unsafe state")
    monkeypatch.setattr(routes, "RemnawaveCustomerCreateAttemptSettlementService", lambda *_args: service)
    db = AsyncMock()

    with pytest.raises(HTTPException) as rejected:
        await routes.reopen_customer_create_attempt(
            attempt_id=uuid4(),
            body=ReopenCustomerCreateAttemptRequest(),
            request=_request(),
            current_admin=_admin(),
            db=cast(AsyncSession, db),
        )

    assert rejected.value.status_code == 409
    assert rejected.value.detail == "Customer create attempt cannot be reopened"
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


async def _post_with_auth(*, role: AdminRole, realm_type: str) -> httpx.Response:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    admin = _admin(role=role)

    async def user_override() -> AdminUserModel:
        return admin

    async def realm_override() -> RealmResolution:
        return _realm(realm_type)

    async def db_override():
        yield cast(AsyncSession, AsyncMock())

    async def client_override() -> RemnawaveClient:
        return cast(RemnawaveClient, object())

    app.dependency_overrides[get_current_active_user] = user_override
    app.dependency_overrides[get_request_admin_realm] = realm_override
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_remnawave_client] = client_override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://admin.cyber-vpn.net") as client:
        return await client.post(
            f"/api/v1/admin/remnawave/customer-create-attempts/{uuid4()}/settle",
            json={"provider_numeric_user_id": 731},
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("realm_type", ["partner", "customer"])
async def test_partner_and_customer_realms_cannot_call_direct_settlement_url(realm_type: str) -> None:
    response = await _post_with_auth(role=AdminRole.ADMIN, realm_type=realm_type)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin realm required"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("role", [AdminRole.OPERATOR, AdminRole.SUPPORT, AdminRole.VIEWER])
async def test_lower_privilege_admin_roles_cannot_call_direct_settlement_url(role: AdminRole) -> None:
    response = await _post_with_auth(role=role, realm_type="admin")

    assert response.status_code == 403
    assert response.json()["detail"] == "Requires minimum role: admin"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anonymous_direct_url_is_rejected_before_attempt_lookup() -> None:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def anonymous_override() -> AdminUserModel:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    async def realm_override() -> RealmResolution:
        return _realm("admin")

    app.dependency_overrides[get_current_active_user] = anonymous_override
    app.dependency_overrides[get_request_admin_realm] = realm_override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://admin.cyber-vpn.net") as client:
        response = await client.post(
            f"/api/v1/admin/remnawave/customer-create-attempts/{uuid4()}/reopen",
            json={},
        )

    assert response.status_code == 401


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalars(self) -> _ScalarResult:
        return self

    def one_or_none(self) -> object:
        return self._value


class _StatementDescription(Protocol):
    column_descriptions: list[dict[str, object]]


class _SharedAttemptState:
    def __init__(self) -> None:
        customer_id = uuid4()
        self.lock = asyncio.Lock()
        self.customer = MobileUserModel(
            id=customer_id,
            public_uid=998877665544,
            email="customer@example.com",
            username="local-customer",
            password_hash="unused",
            status="active",
            is_active=True,
            remnawave_user_id=None,
            remnawave_uuid=None,
        )
        self.attempt = ApiIdempotencyRecordModel(
            id=uuid4(),
            scope="remnawave-customer:create",
            idempotency_key="c" * 64,
            resource_type="remnawave_user_create",
            resource_id=customer_id,
            request_hash="d" * 64,
            response_payload={},
            status="reconciliation_required",
            expires_at=None,
        )


class _LockingSession:
    def __init__(self, state: _SharedAttemptState) -> None:
        self.state = state
        self.owns_lock = False

    async def execute(self, statement: object) -> _ScalarResult:
        entity = cast(_StatementDescription, statement).column_descriptions[0].get("entity")
        if entity is ApiIdempotencyRecordModel:
            # PostgreSQL permits one transaction to select the same row FOR
            # UPDATE again. Mirror that re-entrant behavior for the service's
            # monotonic transition refresh instead of self-deadlocking here.
            if not self.owns_lock:
                await self.state.lock.acquire()
                self.owns_lock = True
            return _ScalarResult(self.state.attempt)
        if entity is MobileUserModel:
            return _ScalarResult(self.state.customer)
        raise AssertionError(f"Unexpected statement: {statement}")

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self._release()

    async def rollback(self) -> None:
        self._release()

    def _release(self) -> None:
        if self.owns_lock:
            self.owns_lock = False
            self.state.lock.release()


class _SharedProvider:
    def __init__(self, state: _SharedAttemptState) -> None:
        self.state = state
        self.calls = 0

    async def get_by_ref(self, ref: RemnawaveUserRef) -> User:
        self.calls += 1
        now = datetime(2026, 9, 1, tzinfo=UTC)
        return User(
            uuid=ref.legacy_uuid,
            username=f"cvpn_t_{self.state.customer.id.hex[:28]}",
            status=UserStatus.ACTIVE,
            short_uuid="safe",
            created_at=now,
            updated_at=now,
            remnawave_id=ref.id,
            email=self.state.customer.email,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_settlement_has_one_authoritative_read_and_one_audit(monkeypatch) -> None:
    state = _SharedAttemptState()
    provider = _SharedProvider(state)
    monkeypatch.setattr(routes, "RemnawaveUserGateway", lambda _client: provider)

    async def persist(
        _session: object,
        *,
        customer: MobileUserModel,
        remnawave_user_id: object,
        remnawave_uuid: object,
        source: str,
    ) -> RemnawaveUserRef:
        assert source == "admin_customer_create_settlement"
        customer.remnawave_user_id = cast(int, remnawave_user_id)
        customer.remnawave_uuid = str(remnawave_uuid) if remnawave_uuid is not None else None
        return RemnawaveUserRef(id=customer.remnawave_user_id, legacy_uuid=None)

    async def resolve(_session: object, customer: MobileUserModel) -> RemnawaveUserRef:
        return RemnawaveUserRef(id=customer.remnawave_user_id, legacy_uuid=None)

    monkeypatch.setattr(settlement_module, "persist_runtime_mapped_mobile_identity", persist)
    monkeypatch.setattr(settlement_module, "resolve_exact_mapped_mobile_user_ref", resolve)
    audited: list[UUID] = []

    async def audit(**kwargs: object) -> None:
        audited.append(cast(UUID, kwargs["resource_id"]))

    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    body = SettleCustomerCreateAttemptRequest(provider_numeric_user_id=731)
    actor = _admin()
    first_session = _LockingSession(state)
    second_session = _LockingSession(state)

    first, second = await asyncio.gather(
        routes.settle_customer_create_attempt(
            attempt_id=state.attempt.id,
            body=body,
            request=_request(),
            current_admin=actor,
            db=cast(AsyncSession, first_session),
            client=cast(RemnawaveClient, object()),
        ),
        routes.settle_customer_create_attempt(
            attempt_id=state.attempt.id,
            body=body,
            request=_request(),
            current_admin=actor,
            db=cast(AsyncSession, second_session),
            client=cast(RemnawaveClient, object()),
        ),
    )

    assert sorted([first.changed, second.changed]) == [False, True]
    assert provider.calls == 1
    assert audited == [state.attempt.id]
    assert state.attempt.status == "completed"
