from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import AdminRole, PrincipalClass
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.presentation.api.v1.subscriptions import credential_access, routes
from src.presentation.dependencies.auth import CurrentPrincipalActor


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self):
        return self

    def all(self) -> list[object]:
        return [] if self._value is None else [self._value]


class _FakeDb:
    def __init__(
        self,
        *,
        admin: object | None = None,
        customer: object | None = None,
        reconciliation: object | None = None,
    ) -> None:
        self.admin = admin
        self.customer = customer
        self.reconciliation = reconciliation
        self.commit = AsyncMock()

    async def get(self, entity: type[object], identifier: UUID) -> object | None:
        if entity is AdminUserModel and self.admin is not None and self.admin.id == identifier:
            return self.admin
        if entity is MobileUserModel and self.customer is not None and self.customer.id == identifier:
            return self.customer
        return None

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.reconciliation)


class _FakePipeline:
    def __init__(self) -> None:
        self.operations: list[tuple[str, object]] = []

    def incr(self, key: str) -> None:
        self.operations.append(("incr", key))

    def expire(self, key: str, seconds: int) -> None:
        self.operations.append(("expire", (key, seconds)))

    async def execute(self) -> list[int | bool]:
        return [1, True]


class _FakeRedis:
    def __init__(self) -> None:
        self.pipeline_instance = _FakePipeline()

    async def get(self, _key: str) -> None:
        return None

    async def ttl(self, _key: str) -> int:
        return 60

    def pipeline(self) -> _FakePipeline:
        return self.pipeline_instance


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [(b"user-agent", b"security-test")],
            "client": ("127.0.0.1", 443),
            "scheme": "https",
            "server": ("testserver", 443),
            "query_string": b"",
        }
    )


def _realm(realm_type: str, *, realm_id: UUID | None = None) -> RealmResolution:
    resolved_id = realm_id or uuid4()
    return RealmResolution(
        auth_realm=SimpleNamespace(
            id=resolved_id,
            realm_type=realm_type,
            realm_key=realm_type,
            audience=f"cybervpn:{realm_type}",
        ),
        source="test",
    )


def _actor(realm: RealmResolution, principal_id: UUID, principal_type: str) -> CurrentPrincipalActor:
    return CurrentPrincipalActor(
        principal_id=principal_id,
        principal_type=principal_type,
        auth_realm_id=realm.auth_realm.id,
        auth_realm_key=realm.realm_key,
        audience=realm.audience,
    )


def _customer(realm_id: UUID, *, customer_id: UUID | None = None, numeric_id: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        id=customer_id or uuid4(),
        auth_realm_id=realm_id,
        remnawave_user_id=numeric_id,
        remnawave_uuid=str(uuid4()),
        is_active=True,
        status="active",
    )


def _reconciliation(customer: SimpleNamespace, *, numeric_id: int | None = None, state: str = "mapped"):
    return SimpleNamespace(
        subject_type="mobile_user",
        subject_id=customer.id,
        numeric_user_id=customer.remnawave_user_id if numeric_id is None else numeric_id,
        legacy_uuid=customer.remnawave_uuid,
        reconciliation_state=state,
    )


def _admin(realm_id: UUID, role: AdminRole) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        auth_realm_id=realm_id,
        role=role.value,
        is_active=True,
        deleted_at=None,
        totp_enabled=True,
    )


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_config_is_self_only_and_uses_exact_numeric_identity(monkeypatch) -> None:
    realm = _realm("customer")
    customer = _customer(realm.auth_realm.id)
    actor = _actor(realm, customer.id, PrincipalClass.CUSTOMER.value)
    captured: dict[str, object] = {}

    class _GenerateConfig:
        def __init__(self, _client: object) -> None:
            pass

        async def execute(self, user_ref) -> dict[str, object]:
            captured["user_ref"] = user_ref
            return {"config": "secret-config"}

    monkeypatch.setattr(routes, "GenerateConfigUseCase", _GenerateConfig)
    db = _FakeDb(customer=customer, reconciliation=_reconciliation(customer))

    response = await routes.generate_config(
        str(customer.id),
        _request(f"/subscriptions/config/{customer.id}"),
        actor,
        realm,
        db,
        object(),
        _FakeRedis(),
    )

    assert response == {"config": "secret-config"}
    assert captured["user_ref"].id == customer.remnawave_user_id
    assert captured["user_ref"].legacy_uuid == UUID(customer.remnawave_uuid)
    db.commit.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_config_rejects_cross_user_before_lookup(monkeypatch) -> None:
    realm = _realm("customer")
    actor = _actor(realm, uuid4(), PrincipalClass.CUSTOMER.value)
    generate = AsyncMock()
    monkeypatch.setattr(routes, "GenerateConfigUseCase", generate)

    with pytest.raises(HTTPException) as exc_info:
        await routes.generate_config(
            str(uuid4()),
            _request("/subscriptions/config/cross-user"),
            actor,
            realm,
            _FakeDb(),
            object(),
            _FakeRedis(),
        )

    assert exc_info.value.status_code == 404
    generate.assert_not_called()


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_config_rejects_unmapped_or_mismatched_identity() -> None:
    realm = _realm("customer")
    customer = _customer(realm.auth_realm.id)
    actor = _actor(realm, customer.id, PrincipalClass.CUSTOMER.value)

    for reconciliation in (None, _reconciliation(customer, state="conflict"), _reconciliation(customer, numeric_id=99)):
        with pytest.raises(HTTPException) as exc_info:
            await routes.generate_config(
                str(customer.id),
                _request(f"/subscriptions/config/{customer.id}"),
                actor,
                realm,
                _FakeDb(customer=customer, reconciliation=reconciliation),
                object(),
                _FakeRedis(),
            )
        assert exc_info.value.status_code == 409


@pytest.mark.security
@pytest.mark.asyncio
async def test_active_subscription_is_customer_self_only_and_uses_exact_numeric_identity(monkeypatch) -> None:
    realm = _realm("customer")
    customer = _customer(realm.auth_realm.id, numeric_id=2718)
    actor = _actor(realm, customer.id, PrincipalClass.CUSTOMER.value)
    captured: dict[str, object] = {}

    class _GetActiveSubscription:
        def __init__(self, _client: object) -> None:
            pass

        async def execute(self, user_ref):
            captured["user_ref"] = user_ref
            return SimpleNamespace(
                status="active",
                plan_name="Safe",
                expires_at=None,
                traffic_limit_bytes=100,
                used_traffic_bytes=10,
                auto_renew=False,
            )

    monkeypatch.setattr(routes, "GetActiveSubscriptionUseCase", _GetActiveSubscription)
    response = await routes.get_active_subscription(
        actor,
        realm,
        _FakeDb(customer=customer, reconciliation=_reconciliation(customer)),
        object(),
        _FakeRedis(),
    )

    assert response.status == "active"
    assert captured["user_ref"].id == 2718
    assert captured["user_ref"].legacy_uuid == UUID(customer.remnawave_uuid)


@pytest.mark.security
@pytest.mark.asyncio
async def test_active_subscription_rejects_admin_partner_and_foreign_customer_realm() -> None:
    for realm_type, principal_type in (
        ("admin", PrincipalClass.ADMIN.value),
        ("partner", PrincipalClass.PARTNER_OPERATOR.value),
    ):
        realm = _realm(realm_type)
        actor = _actor(realm, uuid4(), principal_type)
        with pytest.raises(HTTPException) as exc_info:
            await routes.get_active_subscription(actor, realm, _FakeDb(), object(), _FakeRedis())
        assert exc_info.value.status_code == 403

    customer_realm = _realm("customer")
    customer = _customer(uuid4())
    actor = _actor(customer_realm, customer.id, PrincipalClass.CUSTOMER.value)
    with pytest.raises(HTTPException) as exc_info:
        await routes.get_active_subscription(
            actor,
            customer_realm,
            _FakeDb(customer=customer, reconciliation=_reconciliation(customer)),
            object(),
            _FakeRedis(),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [AdminRole.VIEWER, AdminRole.SUPPORT, AdminRole.FINANCE, AdminRole.OPERATOR, AdminRole.ADMIN],
)
async def test_low_privilege_admin_roles_cannot_read_live_config(role: AdminRole) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, role)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)

    assert not has_permission(role, Permission.VPN_CREDENTIAL_READ)
    with pytest.raises(HTTPException) as exc_info:
        await routes.generate_config(
            str(uuid4()),
            _request("/subscriptions/config/admin-denied"),
            actor,
            realm,
            _FakeDb(admin=admin),
            object(),
            _FakeRedis(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.security
@pytest.mark.asyncio
async def test_partner_foreign_realm_cannot_read_customer_config() -> None:
    realm = _realm("partner")
    actor = _actor(realm, uuid4(), PrincipalClass.PARTNER_OPERATOR.value)

    with pytest.raises(HTTPException) as exc_info:
        await routes.generate_config(
            str(uuid4()),
            _request("/subscriptions/config/foreign-realm"),
            actor,
            realm,
            _FakeDb(),
            object(),
            _FakeRedis(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.security
@pytest.mark.asyncio
async def test_trusted_admin_requires_fresh_passkey_for_config_read() -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, AdminRole.SUPER_ADMIN)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)

    assert has_permission(AdminRole.SUPER_ADMIN, Permission.VPN_CREDENTIAL_READ)
    with pytest.raises(HTTPException) as exc_info:
        await routes.generate_config(
            str(uuid4()),
            _request("/subscriptions/config/fresh-auth-required"),
            actor,
            realm,
            _FakeDb(admin=admin),
            object(),
            _FakeRedis(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Fresh passkey reauthentication required"


@pytest.mark.security
@pytest.mark.asyncio
async def test_trusted_admin_config_read_is_mandatorily_audited_without_secret_material(monkeypatch) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, AdminRole.SUPER_ADMIN)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)
    customer = _customer(uuid4())
    audit = AsyncMock()
    fresh_auth = AsyncMock()

    class _GenerateConfig:
        def __init__(self, _client: object) -> None:
            pass

        async def execute(self, _user_ref) -> dict[str, object]:
            return {"config": "must-never-enter-audit", "subscription_url": "https://secret.example"}

    monkeypatch.setattr(credential_access, "GenerateConfigUseCase", _GenerateConfig)
    monkeypatch.setattr(credential_access, "enforce_passkey_fresh_auth", fresh_auth)
    monkeypatch.setattr(credential_access, "write_required_admin_audit_entry", audit)
    db = _FakeDb(admin=admin, customer=customer, reconciliation=_reconciliation(customer))

    response = await routes.generate_config(
        str(customer.id),
        _request(f"/subscriptions/config/{customer.id}"),
        actor,
        realm,
        db,
        object(),
        _FakeRedis(),
    )

    assert response["config"] == "must-never-enter-audit"
    fresh_auth.assert_awaited_once()
    audit.assert_awaited_once()
    audit_payload = audit.await_args.kwargs
    assert audit_payload["action"] == "customer_vpn_credentials_read"
    assert audit_payload["resource_id"] == customer.id
    serialized_audit = repr(audit_payload)
    assert "must-never-enter-audit" not in serialized_audit
    assert "secret.example" not in serialized_audit
    db.commit.assert_awaited_once()


@pytest.mark.security
@pytest.mark.asyncio
async def test_admin_config_is_not_returned_when_required_audit_fails(monkeypatch) -> None:
    realm = _realm("admin")
    admin = _admin(realm.auth_realm.id, AdminRole.SUPER_ADMIN)
    actor = _actor(realm, admin.id, PrincipalClass.ADMIN.value)
    customer = _customer(uuid4())

    class _GenerateConfig:
        def __init__(self, _client: object) -> None:
            pass

        async def execute(self, _user_ref) -> dict[str, object]:
            return {"config": "never-returned"}

    monkeypatch.setattr(credential_access, "GenerateConfigUseCase", _GenerateConfig)
    monkeypatch.setattr(credential_access, "enforce_passkey_fresh_auth", AsyncMock())
    monkeypatch.setattr(
        credential_access,
        "write_required_admin_audit_entry",
        AsyncMock(side_effect=RuntimeError("audit unavailable")),
    )
    db = _FakeDb(admin=admin, customer=customer, reconciliation=_reconciliation(customer))

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await routes.generate_config(
            str(customer.id),
            _request(f"/subscriptions/config/{customer.id}"),
            actor,
            realm,
            db,
            object(),
            _FakeRedis(),
        )

    db.commit.assert_not_awaited()


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_cancel_uses_exact_numeric_identity(monkeypatch) -> None:
    realm = _realm("customer")
    customer = _customer(realm.auth_realm.id, numeric_id=314)
    actor = _actor(realm, customer.id, PrincipalClass.CUSTOMER.value)
    canceled_at = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
    captured: dict[str, object] = {}

    class _Cancel:
        def __init__(self, *_args: object) -> None:
            pass

        async def execute(self, user_ref):
            captured["user_ref"] = user_ref
            return canceled_at

    monkeypatch.setattr(routes, "CancelSubscriptionUseCase", _Cancel)
    redis_client = _FakeRedis()

    response = await routes.cancel_subscription(
        actor,
        realm,
        _FakeDb(customer=customer, reconciliation=_reconciliation(customer)),
        object(),
        redis_client,
    )

    assert response.canceled_at == canceled_at
    assert captured["user_ref"].id == 314
    assert redis_client.pipeline_instance.operations == [
        ("incr", f"subscription_cancel:{customer.id}"),
        ("expire", (f"subscription_cancel:{customer.id}", 3600)),
    ]


@pytest.mark.security
@pytest.mark.asyncio
async def test_customer_cancel_rejects_unmapped_mismatch_and_cross_realm() -> None:
    realm = _realm("customer")
    customer = _customer(realm.auth_realm.id)
    actor = _actor(realm, customer.id, PrincipalClass.CUSTOMER.value)

    for db in (
        _FakeDb(customer=customer, reconciliation=None),
        _FakeDb(customer=customer, reconciliation=_reconciliation(customer, numeric_id=999)),
        _FakeDb(customer=_customer(uuid4(), customer_id=customer.id), reconciliation=_reconciliation(customer)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await routes.cancel_subscription(actor, realm, db, object(), _FakeRedis())
        assert exc_info.value.status_code in {404, 409}


@pytest.mark.security
@pytest.mark.asyncio
async def test_admin_and_partner_realms_cannot_cancel_customer_subscription() -> None:
    for realm_type, principal_type in (
        ("admin", PrincipalClass.ADMIN.value),
        ("partner", PrincipalClass.PARTNER_OPERATOR.value),
    ):
        realm = _realm(realm_type)
        actor = _actor(realm, uuid4(), principal_type)
        with pytest.raises(HTTPException) as exc_info:
            await routes.cancel_subscription(actor, realm, _FakeDb(), object(), _FakeRedis())
        assert exc_info.value.status_code == 403


def test_config_path_identifier_is_canonical_local_uuid_only() -> None:
    canonical = str(uuid4())
    assert routes._parse_canonical_local_user_id(canonical) == UUID(canonical)
    for malformed in (canonical.upper(), canonical.replace("-", ""), f" {canonical}", "../customer"):
        with pytest.raises(HTTPException) as exc_info:
            routes._parse_canonical_local_user_id(malformed)
        assert exc_info.value.status_code == 422
